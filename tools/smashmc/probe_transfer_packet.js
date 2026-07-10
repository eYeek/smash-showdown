#!/usr/bin/env node
"use strict";

const path = require("path");
const fs = require("fs");
const net = require("net");
const mc = require("minecraft-protocol");
const mineflayer = require("mineflayer");
const minecraftData = require("minecraft-data");
const forgeProtocol = require("minecraft-protocol-forge");

const repoRoot = path.resolve(__dirname, "../..");
const authDir = path.join(repoRoot, "data", "smashmc", "auth");

const cli = {};
for (let i = 2; i < process.argv.length; i++) {
  const arg = process.argv[i];
  if (!arg.startsWith("--")) continue;
  const key = arg.slice(2);
  const value = process.argv[i + 1] && !process.argv[i + 1].startsWith("--") ? process.argv[++i] : "true";
  cli[key] = value;
}

process.env.SMASHMC_MC_HOST = process.env.SMASHMC_MC_HOST || "play.smashmc.co";
process.env.SMASHMC_MC_PORT = process.env.SMASHMC_MC_PORT || "25565";

const host = cli.host || process.env.SMASHMC_MC_HOST;
const port = Number(cli.port || process.env.SMASHMC_MC_PORT);
const username = cli.username || process.env.SMASHMC_MC_USERNAME;
const version = cli.version || process.env.SMASHMC_MC_VERSION || "1.16.5";
const brand = cli.brand || process.env.SMASHMC_MC_BRAND || "vanilla";
const enableForge = cli.forge === "true" || process.env.SMASHMC_PROBE_FORGE === "1";
const WAIT_TIMEOUT_MS = 30000;
const probeMs = Number(cli.ms || process.env.SMASHMC_PROBE_MS || String(WAIT_TIMEOUT_MS));
const logFile = path.resolve(cli["log-file"] || process.env.SMASHMC_PROBE_LOG || path.join(repoRoot, "data", "smashmc", "probe_transfer_latest.log"));

if (!host) {
  console.error("SMASHMC_MC_HOST is required.");
  process.exit(2);
}

function now() {
  return new Date().toISOString();
}

function log(line) {
  const text = `${now()} ${line}`;
  fs.appendFileSync(logFile, `${text}\n`);
  console.log(text);
}

function hex(buffer, limit = 128) {
  if (!buffer) return "";
  const data = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  const clipped = data.subarray(0, Math.min(limit, data.length));
  const suffix = data.length > limit ? `...(+${data.length - limit} bytes)` : "";
  return clipped.toString("hex") + suffix;
}

function readVarInt(buffer, offset = 0) {
  let value = 0;
  let size = 0;
  let byte = 0;
  do {
    if (offset + size >= buffer.length) return null;
    byte = buffer[offset + size];
    value |= (byte & 0x7f) << (size * 7);
    size++;
    if (size > 5) return null;
  } while ((byte & 0x80) === 0x80);
  return { value, size };
}

function readJavaUtf(buffer, offset = 0) {
  if (offset + 2 > buffer.length) return null;
  const length = buffer.readUInt16BE(offset);
  const start = offset + 2;
  const end = start + length;
  if (end > buffer.length) return null;
  return { value: buffer.toString("utf8", start, end), size: 2 + length };
}

function packetIdLookup(protocolVersion, state, packetName) {
  try {
    const data = minecraftData(protocolVersion);
    const toClient = data.protocol[state] && data.protocol[state].toClient;
    const packet = toClient && toClient.types && toClient.types.packet;
    const fields = packet && packet[1];
    const nameField = fields && fields.find(field => field.name === "name");
    const mappings = nameField && nameField.type && nameField.type[1] && nameField.type[1].mappings;
    if (!mappings) return "?";
    for (const [id, name] of Object.entries(mappings)) {
      if (name === packetName) return id;
    }
  } catch (_error) {
    return "?";
  }
  return "?";
}

