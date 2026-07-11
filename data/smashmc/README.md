# SmashMC Data Pipeline

This directory holds SmashMC source exports and generated database artifacts.
Vanilla Pokemon Showdown data is not regenerated or replaced.

Pipeline:

1. `python export.py`
   - Reads the SmashMC Discord forums: `fusion-info`, `paradox-info`, `mega-info`.
   - Requires `DISCORD_TOKEN` plus either `SMASHMC_GUILD_ID` or all three forum channel IDs.
   - Downloads Discord image/GIF attachments into `data/smashmc/assets`.
   - Writes `data/smashmc/custom_pokemon.json`.

Alternative offline Discord import:

- `python import_discord_export.py`
  - Reads DiscordChatExporter JSON files from `exported data from discord custom pokemon`.
  - Downloads attachment images into `data/smashmc/assets`.
  - Writes `data/smashmc/custom_pokemon.json`.
  - Does not require a Discord bot token.

2. `python tools/smashmc/export_learnsets.py --skip-groudon --keep-client-connected`
   - Requires the Forge automation mod to be running in a real Minecraft client.
   - Assumes the player is already manually joined to Groudon when `--skip-groudon` is used.
   - Writes `data/smashmc/learnsets.json`.
   - Mega forms are skipped; they inherit vanilla base-form learnsets.

3. `python build_database.py`
   - Reads `data/smashmc/custom_pokemon.json`.
   - Reads `data/smashmc/learnsets.json`.
   - Writes `data/smashmc/smash_database.json`.
   - Generates Showdown mod data in `data/mods/gen9smashmc`.
   - Fails if any non-Mega Pokemon is missing a Minecraft learnset.

Helpful build commands:

- `python tools/smashmc/build_custom_move_reference.py`
  - Writes `data/smashmc/custom_move_reference.md`.
  - Groups SmashMC Pokemon by Mega, Paradox, and Fusion.
  - Lists each Pokemon's parsed custom move and Discord move description/effect text.

- `python build_database.py --report-learnsets`
  - Writes `data/smashmc/missing_learnsets.json`.
  - Writes `data/smashmc/missing_learnsets.txt`.
  - Writes `data/smashmc/export_missing_learnsets.ps1`.

- `python build_database.py --allow-missing-learnsets`
  - Generates a partial local mod for testing only.
  - Skips Pokemon whose Minecraft learnsets have not been exported yet.

The generated Showdown mod contains only SmashMC Pokemon and data stubs for
custom moves, abilities, and items. Custom battle behavior is intentionally not
implemented in this phase.
