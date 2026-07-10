# SmashMC Automation Mod

Tiny client-side Forge bridge for `tools/smashmc/export_learnsets.py`.

Compatibility:

- Minecraft 1.16.5
- Forge 36.2.35
- Pixelmon 9.1.12
- No SmashModpack dependency

The mod binds an HTTP API to `127.0.0.1` only. It can:

- execute one chat command per request
- return captured chat messages
- report current server/status
- report whether Groudon appears to be joined
- disconnect cleanly

API:

- `GET /health`
- `GET /status`
- `GET /messages?since=<id>`
- `POST /command` with `{"command":"/groudon"}`
- `POST /disconnect`

Build:

```powershell
cd tools\smashmc\forge-automation-mod
gradle build
```

Run the resulting jar from `build/libs/` in a normal Forge 36.2.35 + Pixelmon
9.1.12 client.

Optional settings:

- JVM property `-Dsmashmc.automation.port=17616`
- Environment variable `SMASHMC_AUTOMATION_PORT=17616`
- JVM property `-Dsmashmc.automation.token=secret`
- Environment variable `SMASHMC_AUTOMATION_TOKEN=secret`