function compact(value) {
  try {
    return JSON.stringify(value, (_key, item) => {
      if (typeof item === "bigint") return item.toString();
      if (Buffer.isBuffer(item)) return `<Buffer ${item.length} bytes ${hex(item, 64)}>`;
      if (item && item.type === "Buffer" && Array.isArray(item.data)) {
        return `<Buffer ${item.data.length} bytes ${hex(Buffer.from(item.data), 64)}>`;
      }
      if (Array.isArray(item) && item.length > 30) return `<Array ${item.length} items>`;
      return item;
    });
  } catch (error) {
    return `<unserializable ${error && error.message ? error.message : error}>`;
  }
}

function cleanChat(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value.toString === "function") return value.toString();
  return compact(value);
}

function position(bot) {
  const pos = bot.entity && bot.entity.position;
  if (!pos) return null;
  return { x: pos.x, y: pos.y, z: pos.z };
}

function positionIsNonZero(bot) {
  const pos = position(bot);
  if (!pos) return false;
  return Math.abs(pos.x) > 0.001 || Math.abs(pos.y) > 0.001 || Math.abs(pos.z) > 0.001;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function timeoutError(awaiting, timeoutMs = WAIT_TIMEOUT_MS) {
  return new Error(`AWAIT_TIMEOUT awaiting=${awaiting} waited_ms=${timeoutMs}`);
}

function waitForEvent(emitter, event, timeoutMs = WAIT_TIMEOUT_MS, label = event) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      reject(timeoutError(label, timeoutMs));
    }, timeoutMs);
    const handler = (...args) => {
      cleanup();
      resolve(args);
    };
    const cleanup = () => {
      clearTimeout(timeout);
      emitter.removeListener(event, handler);
    };
    emitter.on(event, handler);
  });
}

function waitUntil(predicate, label, timeoutMs = WAIT_TIMEOUT_MS, intervalMs = 250) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = setInterval(() => {
      if (predicate()) {
        clearInterval(timer);
        resolve();
        return;
      }
      if (Date.now() - started >= timeoutMs) {
        clearInterval(timer);
        reject(timeoutError(label, timeoutMs));
      }
    }, intervalMs);
  });
}

async function waitUntilReady(bot) {
  if (!bot.player) await waitForEvent(bot, "login", WAIT_TIMEOUT_MS, "mineflayer login event");
  await waitForEvent(bot, "spawn", WAIT_TIMEOUT_MS, "mineflayer spawn event");
  await waitUntil(() => positionIsNonZero(bot), "non-zero bot.entity.position", WAIT_TIMEOUT_MS);
  await sleep(3000);
}

async function waitForBackendJoin(bot, startPosition, timeoutMs) {
  return new Promise(resolve => {
    let done = false;
    let lastPosition = startPosition;
    const finish = reason => {
      if (done) return;
      done = true;
      cleanup();
      resolve({ ok: true, reason });
    };
    const cleanup = () => {
      clearInterval(timer);
      clearTimeout(timeout);
      bot.removeListener("spawn", onSpawn);
      bot.removeListener("respawn", onRespawn);
      bot._client.removeListener("login", onLoginPacket);
      bot._client.removeListener("respawn", onRespawnPacket);
    };
    const onSpawn = () => finish("mineflayer spawn event after command");
    const onRespawn = () => finish("mineflayer respawn event after command");
    const onLoginPacket = () => finish("Join Game packet after command");
    const onRespawnPacket = () => finish("Respawn packet after command");
    const timer = setInterval(() => {
      const currentPosition = position(bot);
      if (currentPosition && lastPosition) {
        const dx = currentPosition.x - lastPosition.x;
        const dy = currentPosition.y - lastPosition.y;
        const dz = currentPosition.z - lastPosition.z;
        const moved = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (moved > 8) {
          log(`position_change distance=${moved.toFixed(2)} from=${compact(lastPosition)} to=${compact(currentPosition)}`);
          finish("significant position change after command");
          return;
        }
      }
      lastPosition = currentPosition;
    }, 1000);
    const timeout = setTimeout(() => {
      if (done) return;
      done = true;
      cleanup();
      resolve({ ok: false, reason: `AWAIT_TIMEOUT awaiting=proxy/backend transfer completion after /groudon waited_ms=${timeoutMs}` });
    }, timeoutMs);

    bot.on("spawn", onSpawn);
    bot.on("respawn", onRespawn);
    bot._client.on("login", onLoginPacket);
    bot._client.on("respawn", onRespawnPacket);
  });
}

