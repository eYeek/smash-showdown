package com.smashshowdown.smashmcautomation;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.util.text.ITextComponent;
import net.minecraft.util.text.StringTextComponent;
import net.minecraftforge.client.event.ClientChatReceivedEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.common.MinecraftForge;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Field;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Mod(SmashAutomationMod.MODID)
public final class SmashAutomationMod {
    public static final String MODID = "smashmc_automation";

    private static final int MAX_MESSAGES = 500;
    private static final Pattern CONNECTED_TO = Pattern.compile("connected\\s+to\\s*:?\\s*([A-Za-z0-9 _-]+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern JOINING = Pattern.compile("joining\\s*:?\\s*([A-Za-z0-9 _-]+)", Pattern.CASE_INSENSITIVE);

    private final List<ChatMessage> messages = Collections.synchronizedList(new ArrayList<>());
    private final ExecutorService httpExecutor = Executors.newSingleThreadExecutor(r -> {
        Thread thread = new Thread(r, "SmashMC Automation HTTP");
        thread.setDaemon(true);
        return thread;
    });
    private volatile long nextMessageId = 1;
    private volatile String lastServerName = "";
    private volatile boolean groudonJoined = false;
    private HttpServer server;

    public SmashAutomationMod() {
        FMLJavaModLoadingContext.get().getModEventBus().addListener(this::clientSetup);
        MinecraftForge.EVENT_BUS.register(this);
    }

    private void clientSetup(FMLClientSetupEvent event) {
        startHttpServer();
    }

    @SubscribeEvent
    public void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase == TickEvent.Phase.END) {
            updateServerFromClientUi();
        }
    }

    @SubscribeEvent
    public void onChat(ClientChatReceivedEvent event) {
        String text = event.getMessage().getString();
        String json = ITextComponent.Serializer.toJson(event.getMessage());
        addMessage(text, json);
        updateServerFromText(text);
    }

    private void startHttpServer() {
        try {
            int port = readIntSetting("smashmc.automation.port", "SMASHMC_AUTOMATION_PORT", 17616);
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
            server.createContext("/health", exchange -> writeJson(exchange, 200, "{\"ok\":true}"));
            server.createContext("/status", this::handleStatus);
            server.createContext("/messages", this::handleMessages);
            server.createContext("/command", this::handleCommand);
            server.createContext("/disconnect", this::handleDisconnect);
            server.setExecutor(httpExecutor);
            server.start();
        } catch (IOException error) {
            throw new RuntimeException("Unable to start SmashMC automation HTTP server", error);
        }
    }

    private void handleStatus(HttpExchange exchange) throws IOException {
        if (!checkRequest(exchange, "GET")) return;
        writeJson(exchange, 200, statusJson());
    }

    private void handleMessages(HttpExchange exchange) throws IOException {
        if (!checkRequest(exchange, "GET")) return;
        long since = queryLong(exchange.getRequestURI().getRawQuery(), "since", 0);
        StringBuilder json = new StringBuilder();
        long next = nextMessageId;
        json.append("{\"next\":").append(next).append(",\"messages\":[");
        boolean first = true;
        synchronized (messages) {
            for (ChatMessage message : messages) {
                if (message.id <= since) continue;
                if (!first) json.append(',');
                first = false;
                json.append(message.toJson());
            }
        }
        json.append("]}");
        writeJson(exchange, 200, json.toString());
    }

    private void handleCommand(HttpExchange exchange) throws IOException {
        if (!checkRequest(exchange, "POST")) return;
        String body = readBody(exchange);
        String command = extractJsonString(body, "command").trim();
        if (command.isEmpty()) {
            writeJson(exchange, 400, "{\"ok\":false,\"error\":\"Missing command\"}");
            return;
        }
        Minecraft.getInstance().execute(() -> {
            if (Minecraft.getInstance().player != null) {
                Minecraft.getInstance().player.sendChatMessage(command);
            }
        });
        writeJson(exchange, 200, "{\"ok\":true}");
    }

    private void handleDisconnect(HttpExchange exchange) throws IOException {
        if (!checkRequest(exchange, "POST")) return;
        Minecraft.getInstance().execute(() -> {
            if (Minecraft.getInstance().getConnection() != null) {
                Minecraft.getInstance().getConnection().getNetworkManager().closeChannel(new StringTextComponent("SmashMC automation disconnect"));
            }
        });
        writeJson(exchange, 200, "{\"ok\":true}");
    }

    private boolean checkRequest(HttpExchange exchange, String method) throws IOException {
        if (!method.equals(exchange.getRequestMethod())) {
            writeJson(exchange, 405, "{\"ok\":false,\"error\":\"Method not allowed\"}");
            return false;
        }
        String expectedToken = readStringSetting("smashmc.automation.token", "SMASHMC_AUTOMATION_TOKEN", "");
        if (!expectedToken.isEmpty()) {
            String token = exchange.getRequestHeaders().getFirst("X-SmashMC-Automation-Token");
            if (!expectedToken.equals(token)) {
                writeJson(exchange, 403, "{\"ok\":false,\"error\":\"Forbidden\"}");
                return false;
            }
        }
        return true;
    }

    private String statusJson() {
        Minecraft minecraft = Minecraft.getInstance();
        ServerData serverData = minecraft.getCurrentServerData();
        String serverAddress = serverData == null ? "" : serverData.serverIP;
        String dimension = minecraft.world == null ? "" : minecraft.world.getDimensionKey().getLocation().toString();
        String playerName = minecraft.player == null ? "" : minecraft.player.getName().getString();
        double x = minecraft.player == null ? 0 : minecraft.player.getPosX();
        double y = minecraft.player == null ? 0 : minecraft.player.getPosY();
        double z = minecraft.player == null ? 0 : minecraft.player.getPosZ();
        boolean inGame = minecraft.player != null && minecraft.world != null;
        String serverName = currentServerName();

        return "{"
            + "\"inGame\":" + inGame
            + ",\"server\":\"" + escapeJson(serverName) + "\""
            + ",\"serverAddress\":\"" + escapeJson(serverAddress) + "\""
            + ",\"groudonJoined\":" + groudonJoined
            + ",\"dimension\":\"" + escapeJson(dimension) + "\""
            + ",\"playerName\":\"" + escapeJson(playerName) + "\""
            + ",\"coordinates\":{\"x\":" + x + ",\"y\":" + y + ",\"z\":" + z + "}"
            + "}";
    }

    private String currentServerName() {
        updateServerFromClientUi();
        if (!lastServerName.isEmpty()) return lastServerName;
        ServerData serverData = Minecraft.getInstance().getCurrentServerData();
        return serverData == null ? "" : serverData.serverIP;
    }

    private void updateServerFromClientUi() {
        Minecraft minecraft = Minecraft.getInstance();
        String text = tabOverlayText(minecraft);
        updateServerFromText(text);
    }

    private void updateServerFromText(String text) {
        if (text == null || text.isEmpty()) return;
        Matcher connected = CONNECTED_TO.matcher(text);
        if (connected.find()) {
            setServerName(connected.group(1));
            return;
        }
        Matcher joining = JOINING.matcher(text);
        if (joining.find()) {
            String candidate = joining.group(1).trim();
            if (!candidate.isEmpty()) lastServerName = candidate;
        }
    }

    private void setServerName(String serverName) {
        String normalized = serverName == null ? "" : serverName.trim();
        if (normalized.isEmpty()) return;
        lastServerName = normalized;
        groudonJoined = normalized.toLowerCase(Locale.ROOT).contains("groudon");
    }

    private String tabOverlayText(Minecraft minecraft) {
        if (minecraft.ingameGUI == null || minecraft.ingameGUI.getTabList() == null) return "";
        StringBuilder text = new StringBuilder();
        Object tabList = minecraft.ingameGUI.getTabList();
        for (Field field : tabList.getClass().getDeclaredFields()) {
            if (!ITextComponent.class.isAssignableFrom(field.getType())) continue;
            try {
                field.setAccessible(true);
                ITextComponent component = (ITextComponent) field.get(tabList);
                if (component != null) text.append(' ').append(component.getString());
            } catch (IllegalAccessException ignored) {
            }
        }
        return text.toString();
    }

    private void addMessage(String text, String json) {
        synchronized (messages) {
            messages.add(new ChatMessage(nextMessageId++, System.currentTimeMillis(), text, json));
            while (messages.size() > MAX_MESSAGES) messages.remove(0);
        }
    }

    private static int readIntSetting(String property, String env, int fallback) {
        String value = readStringSetting(property, env, "");
        if (value.isEmpty()) return fallback;
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private static String readStringSetting(String property, String env, String fallback) {
        String value = System.getProperty(property);
        if (value == null || value.isEmpty()) value = System.getenv(env);
        return value == null || value.isEmpty() ? fallback : value;
    }

    private static long queryLong(String query, String key, long fallback) {
        if (query == null || query.isEmpty()) return fallback;
        for (String part : query.split("&")) {
            String[] pieces = part.split("=", 2);
            if (pieces.length == 2 && key.equals(pieces[0])) {
                try {
                    return Long.parseLong(pieces[1]);
                } catch (NumberFormatException ignored) {
                    return fallback;
                }
            }
        }
        return fallback;
    }

    private static String readBody(HttpExchange exchange) throws IOException {
        try (InputStream input = exchange.getRequestBody(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[1024];
            int read;
            while ((read = input.read(buffer)) >= 0) {
                output.write(buffer, 0, read);
            }
            return new String(output.toByteArray(), StandardCharsets.UTF_8);
        }
    }

    private static void writeJson(HttpExchange exchange, int status, String body) throws IOException {
        byte[] data = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, data.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(data);
        }
    }

    private static String extractJsonString(String json, String key) {
        Pattern pattern = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"((?:\\\\.|[^\"])*)\"");
        Matcher matcher = pattern.matcher(json == null ? "" : json);
        if (!matcher.find()) return "";
        return unescapeJson(matcher.group(1));
    }

    private static String unescapeJson(String value) {
        StringBuilder result = new StringBuilder();
        boolean escaped = false;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (escaped) {
                if (c == 'n') result.append('\n');
                else if (c == 'r') result.append('\r');
                else if (c == 't') result.append('\t');
                else result.append(c);
                escaped = false;
            } else if (c == '\\') {
                escaped = true;
            } else {
                result.append(c);
            }
        }
        return result.toString();
    }

    private static String escapeJson(String value) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"': result.append("\\\""); break;
                case '\\': result.append("\\\\"); break;
                case '\n': result.append("\\n"); break;
                case '\r': result.append("\\r"); break;
                case '\t': result.append("\\t"); break;
                default:
                    if (c < 0x20) result.append(String.format("\\u%04x", (int) c));
                    else result.append(c);
            }
        }
        return result.toString();
    }

    private static final class ChatMessage {
        private final long id;
        private final long timestamp;
        private final String text;
        private final String json;

        private ChatMessage(long id, long timestamp, String text, String json) {
            this.id = id;
            this.timestamp = timestamp;
            this.text = text == null ? "" : text;
            this.json = json == null ? "" : json;
        }

        private String toJson() {
            return "{"
                + "\"id\":" + id
                + ",\"timestamp\":" + timestamp
                + ",\"text\":\"" + escapeJson(text) + "\""
                + ",\"json\":\"" + escapeJson(json) + "\""
                + "}";
        }
    }
}
