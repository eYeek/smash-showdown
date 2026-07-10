# Smash Showdown

Smash Showdown is a Pokemon Showdown fork for SmashMC custom Pokemon and formats.

The goal is to keep upstream Pokemon Showdown as intact as possible while adding a separate SmashMC data layer on top of it. Vanilla Gen 9 data is not replaced. SmashMC Pokemon, learnsets, sprites, custom moves, Mega forms, and formats live in isolated generated files.

## Current Status

- Vanilla Pokemon Showdown server and client run locally.
- SmashMC Pokemon are integrated into the teambuilder and battle engine data.
- Custom sprites are downloaded and served locally.
- Minecraft-exported learnsets are merged into generated Showdown learnsets.
- Smash OU and Smash Ubers formats are available.
- Smash OU allows one custom SmashMC OU/UU Pokemon.
- Smash Ubers allows one custom SmashMC Uber Pokemon plus one custom SmashMC OU/UU Pokemon.
- Missing-data reports currently show no missing learnsets, tiers, or move metadata.

## Project Layout

- `data/smashmc/custom_pokemon.json` - source SmashMC Pokemon export.
- `data/smashmc/learnsets.json` - Minecraft `/movelist` learnset export.
- `data/smashmc/smash_database.json` - normalized generated SmashMC database.
- `data/mods/gen9smashmc/` - generated Showdown mod data.
- `client/play.pokemonshowdown.com/sprites/smashmc/` - local custom sprites served by the client.
- `tools/smashmc/` - SmashMC exporter, importer, database builder, and automation tools.
- `config/custom-formats.ts` - SmashMC battle formats.

## Data Pipeline

```text
Discord export
  -> data/smashmc/custom_pokemon.json

Minecraft /movelist export
  -> data/smashmc/learnsets.json

python -m tools.smashmc.build_database
  -> data/smashmc/smash_database.json
  -> data/mods/gen9smashmc/*
  -> client/play.pokemonshowdown.com/data/*
  -> client/play.pokemonshowdown.com/sprites/smashmc/*
```

## Local Development

Install dependencies:

```sh
npm install
```

Build:

```sh
npm run build
```

Start the server:

```sh
npm start
```

Open:

```text
http://localhost:8000
```

## Useful Checks

```sh
npx tsc --noEmit --pretty false
npx mocha test/sim/smashmc-moves.js --timeout 8000
npx mocha test/tools/smashmc-search-index.js --timeout 8000
```

Check generated-data reports:

- `data/smashmc/missing_learnsets.json`
- `data/smashmc/missing_tiers.json`
- `data/smashmc/missing_move_metadata.json`

All three should have `"count": 0` before publishing.

## Deployment

Smash Showdown is a live Node.js/WebSocket app, not a static site. Cloudflare Pages alone is not enough for the server. The recommended first deployment target is Render Web Services.

Render settings:

- Build command: `npm ci && npm run build`
- Start command: `npm start`
- Runtime: Node.js 22 or newer
- Port: use Render's `PORT` environment variable, which Pokemon Showdown reads through its cloud environment support.

This repo includes `render.yaml` for a first Render deployment.

## Sensitive Files

Do not publish local credentials or probe logs.

Ignored paths include:

- `data/smashmc/auth/`
- `data/smashmc/*probe*.log`
- `.codex-server-*.log`
- `tools/smashmc/forge-automation-mod/build/`

## Upstream

Smash Showdown is based on Pokemon Showdown, which is distributed under the MIT License. Upstream copyright and license notices are preserved.