async function createProbeBot() {
  const commonOptions = {
    host,
    port,
    username,
    version,
    brand,
    auth: "microsoft",
    profilesFolder: authDir,
    onMsaCode: data => {
      console.log(`Microsoft device-code URL: ${data.verification_uri}`);
      console.log(`Microsoft device-code: ${data.user_code}`);
    },
  };

  if (!enableForge) return { bot: mineflayer.createBot(commonOptions), releaseConnection: null };

  let delayedConnect = null;
  let connectReady;
  const connectReadyPromise = new Promise(resolve => {
    connectReady = resolve;
  });
  const client = mc.createClient({
    ...commonOptions,
    validateChannelProtocol: false,
    connect: protocolClient => {
      delayedConnect = () => {
        log(`forge_probe opening socket host=${host} port=${port}`);
        protocolClient.setSocket(net.connect(port, host));
      };
      connectReady();
    },
  });

  forgeProtocol.forgeHandshake(client, {
    forgeMods: [
      { modid: "minecraft", version: "1.16.5" },
      { modid: "forge", version: "36.2.35" },
    ],
  });
  log("forge_probe installed official minecraft-protocol-forge forgeHandshake plugin");
  log("forge_probe advertised_mods=[minecraft@1.16.5, forge@36.2.35]");
  log("forge_probe plugin_support=legacy FML|HS client handshake");

  client.on("forgeMods", mods => {
    log(`forge_probe event=forgeMods mods=${compact(mods)}`);
  });

  const bot = mineflayer.createBot({ ...commonOptions, client });
  const releaseConnection = async () => {
    await Promise.race([
      connectReadyPromise,
      new Promise((_resolve, reject) => setTimeout(() => reject(timeoutError("minecraft auth/session before socket connect", WAIT_TIMEOUT_MS)), WAIT_TIMEOUT_MS)),
    ]);
    delayedConnect();
  };
  return { bot, releaseConnection };
}

function decodePluginMessage(packet) {
  const channel = packet.channel || packet.tag || packet.channelName || "";
  const data = packet.data || packet.payload || Buffer.alloc(0);
  const buffer = Buffer.isBuffer(data) ? data : Buffer.from(data);
  const details = [`channel=${channel}`, `bytes=${buffer.length}`, `hex=${hex(buffer)}`];
  const lower = channel.toLowerCase();

  if (lower === "bungeecord" || lower === "bungeecord:main") {
    const first = readJavaUtf(buffer, 0);
    if (first) {
      details.push(`bungee_subchannel=${first.value}`);
      const second = readJavaUtf(buffer, first.size);
      if (second) details.push(`bungee_arg1=${second.value}`);
    }
  }

  if (lower.startsWith("velocity:") || lower.includes("velocity")) {
    details.push("velocity_channel=true");
  }

  return details.join(" ");
}

function attachSocketLogging(client) {
  const socket = client.socket;
  if (!socket) return;
  socket.on("connect", () => log("socket event=connect"));
  socket.on("ready", () => log("socket event=ready"));
  socket.on("end", () => log("socket event=end"));
  socket.on("close", hadError => log(`socket event=close hadError=${hadError}`));
  socket.on("timeout", () => log("socket event=timeout"));
  socket.on("error", error => log(`socket event=error message=${error && error.message ? error.message : error}`));
}

