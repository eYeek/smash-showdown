# Smash Showdown Project Notes

## Objective

Smash Showdown is a public-hostable Pokemon Showdown fork for SmashMC custom Pokemon and metagames.

Users should be able to build teams, search custom Pokemon, view sprites/stats/types/abilities/learnsets, import and export teams, challenge players, run local battles, and play SmashMC formats.

## Architecture

Vanilla Pokemon Showdown should remain as close to upstream as possible.

SmashMC content is isolated in:

- `data/smashmc/` for source exports and generated database artifacts.
- `data/mods/gen9smashmc/` for the generated Showdown mod.
- `client/play.pokemonshowdown.com/sprites/smashmc/` for local custom sprites.
- `tools/smashmc/` for data import/export/build tools.
- `config/custom-formats.ts` for SmashMC formats.

Vanilla Gen 9 data must not be regenerated or replaced.

## Data Sources

Pokemon metadata comes from SmashMC Discord exports:

- Pokemon names
- Forms
- Typing
- Base stats
- Abilities
- Signature move metadata
- Items
- Images/GIFs
- Evidence and thread URLs

Learnsets do not come from Discord. The authoritative source is the in-game command:

```text
/movelist <pokemon>
```

The learnset exporter uses a local Forge 36.2.35 client-side automation bridge because Mineflayer cannot join the SmashMC Groudon server reliably.

## Data Pipeline

```text
Discord export/import
  -> data/smashmc/custom_pokemon.json

Forge automation + /movelist
  -> data/smashmc/learnsets.json

python -m tools.smashmc.build_database
  -> data/smashmc/smash_database.json
  -> data/mods/gen9smashmc/pokedex.ts
  -> data/mods/gen9smashmc/learnsets.ts
  -> data/mods/gen9smashmc/moves.ts
  -> data/mods/gen9smashmc/items.ts
  -> data/mods/gen9smashmc/abilities.ts
  -> data/mods/gen9smashmc/formats-data.ts
  -> client generated data and sprites
```

## Current Formats

### Smash OU

Base format: National Dex OU behavior through the SmashMC Gen 9 mod.

Rule:

- Allows only one custom SmashMC OU or UU Pokemon.

### Smash Ubers

Base format: National Dex Ubers behavior through the SmashMC Gen 9 mod.

Rule:

- Allows one custom SmashMC Uber Pokemon.
- Allows one custom SmashMC OU or UU Pokemon.

Search labels are shortened in the teambuilder:

- `SOU`
- `SUbers`

Format names remain user-facing:

- `Smash OU`
- `Smash Ubers`

## Current Status

Publishing-prep baseline:

- 119 SmashMC Pokemon generated.
- 119 local sprite files present.
- Missing learnsets: 0.
- Missing tiers: 0.
- Missing move metadata: 0.
- Focused SmashMC tests pass.
- Local server responds on `http://localhost:8000`.
- Custom format validation rules are active.

## Publishing Target

Use Render Web Services first.

Reason:

- Smash Showdown needs a long-running Node.js server and WebSocket support.
- Static hosts such as Cloudflare Pages are not enough by themselves.
- Render supports Node web services and provides a normal public URL plus custom-domain support.

Expected deployment commands:

```sh
npm ci && npm run build
npm start
```

## Do Not Publish

Never commit or publish:

- `data/smashmc/auth/`
- local Minecraft/Microsoft token caches
- `data/smashmc/*probe*.log`
- `.codex-server-*.log`
- local build artifacts from the Forge automation mod

## Remaining Work After First Publish

- Configure a real domain or subdomain.
- Decide whether to use a custom login flow or manual/guest-only testing at first.
- Rebrand visible client assets beyond the data integration.
- Add a proper replay hosting strategy if public replay persistence is required.
- Add CI after the first successful deployment.
