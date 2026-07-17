#!/usr/bin/env python3
"""Build the isolated SmashMC Showdown mod data files."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.smashmc.move_effects import battle_effect, raw_effect
from tools.smashmc.move_descriptions import compact_move_short_desc


STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
VALID_TYPES = {
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel", "Fairy",
}
EVIDENCE_TYPE_ALIASES = {"Iron": "Steel"}
VANILLA_ABILITY_IDS: set[str] = set()
VANILLA_ABILITY_NAMES: dict[str, str] = {}
VANILLA_MOVE_IDS: set[str] = set()
VANILLA_ITEM_IDS: set[str] = set()
VANILLA_LEARNSETS: dict[str, list[str]] = {}
CUSTOM_MOVE_ID_RE = re.compile(r"[a-z][a-z0-9_]*")
IGNORED_LEARNSET_FRAGMENTS = (
    "vote and get rewards",
    "vote for the server",
    "with vote",
    "with /vote",
    "items and more",
    "broadcast",
)
IGNORED_MOVE_IDS = {
    "burningbutts",
    "wetfart",
}
MOVE_NAME_ALIASES = {
    "constipatedcraps": "Toxic Spikes",
    "mimicsmisery": "Phantom's Grudge",
    "supersonicimpact": "Thunderous Phoenix",
}
SPECIES_MOVE_BANS = {
    "espeonmega": {"expandingforce"},
    "jolteonmega": {"risingvoltage"},
}
ABILITY_NAME_ALIASES = {
    "beserk": "Berserk",
    "electricterrain": "Electric Surge",
    "galewinds": "Gale Wings",
    "icescale": "Ice Scales",
    "neutralisinggas": "Neutralizing Gas",
    "neutralizinggas": "Neutralizing Gas",
    "pixelate": "Pixilate",
    "pixilate": "Pixilate",
    "prismarmour": "Prism Armor",
    "prismarmor": "Prism Armor",
    "tintedlense": "Tinted Lens",
    "tintedlens": "Tinted Lens",
}
TIER_ALIASES = {
    "ou": "OU",
    "smashou": "OU",
    "uu": "UU",
    "smashuu": "UU",
    "uber": "Uber",
    "ubers": "Uber",
    "smashuber": "Uber",
    "smashubers": "Uber",
    "ag": "AG",
    "anythinggoes": "AG",
    "smashag": "AG",
}
DISPLAY_TIERS = {
    "OU": "Smash OU",
    "UU": "Smash UU",
    "Uber": "Smash Ubers",
    "AG": "Smash AG",
    "Unreleased": "Smash Unranked",
}
FORCED_TIERS = {
    "hyzor": "Uber",
}


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


CUSTOM_CANONICAL_MOVE_IDS = {to_id(move) for move in MOVE_NAME_ALIASES.values()}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def ts_key(key: str) -> str:
    return key if re.fullmatch(r"[a-z][a-z0-9]*", key) else quote(key)


def normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = re.sub(r"\s+", " ", value).strip()
        value_id = to_id(cleaned)
        if cleaned and value_id not in seen:
            result.append(cleaned)
            seen.add(value_id)
    return result


def normalize_move_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        for part in value.split(","):
            cleaned = re.sub(r"\s+", " ", part).strip()
            value_id = to_id(cleaned)
            if value_id in IGNORED_MOVE_IDS:
                continue
            cleaned = MOVE_NAME_ALIASES.get(value_id, cleaned)
            value_id = to_id(cleaned)
            if cleaned and value_id not in seen and is_valid_learnset_move(cleaned):
                result.append(display_move_name(cleaned))
                seen.add(value_id)
    return result


def normalize_ability_list(values: Any) -> list[str]:
    abilities = normalize_list(values)
    result: list[str] = []
    seen: set[str] = set()
    for ability in abilities:
        ability = ABILITY_NAME_ALIASES.get(to_id(ability), ability)
        ability_id = to_id(ability)
        ability = VANILLA_ABILITY_NAMES.get(ability_id, ability)
        if ability_id and ability_id not in seen:
            result.append(ability)
            seen.add(ability_id)
    return result


def display_move_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.replace("_", " ")).strip()
    if value == value.lower() and "_" in value:
        return cleaned.title()
    return cleaned


def is_valid_learnset_move(value: str) -> bool:
    lowered = value.lower()
    if any(fragment in lowered for fragment in IGNORED_LEARNSET_FRAGMENTS):
        return False
    move_id = to_id(value)
    if move_id in VANILLA_MOVE_IDS:
        return True
    if move_id in CUSTOM_CANONICAL_MOVE_IDS:
        return True
    return CUSTOM_MOVE_ID_RE.fullmatch(value) is not None and "_" in value


def clean_evidence_line(value: str) -> str:
    value = re.sub(r"<a?:[^:]+:\d+>", " ", value)
    value = re.sub(r":[A-Za-z0-9_+-]+:", " ", value)
    value = re.sub(r"^\s*(?:[-•]\s*)+", "", value)
    value = re.sub(r"[*_~`#]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def evidence_contents(raw: dict[str, Any]) -> list[str]:
    result: list[str] = []
    evidence = raw.get("evidence")
    if not isinstance(evidence, list):
        return result
    for item in evidence:
        if isinstance(item, dict) and isinstance(item.get("content"), str):
            result.append(item["content"])
    return result


def normalize_tier(value: str) -> str:
    return TIER_ALIASES.get(to_id(value), "")


def display_tier(tier: str) -> str:
    return DISPLAY_TIERS.get(tier, "Smash Unranked")


def tier_from_text(content: str) -> str:
    for raw_line in content.splitlines():
        line = clean_evidence_line(raw_line)
        if not line:
            continue
        tier_match = re.match(r"(?i)^tier\s*:?\s*(.+)$", line)
        if tier_match:
            tier = normalize_tier(tier_match.group(1))
            if tier:
                return tier
        tier = normalize_tier(line)
        if tier:
            return tier
    return ""


def tier_from_entry(raw: dict[str, Any]) -> str:
    raw_tier = raw.get("tier")
    if isinstance(raw_tier, str):
        tier = normalize_tier(raw_tier)
        if tier:
            return tier
    for content in evidence_contents(raw):
        tier = tier_from_text(content)
        if tier:
            return tier
    return ""


def find_move_section(raw: dict[str, Any], move_id: str) -> tuple[str, list[str]]:
    best_match: tuple[float, str, list[str]] = (0, "", [])
    for content in evidence_contents(raw):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            heading = clean_evidence_line(line)
            heading_id = to_id(heading)
            if not heading_id or len(heading) > 60:
                continue
            section: list[str] = []
            for following in lines[index + 1:]:
                cleaned = clean_evidence_line(following)
                if cleaned.startswith("="):
                    break
                if cleaned:
                    section.append(cleaned)
            if heading_id == move_id:
                return heading, section
            similarity = difflib.SequenceMatcher(None, heading_id, move_id).ratio()
            if similarity > best_match[0]:
                best_match = (similarity, heading, section)
    if best_match[0] >= 0.78:
        return best_match[1], best_match[2]
    return "", []


def parse_move_metadata(raw: dict[str, Any], move: str) -> dict[str, Any]:
    move_id = to_id(move)
    heading, section = find_move_section(raw, move_id)
    name = heading if heading and to_id(heading) == move_id else display_move_name(move)
    text = "\n".join(section)
    evidence_types = VALID_TYPES | set(EVIDENCE_TYPE_ALIASES)
    type_pattern = "|".join(sorted(evidence_types, key=len, reverse=True))
    definition_text = "\n".join(
        line for line in section
        if (
            re.search(r"\b\d+\s*(?:Base\s*)?Power\b", line, re.IGNORECASE) or
            re.search(r"\b(?:Physical|Special|Status)\s+\w+(?:-Type|\s+Type)?\s+Move\b", line, re.IGNORECASE) or
            re.search(rf"\b(?:{type_pattern})(?:-Type|\s+Type)?\s+(?:Physical|Special|Status)\b", line, re.IGNORECASE) or
            re.search(rf"\b(?:{type_pattern})(?:-Type|\s+Type)?\s+Move\b", line, re.IGNORECASE) or
            re.search(r"\bSpecial\s+Status\b", line, re.IGNORECASE)
        )
    )
    power_match = re.search(r"\b(\d+)\s*(?:Base\s*)?Power\b", text, re.IGNORECASE)
    damaging_category = re.search(r"\b(Physical|Special)\b", definition_text, re.IGNORECASE)
    status_category = re.search(r"\bStatus\b", definition_text, re.IGNORECASE)
    category = (
        damaging_category.group(1).title() if damaging_category
        else "Status" if status_category or not power_match
        else "Status"
    )
    if status_category and re.search(
        r"\b(?:Status\s+Move|Status\s+\w+(?:-Type)?|Special\s+Status)\b",
        definition_text,
        re.IGNORECASE,
    ):
        category = "Status"
    type_match = re.search(
        rf"\b({type_pattern})(?:-Type|\s+Type)?\s+"
        r"(?:Physical|Special|Status)?\s*Move\b",
        definition_text,
        re.IGNORECASE,
    )
    if not type_match:
        type_match = re.search(
            rf"\b(?:Physical|Special|Status)\s+({type_pattern})"
            r"(?:-Type|\s+Type)?\s+Move\b",
            definition_text,
            re.IGNORECASE,
        )
    if not type_match:
        type_match = re.search(
            rf"\b({type_pattern})"
            r"(?:-Type|\s+Type)?\s+(?:Physical|Special|Status)\b",
            definition_text,
            re.IGNORECASE,
        )
    if not type_match:
        type_match = re.search(
            rf"\b({type_pattern})(?:-Type|\s+Type)?\b",
            definition_text,
            re.IGNORECASE,
        )
    accuracy_match = re.search(r"\b(\d+)\s*%?\s*Accuracy\b", text, re.IGNORECASE)
    priority_match = re.search(r"([+-]\d+)\s*Priority", text, re.IGNORECASE)
    description = ""
    effects: list[str] = []
    for line in section:
        if re.search(r"\b\d+\s*(?:Base\s*)?Power\b|\bAccuracy\b", line, re.IGNORECASE):
            continue
        if re.search(r"\b(?:Physical|Special|Status)\b.*\bMove\b", line, re.IGNORECASE):
            continue
        if not description:
            description = line
        else:
            effects.append(line.rstrip("."))
    short_desc = "; ".join(effects) or description
    if len(short_desc) > 250:
        short_desc = short_desc[:247].rstrip() + "..."
    parsed = {
        "id": move_id,
        "name": name,
        "accuracy": (
            True if re.search(r"\bAlways Hits?\b|\bNever Misses?\b", text, re.IGNORECASE)
            else int(accuracy_match.group(1)) if accuracy_match else 100
        ),
        "basePower": int(power_match.group(1)) if power_match else 0,
        "category": category,
        "pp": 5,
        "priority": int(priority_match.group(1)) if priority_match else 0,
        "flags": {},
        "target": "normal",
        "type": EVIDENCE_TYPE_ALIASES.get(type_match.group(1).title(), type_match.group(1).title()) if type_match else "Normal",
        "desc": description,
        "shortDesc": short_desc,
        "source": "SmashMC Discord evidence",
        "metadataComplete": bool((heading or description) and (power_match or category == "Status") and type_match),
    }
    parsed["battle"] = battle_effect(move_id)
    parsed["shortDesc"] = compact_move_short_desc(parsed)
    return parsed


def normalize_stats(value: Any, name: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} is missing base_stats.")
    stats: dict[str, int] = {}
    for stat in STAT_KEYS:
        number = value.get(stat)
        if not isinstance(number, int):
            raise ValueError(f"{name} is missing numeric {stat}.")
        if number < 1 or number > 255:
            raise ValueError(f"{name} has invalid {stat}: {number}.")
        stats[stat] = number
    return stats


def normalize_types(value: Any, name: str) -> list[str]:
    types = normalize_list(value)
    if not types:
        raise ValueError(f"{name} is missing typing.")
    bad = [type_name for type_name in types if type_name not in VALID_TYPES]
    if bad:
        raise ValueError(f"{name} has invalid typing: {', '.join(bad)}.")
    return types[:2]


def is_mega_form_name(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return normalized.startswith("mega ")


def mega_base_id(text: str) -> str:
    normalized = re.sub(r"(?i)^\s*mega\s+", "", text).strip()
    base_id = to_id(normalized)
    if base_id.endswith("x") or base_id.endswith("y"):
        fallback = base_id[:-1]
        if fallback in VANILLA_LEARNSETS:
            return fallback
    return base_id


def mega_base_name(text: str) -> str:
    return re.sub(r"(?i)^\s*mega\s+", "", text).strip()


def mega_stone_name(base_species: str) -> str:
    return f"{base_species}ite"


def learnset_moves_for(name: str, pokemon_id: str, learnsets: dict[str, Any]) -> list[str]:
    for key in (name, pokemon_id):
        entry = learnsets.get(key)
        if isinstance(entry, dict):
            moves = normalize_move_list(entry.get("moves"))
            if moves:
                return moves
            moves = normalize_move_list(entry.get("learnset"))
            if moves:
                return moves
    for key, entry in learnsets.items():
        if to_id(str(key)) != pokemon_id or not isinstance(entry, dict):
            continue
        moves = normalize_move_list(entry.get("moves"))
        if moves:
            return moves
        moves = normalize_move_list(entry.get("learnset"))
        if moves:
            return moves
    if is_mega_form_name(name):
        return VANILLA_LEARNSETS.get(mega_base_id(name), [])
    return []


def apply_species_move_bans(pokemon_id: str, moves: list[str]) -> list[str]:
    banned = SPECIES_MOVE_BANS.get(pokemon_id)
    if not banned:
        return moves
    return [move for move in moves if to_id(move) not in banned]


def normalize_entry(raw: dict[str, Any], learnsets: dict[str, Any]) -> dict[str, Any]:
    source_name = str(raw.get("name", "")).strip()
    if not source_name:
        raise ValueError("A Pokemon entry is missing name.")
    source_id = to_id(source_name)
    is_mega = is_mega_form_name(source_name)
    tier = "AG" if is_mega else FORCED_TIERS.get(source_id, tier_from_entry(raw) or "Unreleased")
    base_species = mega_base_name(source_name) if is_mega else ""
    name = f"{base_species}-Mega" if is_mega else source_name
    pokemon_id = to_id(name)
    abilities = normalize_ability_list(raw.get("abilities"))
    if not abilities:
        raise ValueError(f"{name} is missing abilities.")
    moves = learnset_moves_for(source_name, source_id, learnsets)
    moves = apply_species_move_bans(pokemon_id, moves)
    if not moves:
        raise ValueError(f"{name} is missing moves. Run tools/smashmc/export_learnsets.py.")
    custom_moves = [
        parse_move_metadata(raw, move)
        for move in moves
        if to_id(move) not in VANILLA_MOVE_IDS
    ]
    images = raw.get("images") if isinstance(raw.get("images"), list) else []
    sprites = raw.get("sprites") if isinstance(raw.get("sprites"), list) else []
    sprite_path = ""
    if sprites and isinstance(sprites[0], str):
        sprite_path = sprites[0].replace("\\", "/")
    for image in images:
        if sprite_path:
            break
        if isinstance(image, dict) and image.get("path"):
            sprite_path = str(image["path"]).replace("\\", "/")
            break
    return {
        "id": pokemon_id,
        "name": name,
        "types": normalize_types(raw.get("typing"), name),
        "baseStats": normalize_stats(raw.get("base_stats"), name),
        "abilities": abilities,
        "moves": moves,
        "customMoves": custom_moves,
        "tier": tier,
        "displayTier": display_tier(tier),
        "learnsetSource": "minecraft",
        "items": normalize_list(raw.get("items")) + ([mega_stone_name(base_species)] if is_mega else []),
        "spritePath": sprite_path,
        "spriteid": source_id,
        "isMega": is_mega,
        "baseSpecies": base_species,
        "forme": "Mega" if is_mega else "",
        "requiredItem": mega_stone_name(base_species) if is_mega else "",
        "threadUrl": str(raw.get("thread_url", "")),
        "forum": str(raw.get("forum", "")),
    }


def entry_name(raw: dict[str, Any]) -> str:
    return str(raw.get("name", "")).strip()


def missing_learnset_names(raw_entries: list[dict[str, Any]], learnsets: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for raw in raw_entries:
        name = entry_name(raw)
        if not name:
            continue
        pokemon_id = to_id(name)
        if learnset_moves_for(name, pokemon_id, learnsets):
            continue
        missing.append(name)
    return missing


def missing_tier_names(raw_entries: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for raw in raw_entries:
        name = entry_name(raw)
        if name and not is_mega_form_name(name) and to_id(name) not in FORCED_TIERS and not tier_from_entry(raw):
            missing.append(name)
    return missing


def write_learnset_report(root: Path, missing: list[str]) -> None:
    report_dir = root / "data" / "smashmc"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "missing_learnsets.json").write_text(
        json.dumps({
            "count": len(missing),
            "pokemon": missing,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "missing_learnsets.txt").write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")
    command = (
        "python tools\\smashmc\\export_learnsets.py --skip-groudon --keep-client-connected "
        "--names " + quote(",".join(missing))
    )
    (report_dir / "export_missing_learnsets.ps1").write_text(command + "\n", encoding="utf-8")


def write_tier_report(root: Path, missing: list[str]) -> None:
    report_dir = root / "data" / "smashmc"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "missing_tiers.json").write_text(
        json.dumps({
            "count": len(missing),
            "pokemon": missing,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (report_dir / "missing_tiers.txt").write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")


def load_vanilla_ids(root: Path) -> None:
    for filename, target in (
        ("abilities.ts", VANILLA_ABILITY_IDS),
        ("moves.ts", VANILLA_MOVE_IDS),
        ("items.ts", VANILLA_ITEM_IDS),
    ):
        text = (root / "data" / filename).read_text(encoding="utf-8")
        for match in re.finditer(r"^\s*([a-z0-9]+):\s*{", text, flags=re.MULTILINE):
            target.add(match.group(1))
    abilities_text = (root / "data" / "abilities.ts").read_text(encoding="utf-8")
    ability_entries = list(re.finditer(r"^\t([a-z0-9]+):\s*{", abilities_text, flags=re.MULTILINE))
    for index, ability_match in enumerate(ability_entries):
        ability_id = ability_match.group(1)
        end = ability_entries[index + 1].start() if index + 1 < len(ability_entries) else len(abilities_text)
        body = abilities_text[ability_match.end():end]
        name_match = re.search(r'name:\s*"([^"]+)"', body)
        VANILLA_ABILITY_NAMES[ability_id] = name_match.group(1) if name_match else ability_id
    learnsets_text = (root / "data" / "learnsets.ts").read_text(encoding="utf-8")
    for species_match in re.finditer(r"^\t([a-z0-9]+):\s*{\n\t\tlearnset:\s*{", learnsets_text, flags=re.MULTILINE):
        species_id = species_match.group(1)
        start = species_match.end()
        end = learnsets_text.find("\n\t\t},", start)
        if end < 0:
            continue
        block = learnsets_text[start:end]
        moves = re.findall(r"^\t\t\t([a-z0-9]+):\s*\[", block, flags=re.MULTILINE)
        if moves:
            VANILLA_LEARNSETS[species_id] = moves


def write_ts(path: Path, export_name: str, module_name: str, table_type: str, body: str) -> None:
    path.write_text(
        f"export const {export_name}: import('../../../sim/{module_name}').{table_type} = {{\n{body}}};\n",
        encoding="utf-8",
    )


def species_body(entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        ability_parts = [f"0: {quote(entry['abilities'][0])}"]
        if len(entry["abilities"]) > 1:
            ability_parts.append(f"1: {quote(entry['abilities'][1])}")
        if len(entry["abilities"]) > 2:
            ability_parts.append(f"H: {quote(entry['abilities'][2])}")
        lines.extend([
            f"\t{ts_key(entry['id'])}: {{",
            f"\t\tnum: {-9000 - index},",
            f"\t\tname: {quote(entry['name'])},",
            f"\t\ttypes: [{', '.join(quote(t) for t in entry['types'])}],",
            "\t\tbaseStats: {" + ", ".join(f"{stat}: {entry['baseStats'][stat]}" for stat in STAT_KEYS) + "},",
            f"\t\tabilities: {{ {', '.join(ability_parts)} }},",
            "\t\theightm: 1,",
            "\t\tweightkg: 1,",
            "\t\tcolor: \"Gray\",",
            "\t\teggGroups: [\"Undiscovered\"],",
            "\t\tgen: 9,",
            "\t\tisNonstandard: \"Custom\",",
            f"\t\tspriteid: {quote(entry.get('spriteid', entry['id']))},",
        ])
        if entry.get("isMega"):
            lines.extend([
                f"\t\tbaseSpecies: {quote(entry['baseSpecies'])},",
                "\t\tforme: \"Mega\",",
                f"\t\trequiredItem: {quote(entry['requiredItem'])},",
            ])
        lines.append("\t},")
    return "\n".join(lines) + ("\n" if lines else "")


def learnsets_body(entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in entries:
        lines.append(f"\t{ts_key(entry['id'])}: {{")
        lines.append("\t\tlearnset: {")
        seen: set[str] = set()
        for move in entry["moves"]:
            move_id = to_id(move)
            if not move_id or move_id in seen:
                continue
            seen.add(move_id)
            lines.append(f"\t\t\t{ts_key(move_id)}: [\"9M\"],")
        lines.append("\t\t},")
        lines.append("\t},")
    return "\n".join(lines) + ("\n" if lines else "")


def effect_body(names: list[str], kind: str) -> str:
    lines: list[str] = []
    for index, name in enumerate(names, start=1):
        effect_id = to_id(name)
        lines.append(f"\t{ts_key(effect_id)}: {{")
        lines.append(f"\t\tnum: {-9000 - index},")
        lines.append(f"\t\tname: {quote(name)},")
        lines.append("\t\tisNonstandard: \"Custom\",")
        if kind == "ability":
            lines.append("\t\trating: 0,")
        lines.append(f"\t\tshortDesc: \"SmashMC custom {kind}; battle behavior is not implemented yet.\",")
        lines.append("\t},")
    return "\n".join(lines) + ("\n" if lines else "")


def items_body(entries: list[dict[str, Any]], names: list[str]) -> str:
    mega_items = {
        to_id(entry["requiredItem"]): entry
        for entry in entries
        if entry.get("isMega")
    }
    lines: list[str] = []
    for index, name in enumerate(names, start=1):
        item_id = to_id(name)
        lines.extend([
            f"\t{ts_key(item_id)}: {{",
            f"\t\tnum: {-9000 - index},",
            f"\t\tname: {quote(name)},",
            "\t\tisNonstandard: \"Custom\",",
        ])
        mega = mega_items.get(item_id)
        if mega:
            description = f"If held by {mega['baseSpecies']}, this item allows it to Mega Evolve."
            lines.extend([
                f"\t\tmegaStone: {{ {quote(mega['baseSpecies'])}: {quote(mega['name'])}, {quote(mega['name'])}: {quote(mega['name'])} }},",
                f"\t\titemUser: [{quote(mega['baseSpecies'])}, {quote(mega['name'])}],",
                "\t\tonTakeItem(item, source) {",
                "\t\t\treturn !item.megaStone?.[source.baseSpecies.baseSpecies];",
                "\t\t},",
                f"\t\tshortDesc: {quote(description)},",
            ])
        else:
            lines.append("\t\tshortDesc: \"SmashMC custom item; battle behavior is not implemented yet.\",")
        lines.append("\t},")
    return "\n".join(lines) + ("\n" if lines else "")


def moves_body(moves: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, move in enumerate(moves, start=1):
        battle = move.get("battle", {})
        flags = dict(move.get("flags", {}))
        if move["target"] not in {"self", "allySide", "allyTeam"}:
            flags.update({"protect": 1, "mirror": 1})
        flags.update(battle.get("flags", {}))
        pp = battle.get("pp", move["pp"])
        priority = battle.get("priority", move["priority"])
        target = battle.get("target", move["target"])
        lines.extend([
            f"\t{ts_key(move['id'])}: {{",
            f"\t\tnum: {-9000 - index},",
            f"\t\tname: {quote(move['name'])},",
            "\t\tisNonstandard: \"Custom\",",
            f"\t\taccuracy: {json.dumps(move['accuracy'])},",
            f"\t\tbasePower: {move['basePower']},",
            f"\t\tcategory: {quote(move['category'])},",
            f"\t\tpp: {pp},",
            f"\t\tpriority: {priority},",
            f"\t\tflags: {json.dumps(flags, ensure_ascii=False)},",
            f"\t\ttarget: {quote(target)},",
            f"\t\ttype: {quote(move['type'])},",
            f"\t\tdesc: {quote(move['desc'])},",
            f"\t\tshortDesc: {quote(move['shortDesc'])},",
        ])
        for key, value in battle.items():
            if key in {"flags", "pp", "priority", "target"}:
                continue
            lines.append(f"\t\t{key}: {json.dumps(value, ensure_ascii=False)},")
        lines.extend(f"\t\t{line}" for line in raw_effect(move["id"]))
        lines.append("\t},")
    return "\n".join(lines) + ("\n" if lines else "")


def formats_data_body(entries: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for entry in entries:
        lines.extend([
            f"\t{ts_key(entry['id'])}: {{",
            "\t\tisNonstandard: \"Custom\",",
            f"\t\ttier: {quote(entry['tier'])},",
            "\t},",
        ])
    return "\n".join(lines) + ("\n" if lines else "")


def write_mod_files(root: Path, entries: list[dict[str, Any]]) -> None:
    mod_dir = root / "data" / "mods" / "gen9smashmc"
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "scripts.ts").write_text(
        "export const Scripts: ModdedBattleScriptsData = {\n\tgen: 9,\n\tinherit: 'gen9',\n};\n",
        encoding="utf-8",
    )
    write_ts(mod_dir / "pokedex.ts", "Pokedex", "dex-species", "ModdedSpeciesDataTable", species_body(entries))
    write_ts(mod_dir / "learnsets.ts", "Learnsets", "dex-species", "ModdedLearnsetDataTable", learnsets_body(entries))
    write_ts(
        mod_dir / "formats-data.ts",
        "FormatsData",
        "dex-species",
        "ModdedSpeciesFormatsDataTable",
        formats_data_body(entries),
    )

    abilities = sorted({
        ability
        for entry in entries
        for ability in entry["abilities"]
        if to_id(ability) not in VANILLA_ABILITY_IDS
    }, key=to_id)
    moves_by_id = {
        move["id"]: move
        for entry in entries
        for move in entry["customMoves"]
    }
    moves = [moves_by_id[move_id] for move_id in sorted(moves_by_id)]
    items = sorted({
        item
        for entry in entries
        for item in entry["items"]
        if to_id(item) not in VANILLA_ITEM_IDS
    }, key=to_id)

    write_ts(mod_dir / "abilities.ts", "Abilities", "dex-abilities", "ModdedAbilityDataTable", effect_body(abilities, "ability"))
    write_ts(mod_dir / "moves.ts", "Moves", "dex-moves", "ModdedMoveDataTable", moves_body(moves))
    write_ts(mod_dir / "items.ts", "Items", "dex-items", "ModdedItemDataTable", items_body(entries, items))


def run(args: argparse.Namespace) -> int:
    root = repo_root()
    input_path = root / "data" / "smashmc" / "custom_pokemon.json"
    learnsets_path = root / "data" / "smashmc" / "learnsets.json"
    if not input_path.exists():
        raise RuntimeError(f"Missing {input_path}. Run export.py first.")

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    raw_entries = raw.get("pokemon")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise RuntimeError(f"{input_path} contains no Pokemon entries.")
    if not learnsets_path.exists():
        raise RuntimeError(f"Missing {learnsets_path}. Run tools/smashmc/export_learnsets.py first.")
    learnsets = json.loads(learnsets_path.read_text(encoding="utf-8"))
    if not isinstance(learnsets, dict):
        raise RuntimeError(f"{learnsets_path} must contain an object.")

    load_vanilla_ids(root)
    missing = missing_learnset_names(raw_entries, learnsets)
    missing_tiers = missing_tier_names(raw_entries)
    write_learnset_report(root, missing)
    write_tier_report(root, missing_tiers)
    if missing and args.report_learnsets:
        print(f"{len(missing)} Pokemon are missing learnsets. See data/smashmc/missing_learnsets.txt")
        return 1
    if missing and not args.allow_missing_learnsets:
        preview = ", ".join(missing[:5])
        suffix = "" if len(missing) <= 5 else f", ... plus {len(missing) - 5} more"
        raise RuntimeError(
            f"{len(missing)} Pokemon are missing moves: {preview}{suffix}. "
            "See data/smashmc/missing_learnsets.txt or run data/smashmc/export_missing_learnsets.ps1."
        )

    entries: list[dict[str, Any]] = []
    for raw_entry in raw_entries:
        if entry_name(raw_entry) in missing:
            continue
        entries.append(normalize_entry(raw_entry, learnsets))
    entries.sort(key=lambda entry: entry["id"])
    incomplete_moves = sorted({
        move["name"]
        for entry in entries
        for move in entry["customMoves"]
        if not move["metadataComplete"]
    }, key=to_id)
    database = {
        "schema_version": 1,
        "source": raw.get("source", "SmashMC Discord"),
        "incomplete": bool(missing),
        "missing_learnsets": missing,
        "missing_tiers": missing_tiers,
        "missing_move_metadata": incomplete_moves,
        "pokemon": entries,
    }
    db_path = root / "data" / "smashmc" / "smash_database.json"
    db_path.write_text(json.dumps(database, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "data" / "smashmc" / "missing_move_metadata.json").write_text(
        json.dumps({"count": len(incomplete_moves), "moves": incomplete_moves}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_mod_files(root, entries)
    from tools.smashmc.build_client_data import main as build_client_data
    build_client_data()
    print(f"Generated {len(entries)} SmashMC Pokemon into data/mods/gen9smashmc")
    if missing:
        print(f"Skipped {len(missing)} Pokemon with missing learnsets.")
    if missing_tiers:
        print(f"{len(missing_tiers)} Pokemon have no tier in Discord evidence. See data/smashmc/missing_tiers.txt")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-learnsets", action="store_true", help="Write missing learnset reports and exit without generating mod files.")
    parser.add_argument("--allow-missing-learnsets", action="store_true", help="Generate a partial mod by skipping Pokemon whose Minecraft learnsets have not been exported.")
    return parser


def main() -> int:
    try:
        return run(build_parser().parse_args())
    except Exception as error:
        print(f"build_database.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