async function main() {
  let sentGroudon = false;
  let sawBackendJoin = false;
  let sawDisconnect = false;
  let sawBungee = false;
  let sawVelocity = false;
  let sawCustomProxyPayload = false;
  let sawReconnectAttempt = false;
  let sawLegacyFmlHs = false;
  let sawModernFmlHandshake = false;
  let sawFmlPlay = false;
  const prePosition = { value: null };

  fs.mkdirSync(path.dirname(logFile), { recursive: true });
  fs.writeFileSync(logFile, "");
  log(`probe version=${version} host=${host} port=${port} brand=${brand} forge=${enableForge} logFile=${logFile}`);

  const { bot, releaseConnection } = await createProbeBot();

  bot.once("inject_allowed", () => {
    log("mineflayer event=inject_allowed");
    attachSocketLogging(bot._client);
  });

  bot.on("login", () => log(`mineflayer event=login username=${bot.username || ""} game=${compact(bot.game || {})}`));
  bot.on("spawn", () => {
    if (sentGroudon) sawBackendJoin = true;
    log(`mineflayer event=spawn pos=${compact(position(bot))} game=${compact(bot.game || {})}`);
  });
  bot.on("respawn", () => {
    if (sentGroudon) sawBackendJoin = true;
    log(`mineflayer event=respawn pos=${compact(position(bot))} game=${compact(bot.game || {})}`);
  });
  bot.on("end", reason => log(`mineflayer event=end reason=${reason || ""}`));
  bot.on("kicked", reason => {
    sawDisconnect = true;
    log(`mineflayer event=kicked reason=${cleanChat(reason)}`);
  });
  bot.on("error", error => log(`mineflayer event=error message=${error && error.stack ? error.stack : error}`));
  bot.on("message", message => log(`chat event=message text=${cleanChat(message)}`));
  bot.on("messagestr", message => log(`chat event=messagestr text=${message}`));
  bot.on("chat", (usernameValue, message) => log(`chat event=chat username=${usernameValue} text=${message}`));
  bot.on("whisper", (usernameValue, message) => log(`chat event=whisper username=${usernameValue} text=${message}`));
  bot.on("actionBar", message => log(`chat event=actionBar text=${cleanChat(message)}`));

  bot._client.on("state", (newState, oldState) => {
    log(`protocol event=state old=${oldState} new=${newState}`);
  });
  bot._client.on("connect", () => log("protocol event=connect"));
  bot._client.on("end", reason => log(`protocol event=end reason=${reason || ""}`));
  bot._client.on("error", error => {
    log(`protocol event=error message=${error && error.stack ? error.stack : error}`);
    if (error && error.buffer) log(`protocol parse_error_buffer_hex=${hex(error.buffer, 256)}`);
  });

  const originalWrite = bot._client.write.bind(bot._client);
  bot._client.write = (name, params) => {
    const state = bot._client.state;
    const id = packetIdLookup(version, state, name);
    if (sentGroudon || name === "custom_payload" || name === "chat" || name === "set_protocol") {
      log(`outgoing_packet state=${state} id=${id} name=${name} payload=${compact(params)}`);
      if (name === "custom_payload") {
        const channel = params && (params.channel || params.tag || params.channelName || "");
        const lower = String(channel).toLowerCase();
        if (lower === "fml|hs") sawLegacyFmlHs = true;
        if (lower === "fml:handshake") sawModernFmlHandshake = true;
        if (lower === "fml:play") sawFmlPlay = true;
        if (lower.includes("fml") || lower.includes("forge")) {
          log(`forge_probe outgoing_stage channel=${channel} bytes=${params && params.data ? Buffer.from(params.data).length : 0}`);
        }
      }
    }
    return originalWrite(name, params);
  };

  if (releaseConnection) await releaseConnection();

  bot._client.on("raw", (buffer, metadata) => {
    const state = metadata && metadata.state ? metadata.state : bot._client.state;
    const name = metadata && metadata.name ? metadata.name : "unknown";
    const shouldLog = sentGroudon || name === "custom_payload" || name === "custom_payload_login";
    if (!shouldLog) return;
    const decodedId = packetIdLookup(version, state, name);
    const varint = readVarInt(buffer, 0);
    const rawId = varint ? `0x${varint.value.toString(16)}` : "?";
    log(`raw_incoming state=${state} decoded_id=${decodedId} raw_first_varint=${rawId} name=${name} raw_hex=${hex(buffer, 96)}`);
  });

  bot._client.on("packet", (packet, metadata) => {
    const state = metadata && metadata.state ? metadata.state : bot._client.state;
    const name = metadata && metadata.name ? metadata.name : "unknown";
    const shouldLog = sentGroudon || name === "custom_payload" || name === "custom_payload_login" || name === "login" || name === "respawn" || name === "kick_disconnect" || name === "disconnect";
    if (!shouldLog) return;
    const decodedId = packetIdLookup(version, state, name);
    log(`incoming_packet state=${state} id=${decodedId} name=${name} payload=${compact(packet)}`);

    if (name === "custom_payload" || name === "custom_payload_login") {
      const channel = packet.channel || packet.tag || packet.channelName || "";
      const lower = channel.toLowerCase();
      if (lower === "bungeecord" || lower === "bungeecord:main") sawBungee = true;
      if (lower.startsWith("velocity:") || lower.includes("velocity")) sawVelocity = true;
      if (lower === "fml|hs") sawLegacyFmlHs = true;
      if (lower === "fml:handshake") sawModernFmlHandshake = true;
      if (lower === "fml:play") sawFmlPlay = true;
      if (lower.includes("bungee") || lower.includes("velocity") || lower.includes("proxy")) sawCustomProxyPayload = true;
      log(`plugin_message ${decodePluginMessage(packet)}`);
      if (lower.includes("fml") || lower.includes("forge")) {
        log(`forge_probe incoming_stage channel=${channel} bytes=${(packet.data || packet.payload || Buffer.alloc(0)).length || 0}`);
      }
    }

    if (name === "kick_disconnect" || name === "disconnect") {
      sawDisconnect = true;
      log(`disconnect_packet reason=${cleanChat(packet.reason)}`);
    }

    if (name === "login") {
      if (sentGroudon) sawBackendJoin = true;
      log(`join_game_packet ${compact(packet)}`);
    }

    if (name === "respawn") {
      if (sentGroudon) sawBackendJoin = true;
      log(`respawn_packet ${compact(packet)}`);
    }
  });

  const originalConnect = bot._client.connect && bot._client.connect.bind(bot._client);
  if (originalConnect) {
    bot._client.connect = (...args) => {
      sawReconnectAttempt = true;
      log(`protocol reconnect_attempt args=${compact(args)}`);
      return originalConnect(...args);
    };
  }

  await waitUntilReady(bot);

  prePosition.value = position(bot);
  log(`READY pos=${compact(prePosition.value)} game=${compact(bot.game || {})}`);
  log("SENDING COMMAND: /groudon");
  sentGroudon = true;
  bot.chat("/groudon");
  log("COMMAND SENT");

  const transfer = await waitForBackendJoin(bot, prePosition.value, probeMs);
  if (transfer.ok) {
    sawBackendJoin = true;
    log(`TRANSFER COMPLETE reason=${transfer.reason}`);
    await sleep(3000);
    log("SENDING COMMAND: /movelist Iron Abyss");
    bot.chat("/movelist Iron Abyss");
    log("COMMAND SENT");
    await sleep(15000);
  }

  if (!sawBackendJoin) {
    log(transfer.reason);
  }

  log(`SUMMARY sawBackendJoin=${sawBackendJoin} sawDisconnect=${sawDisconnect} sawBungee=${sawBungee} sawVelocity=${sawVelocity} sawCustomProxyPayload=${sawCustomProxyPayload} sawReconnectAttempt=${sawReconnectAttempt} sawLegacyFmlHs=${sawLegacyFmlHs} sawModernFmlHandshake=${sawModernFmlHandshake} sawFmlPlay=${sawFmlPlay}`);
  if (enableForge && !sawLegacyFmlHs) {
    log("SUMMARY official minecraft-protocol-forge did not observe a legacy FML|HS handshake from SmashMC.");
  }
  if (enableForge && sawModernFmlHandshake && !sawLegacyFmlHs) {
    log("SUMMARY SmashMC advertised modern fml:handshake/fml:play channels, while the official plugin only handles legacy FML|HS.");
  }
  if (!sawBungee && !sawVelocity && !sawCustomProxyPayload) {
    log("SUMMARY no BungeeCord, Velocity, or proxy-named plugin message was received by the client after /groudon.");
  }
  if (!sawReconnectAttempt) {
    log("SUMMARY Mineflayer/minecraft-protocol did not attempt a client-side reconnect after /groudon.");
  }
  if (!sawBackendJoin) {
    log("SUMMARY no client-observable backend join was detected through Join Game, respawn, spawn, or significant position change.");
  }

  bot.quit("proxy transfer probe complete");
  await sleep(1000);
}

main().catch(error => {
  const message = error && error.message ? error.message : String(error);
  if (message.startsWith("AWAIT_TIMEOUT")) {
    console.error(message);
  } else {
    console.error(error && error.stack ? error.stack : String(error));
  }
  process.exit(1);
});
