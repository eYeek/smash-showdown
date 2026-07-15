#!/usr/bin/env python3
"""Generate the client-side SmashMC data overlay for the teambuilder."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image
from tools.smashmc.move_descriptions import compact_move_short_desc


START = "/* SmashMC generated client data start */"
END = "/* SmashMC generated client data end */"
STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
IMAGE_SUFFIXES = {".png", ".gif", ".jpg", ".jpeg", ".webp"}
DISPLAY_TIERS = {
    "OU": "SOU",
    "UU": "SOU",
    "Uber": "SUbers",
    "AG": "SAG",
    "Unreleased": "Smash Unranked",
}
SMASH_TIER_ORDER = ["SAG", "SUbers", "SOU", "Smash Unranked"]
CLIENT_SPRITE_MAX_DIMENSION = 384


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def strip_overlay(text: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(START)}.*?{re.escape(END)}\n?",
        flags=re.DOTALL,
    )
    return pattern.sub("\n", text).rstrip()


def display_tier(entry: dict[str, Any]) -> str:
    tier = str(entry.get("tier") or "")
    return DISPLAY_TIERS.get(tier, str(entry.get("displayTier") or "Smash Unranked"))


def append_overlay(path: Path, body: str) -> None:
    original = path.read_text(encoding="utf-8")
    cleaned = strip_overlay(original)
    path.write_text(f"{cleaned}\n{START}\n{body.rstrip()}\n{END}\n", encoding="utf-8")


def abilities_dict(abilities: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    if abilities:
        result["0"] = abilities[0]
    if len(abilities) > 1:
        result["1"] = abilities[1]
    if len(abilities) > 2:
        result["H"] = abilities[2]
    return result


def pokemon_overlay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    overlay: dict[str, Any] = {}
    for index, entry in enumerate(entries, start=1):
        stats = entry.get("baseStats", {})
        overlay[entry["id"]] = {
            "num": -9000 - index,
            "name": entry["name"],
            "types": entry.get("types", ["Normal"]),
            "baseStats": {key: int(stats.get(key, 1)) for key in STAT_KEYS},
            "abilities": abilities_dict(entry.get("abilities", [])),
            "heightm": 1,
            "weightkg": 1,
            "color": "Gray",
            "eggGroups": ["Undiscovered"],
            "gen": 9,
            "tier": display_tier(entry),
            "isNonstandard": "Custom",
            "spriteid": entry.get("spriteid", entry["id"]),
        }
        if entry.get("isMega"):
            overlay[entry["id"]].update({
                "baseSpecies": entry["baseSpecies"],
                "forme": "Mega",
                "requiredItem": entry["requiredItem"],
            })
    return overlay


def formats_overlay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        entry["id"]: {"isNonstandard": "Custom", "tier": display_tier(entry)}
        for entry in entries
    }


def format_list_overlay() -> list[dict[str, Any]]:
    return [
        {"section": "SmashMC", "column": 1},
        {
            "name": "[Gen 9] Smash OU",
            "desc": "National Dex OU with one custom SmashMC OU Pokemon allowed.",
            "mod": "gen9smashmc",
            "searchShow": True,
            "challengeShow": True,
            "tournamentShow": True,
            "ruleset": ["Standard NatDex", "Terastal Clause", "+Custom"],
            "banlist": [
                "ND Uber", "ND AG", "Arena Trap", "Moody", "Power Construct", "Shadow Tag",
                "King's Rock", "Quick Claw", "Razor Fang", "Assist", "Baton Pass",
                "Last Respects", "Shed Tail",
            ],
        },
        {
            "name": "[Gen 9] Smash Ubers",
            "desc": "National Dex Ubers with one custom SmashMC Uber and one custom SmashMC OU Pokemon allowed.",
            "mod": "gen9smashmc",
            "searchShow": True,
            "challengeShow": True,
            "tournamentShow": True,
            "ruleset": [
                "Standard NatDex", "!Evasion Clause", "Evasion Moves Clause",
                "Evasion Items Clause", "Mega Rayquaza Clause", "Terastal Clause", "+Custom",
            ],
            "banlist": ["ND AG", "Shedinja", "Assist", "Baton Pass"],
        },
        {
            "name": "[Gen 9] Smash AG",
            "desc": "National Dex Anything Goes with unrestricted custom SmashMC Pokemon.",
            "mod": "gen9smashmc",
            "searchShow": True,
            "challengeShow": True,
            "tournamentShow": True,
            "ruleset": ["Standard AG", "NatDex Mod", "Terastal Clause", "+Custom"],
        },
        {
            "name": "[Gen 9] SmashMC",
            "desc": "Legacy alias for Smash AG.",
            "mod": "gen9smashmc",
            "searchShow": False,
            "challengeShow": False,
            "tournamentShow": False,
            "ruleset": ["Standard AG", "NatDex Mod", "Terastal Clause", "+Custom"],
        },
    ]


def learnsets_overlay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    overlay: dict[str, Any] = {}
    for entry in entries:
        learnset: dict[str, list[str]] = {}
        for move in entry.get("moves", []):
            move_id = to_id(move)
            if move_id:
                learnset[move_id] = ["9M"]
        overlay[entry["id"]] = {"learnset": learnset}
    return overlay


def teambuilder_learnsets_overlay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    overlay: dict[str, Any] = {}
    for entry in entries:
        learnset: dict[str, str] = {}
        for move in entry.get("moves", []):
            move_id = to_id(move)
            if move_id:
                learnset[move_id] = "9a"
        overlay[entry["id"]] = learnset
    return overlay


def teambuilder_signature_moves_overlay(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    overlay: dict[str, list[str]] = {}
    for entry in entries:
        signature_moves: list[str] = []
        learnset_ids = {to_id(move) for move in entry.get("moves", [])}
        for move in entry.get("customMoves", []):
            move_id = str(move.get("id", "")) or to_id(move.get("name", ""))
            if move_id and move_id in learnset_ids and move_id not in signature_moves:
                signature_moves.append(move_id)
        if signature_moves:
            overlay[entry["id"]] = signature_moves
    return overlay


def teambuilder_overlay(entries: list[dict[str, Any]]) -> str:
    ids = [entry["id"] for entry in entries]
    tiers = {entry["id"]: display_tier(entry) for entry in entries}
    learnsets = teambuilder_learnsets_overlay(entries)
    signature_moves = teambuilder_signature_moves_overlay(entries)
    return "\n".join([
        f"var smashPokemonIds = {js(ids)};",
        f"var smashPokemonTiers = {js(tiers)};",
        f"var smashTierOrder = {js(SMASH_TIER_ORDER)};",
        f"var smashLearnsets = {js(learnsets)};",
        f"var smashSignatureMoves = {js(signature_moves)};",
        "var smashTables = [exports.BattleTeambuilderTable, exports.BattleTeambuilderTable.gen9natdex];",
        "for (const table of smashTables) {",
        "\tif (!table) continue;",
        "\tif (!table.overrideTier) table.overrideTier = {};",
        "\tif (!table.learnsets) table.learnsets = {};",
        "\tif (!table.formatSlices) table.formatSlices = {};",
        "\tif (!table.tiers) {",
        "\t\ttable.tiers = table.tierSet || [];",
        "\t\ttable.tierSet = null;",
        "\t}",
        "\tfor (const id of smashPokemonIds) {",
        "\t\ttable.overrideTier[id] = smashPokemonTiers[id] || 'Smash Unranked';",
        "\t\ttable.learnsets[id] = smashLearnsets[id] || {};",
        "\t}",
        "\ttable.smashPokemonIds = smashPokemonIds;",
        "\ttable.smashPokemonTiers = smashPokemonTiers;",
        "\ttable.smashSignatureMoves = smashSignatureMoves;",
        "\tvar existing = new Set(table.tiers.map(row => typeof row === 'string' ? row : row[1]));",
        "\tvar rows = [];",
        "\tfor (const tier of smashTierOrder) {",
        "\t\tvar tierRows = smashPokemonIds.filter(id => smashPokemonTiers[id] === tier && !existing.has(id));",
        "\t\tif (tierRows.length) rows.push(['header', tier], ...tierRows);",
        "\t}",
        "\tif (rows.length > 1) {",
        "\t\tfor (const slice in table.formatSlices) table.formatSlices[slice] += rows.length;",
        "\t\ttable.tiers = rows.concat(table.tiers);",
        "\t}",
        "\ttable.formatSlices.SmashMC = 1;",
        "\ttable.formatSlices.SmashOU = 1;",
        "\ttable.formatSlices.SmashUbers = 1;",
        "}",
    ])


def ability_overlay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    abilities: dict[str, Any] = {}
    for entry in entries:
        for ability in entry.get("abilities", []):
            ability_id = to_id(ability)
            if ability_id:
                abilities[ability_id] = {
                    "name": ability,
                    "rating": 1,
                    "num": -9000,
                    "isNonstandard": "Custom",
                    "shortDesc": "SmashMC custom ability; battle behavior is not implemented yet.",
                }
    return dict(sorted(abilities.items()))


def item_overlay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for entry in entries:
        if not entry.get("isMega"):
            continue
        item_id = to_id(entry["requiredItem"])
        description = f"If held by {entry['baseSpecies']}, this item allows it to Mega Evolve."
        items[item_id] = {
            "name": entry["requiredItem"],
            "num": -9000,
            "gen": 9,
            "isNonstandard": "Custom",
            "icon": f"sprites/itemicons/smashmc/{item_id}.png",
            "megaStone": {entry["baseSpecies"]: entry["name"], entry["name"]: entry["name"]},
            "itemUser": [entry["baseSpecies"], entry["name"]],
            "desc": description,
            "shortDesc": description,
        }
    return dict(sorted(items.items()))


def item_icon_overlay(entries: list[dict[str, Any]]) -> dict[str, str]:
    icons: dict[str, str] = {}
    for entry in entries:
        if not entry.get("isMega"):
            continue
        item_id = to_id(entry["requiredItem"])
        icons[item_id] = f"sprites/itemicons/smashmc/{item_id}.png"
    return dict(sorted(icons.items()))


def move_overlay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    moves: dict[str, Any] = {}
    for entry in entries:
        for move in entry.get("customMoves", []):
            move_id = str(move.get("id", ""))
            if move_id:
                battle = move.get("battle", {})
                flags = dict(move.get("flags", {}))
                flags.update(battle.get("flags", {}))
                moves[move_id] = {
                    "name": move["name"],
                    "accuracy": move["accuracy"],
                    "basePower": move["basePower"],
                    "category": move["category"],
                    "pp": battle.get("pp", move["pp"]),
                    "priority": battle.get("priority", move["priority"]),
                    "flags": flags,
                    "target": battle.get("target", move.get("target", "normal")),
                    "type": move["type"],
                    "num": -9000,
                    "isNonstandard": "Custom",
                    "desc": move.get("desc", ""),
                    "shortDesc": compact_move_short_desc(move),
                }
                moves[move_id].update({
                    key: value for key, value in battle.items()
                    if key not in {"flags", "pp", "priority", "target"}
                })
    return dict(sorted(moves.items()))


def search_entries(entries: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        pokemon_row = (entry["id"], "pokemon")
        if pokemon_row not in seen:
            rows.append([pokemon_row[0], pokemon_row[1]])
            seen.add(pokemon_row)
        for ability in entry.get("abilities", []):
            ability_row = (to_id(ability), "ability")
            if ability_row[0] and ability_row not in seen:
                rows.append([ability_row[0], ability_row[1]])
                seen.add(ability_row)
        for move in entry.get("moves", []):
            move_row = (to_id(move), "move")
            if move_row[0] and move_row not in seen:
                rows.append([move_row[0], move_row[1]])
                seen.add(move_row)
        for item in entry.get("items", []):
            item_row = (to_id(item), "item")
            if item_row[0] and item_row not in seen:
                rows.append([item_row[0], item_row[1]])
                seen.add(item_row)
    return sorted(rows, key=lambda row: (row[0], row[1]))


def copy_sprite_assets(root: Path, entries: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    sprite_root = root / "client" / "play.pokemonshowdown.com" / "sprites" / "smashmc"
    sprite_root.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, dict[str, str]] = {}
    for entry in entries:
        raw_path = str(entry.get("spritePath") or "").replace("\\", "/")
        if not raw_path:
            continue
        source = root / raw_path
        if not source.is_file() or source.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        with Image.open(source) as image:
            midpoint = image.width // 2
            normal_target = sprite_root / f"{entry['id']}.png"
            shiny_target = sprite_root / f"{entry['id']}-shiny.png"
            normal = image.crop((0, 0, midpoint, image.height))
            shiny = image.crop((midpoint, 0, image.width, image.height))
            normal.thumbnail(
                (CLIENT_SPRITE_MAX_DIMENSION, CLIENT_SPRITE_MAX_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            shiny.thumbnail(
                (CLIENT_SPRITE_MAX_DIMENSION, CLIENT_SPRITE_MAX_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            save_png(normal, normal_target)
            save_png(shiny, shiny_target)
            display_w, display_h = scaled_sprite_size(normal.width, normal.height)
        mapping[entry["id"]] = {
            "normal": f"sprites/smashmc/{normal_target.name}",
            "shiny": f"sprites/smashmc/{shiny_target.name}",
            "w": display_w,
            "h": display_h,
        }
    return mapping


def save_png(image: Image.Image, target: Path) -> None:
    temp = target.with_name(f"{target.stem}.tmp{target.suffix}")
    image.save(temp, optimize=True)
    if target.exists() and target.read_bytes() == temp.read_bytes():
        temp.unlink()
        return
    os.replace(temp, target)


def scaled_sprite_size(width: int, height: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        return (96, 96)
    scale = 96 / max(width, height)
    return (max(1, round(width * scale)), max(1, round(height * scale)))


def main() -> None:
    root = repo_root()
    database_path = root / "data" / "smashmc" / "smash_database.json"
    client_data = root / "client" / "play.pokemonshowdown.com" / "data"
    database = json.loads(database_path.read_text(encoding="utf-8"))
    entries = database.get("pokemon", [])
    if not entries:
        raise RuntimeError(f"{database_path} does not contain generated Pokemon data.")
    sprite_mapping = copy_sprite_assets(root, entries)

    append_overlay(
        client_data / "pokedex.js",
        "\n".join([
            f"Object.assign(exports.BattlePokedex, {js(pokemon_overlay(entries))});",
            f"exports.BattleSmashMCSprites = {js(sprite_mapping)};",
        ]),
    )
    append_overlay(
        client_data / "pokedex-mini.js",
        f"exports.BattleSmashMCSprites = {js(sprite_mapping)};",
    )
    append_overlay(
        client_data / "formats-data.js",
        f"Object.assign(exports.BattleFormatsData, {js(formats_overlay(entries))});",
    )
    append_overlay(
        client_data / "formats.js",
        f"exports.Formats = {js(format_list_overlay())}.concat(exports.Formats);",
    )
    append_overlay(
        client_data / "learnsets.js",
        f"Object.assign(exports.BattleLearnsets, {js(learnsets_overlay(entries))});",
    )
    append_overlay(
        client_data / "abilities.js",
        "\n".join([
            f"var smashAbilities = {js(ability_overlay(entries))};",
            "for (const id in smashAbilities) if (!exports.BattleAbilities[id]) exports.BattleAbilities[id] = smashAbilities[id];",
        ]),
    )
    append_overlay(
        client_data / "moves.js",
        "\n".join([
            f"var smashMoves = {js(move_overlay(entries))};",
            "for (const id in smashMoves) if (!exports.BattleMovedex[id]) exports.BattleMovedex[id] = smashMoves[id];",
        ]),
    )
    append_overlay(
        client_data / "items.js",
        "\n".join([
            f"exports.BattleSmashMCItemIcons = {js(item_icon_overlay(entries))};",
            f"var smashItems = {js(item_overlay(entries))};",
            "for (const id in smashItems) exports.BattleItems[id] = Object.assign({}, exports.BattleItems[id], smashItems[id]);",
        ]),
    )
    append_overlay(
        client_data / "search-index.js",
        "\n".join([
            f"var smashSearchIndex = {js(search_entries(entries))};",
            "var smashSearchSeen = new Set(exports.BattleSearchIndex.map(row => `${row[0]}|${row[1]}`));",
            "var smashSearchRows = exports.BattleSearchIndex.map((row, originalIndex) => ({",
            "\trow: row.slice(),",
            "\toffset: exports.BattleSearchIndexOffset?.[originalIndex] || '',",
            "\toriginalIndex,",
            "}));",
            "for (const row of smashSearchIndex) {",
            "\tvar key = `${row[0]}|${row[1]}`;",
            "\tif (!smashSearchSeen.has(key)) {",
            "\t\tsmashSearchRows.push({row, offset: '', originalIndex: -1});",
            "\t\tsmashSearchSeen.add(key);",
            "\t}",
            "}",
            "smashSearchRows.sort((a, b) => a.row[0] === b.row[0] ? a.row[1].localeCompare(b.row[1]) : a.row[0].localeCompare(b.row[0]));",
            "var smashSearchRemap = new Map();",
            "smashSearchRows.forEach((entry, newIndex) => {",
            "\tif (entry.originalIndex >= 0) smashSearchRemap.set(entry.originalIndex, newIndex);",
            "});",
            "for (const entry of smashSearchRows) {",
            "\tif (entry.originalIndex >= 0 && typeof entry.row[2] === 'number') {",
            "\t\tentry.row[2] = smashSearchRemap.get(entry.row[2]);",
            "\t}",
            "}",
            "exports.BattleSearchIndex = smashSearchRows.map(entry => entry.row);",
            "exports.BattleSearchIndexOffset = smashSearchRows.map(entry => entry.offset);",
        ]),
    )
    append_overlay(
        client_data / "teambuilder-tables.js",
        teambuilder_overlay(entries),
    )
    print(f"Generated SmashMC client overlay for {len(entries)} Pokemon.")


if __name__ == "__main__":
    main()
