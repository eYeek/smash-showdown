"""Compact descriptions for SmashMC custom moves."""

from __future__ import annotations

from typing import Any


MAX_SHORT_DESC = 80

STAT_NAMES = {
    "atk": "Atk",
    "def": "Def",
    "spa": "SpA",
    "spd": "SpD",
    "spe": "Spe",
    "accuracy": "Acc",
    "evasion": "Eva",
}

STATUS_NAMES = {
    "brn": "burns",
    "frz": "freezes",
    "par": "paralyzes",
    "psn": "poisons",
    "tox": "badly poisons",
    "slp": "sleeps",
}

WEATHER_NAMES = {
    "raindance": "rain",
    "sunnyday": "sun",
    "sandstorm": "sand",
    "snow": "snow",
    "hail": "hail",
}

TERRAIN_NAMES = {
    "electricterrain": "Electric Terrain",
    "grassyterrain": "Grassy Terrain",
    "mistyterrain": "Misty Terrain",
    "psychicterrain": "Psychic Terrain",
}

SIDE_CONDITION_NAMES = {
    "spikes": "Spikes",
    "toxicspikes": "Toxic Spikes",
    "stealthrock": "Stealth Rock",
    "stickyweb": "Sticky Web",
}

VOLATILE_NAMES = {
    "leechseed": "Leech Seeds target",
    "partiallytrapped": "Traps and damages target",
}

SPECIAL_SHORT_DESCS = {
    "eternaldamnation": "Traps target; deals 10% max HP each turn.",
    "fairykingscry": "Charges turn 1; then raises Atk, Def, Spe by 2.",
    "fullmoonscurse": "Does not check accuracy. Hits adjacent foes.",
    "guardiansideals": "Raises Def, SpA, SpD by 1; cures user's status.",
    "chaoticthrashing": "User is locked in, then confused.",
    "dimensionaldistortion": "Clears terrain on hit.",
    "draconicstrike": "Removes user's Dragon typing after use.",
    "illusionistsmasterpiece": "User transforms after the move.",
    "leviathanswrath": "User falls asleep after use.",
    "raginginferno": "Locks user for 2 turns; confuses user after.",
    "shimmeringsakura": "Lowers target Def, SpD by 1; heals user.",
    "spearofanguish": "Target loses 1/12 max HP each turn until switch.",
    "surgingcurrents": "Target loses 1/16 max HP; 10% paralysis each turn.",
    "tsunamistrike": "No additional effect.",
    "undyinggrudge": "Target loses 1/12 max HP each turn until switch.",
    "volcanicvoltage": "Becomes Fire type in sun.",
    "wingsofjustice": "Traps target for 2 turns; damages each turn.",
    "wishfulgrace": "Cures party status; user loses 1/2 HP; sets Wish.",
}


def percent(fraction: Any) -> str:
    if not isinstance(fraction, (list, tuple)) or len(fraction) != 2:
        return ""
    numerator, denominator = fraction
    if not denominator:
        return ""
    value = round(numerator * 100 / denominator)
    return f"{value}%"


def format_boosts(boosts: dict[str, Any], subject: str = "") -> str:
    if not boosts:
        return ""
    parts = []
    for stat, amount in boosts.items():
        name = STAT_NAMES.get(stat, stat)
        sign = "+" if amount > 0 else ""
        parts.append(f"{sign}{amount} {name}")
    joined = ", ".join(parts)
    return f"{subject}{joined}".strip()


def secondary_desc(effect: dict[str, Any]) -> str:
    chance = effect.get("chance")
    prefix = f"{chance}% " if chance else ""
    if effect.get("status"):
        return f"{prefix}{STATUS_NAMES.get(effect['status'], effect['status'])} target"
    if effect.get("boosts"):
        return f"{prefix}{format_boosts(effect['boosts'], 'target ')}"
    self_effect = effect.get("self")
    if isinstance(self_effect, dict):
        if self_effect.get("boosts"):
            return f"{prefix}{format_boosts(self_effect['boosts'], 'user ')}"
        if self_effect.get("status"):
            return f"{prefix}{STATUS_NAMES.get(self_effect['status'], self_effect['status'])} user"
    return ""


def shorten(parts: list[str], fallback: str) -> str:
    parts = [part.rstrip(".") for part in parts if part]
    if not parts:
        return fallback
    chosen: list[str] = []
    for part in parts:
        candidate = "; ".join([*chosen, part])
        if len(candidate) <= MAX_SHORT_DESC:
            chosen.append(part)
        elif not chosen:
            return part[:MAX_SHORT_DESC - 3].rstrip() + "..."
        else:
            break
    return "; ".join(chosen) + "."


def compact_move_short_desc(move: dict[str, Any]) -> str:
    move_id = str(move.get("id", ""))
    if move_id in SPECIAL_SHORT_DESCS:
        return SPECIAL_SHORT_DESCS[move_id]

    battle = move.get("battle", {}) if isinstance(move.get("battle"), dict) else {}
    parts: list[str] = []

    priority = battle.get("priority", move.get("priority", 0))
    if priority:
        parts.append(f"{priority:+} priority")
    if battle.get("flags", {}).get("charge") or move.get("flags", {}).get("charge"):
        parts.append("Charges turn 1")
    if move.get("accuracy") is True and move.get("basePower", 0):
        parts.append("Does not check accuracy")
    if battle.get("target", move.get("target")) == "allAdjacentFoes":
        parts.append("Hits adjacent foes")

    crit_ratio = battle.get("critRatio")
    if crit_ratio:
        parts.append("Always crits" if crit_ratio >= 4 else "High crit ratio")

    multihit = battle.get("multihit")
    if isinstance(multihit, int):
        parts.append(f"Hits {multihit} times")
    elif isinstance(multihit, list) and len(multihit) == 2:
        parts.append(f"Hits {multihit[0]}-{multihit[1]} times")

    if battle.get("status"):
        parts.append(f"{STATUS_NAMES.get(battle['status'], battle['status']).capitalize()} target")
    if battle.get("boosts"):
        subject = "User " if battle.get("target", move.get("target")) == "self" else "Target "
        parts.append(format_boosts(battle["boosts"], subject))
    if battle.get("self", {}).get("boosts"):
        parts.append(format_boosts(battle["self"]["boosts"], "User "))

    secondary = battle.get("secondary")
    if isinstance(secondary, dict):
        parts.append(secondary_desc(secondary))
    for secondary in battle.get("secondaries", []) or []:
        if isinstance(secondary, dict):
            parts.append(secondary_desc(secondary))

    drain = percent(battle.get("drain"))
    if drain:
        parts.append(f"Heals {drain} damage dealt")
    recoil = percent(battle.get("recoil"))
    if recoil:
        parts.append(f"User loses {recoil} recoil")
    heal = percent(battle.get("heal"))
    if heal:
        parts.append(f"Heals {heal} max HP")

    volatile = battle.get("volatileStatus")
    if volatile:
        parts.append(VOLATILE_NAMES.get(volatile, f"Inflicts {volatile}"))
    if battle.get("sideCondition"):
        parts.append(f"Sets {SIDE_CONDITION_NAMES.get(battle['sideCondition'], battle['sideCondition'])}")
    if battle.get("weather"):
        parts.append(f"Sets {WEATHER_NAMES.get(battle['weather'], battle['weather'])}")
    if battle.get("terrain"):
        parts.append(f"Sets {TERRAIN_NAMES.get(battle['terrain'], battle['terrain'])}")
    if battle.get("ignoreDefensive"):
        parts.append("Ignores defensive boosts")
    if battle.get("ignoreImmunity"):
        parts.append("Hits immune targets")
    if battle.get("selfSwitch"):
        parts.append("User switches out")
    if battle.get("flags", {}).get("defrost") or move.get("flags", {}).get("defrost"):
        parts.append("Thaws user")

    fallback = str(move.get("shortDesc") or move.get("desc") or "No additional effect.").strip()
    if not parts and (not fallback or len(fallback) > MAX_SHORT_DESC):
        fallback = "No additional effect."
    return shorten(parts, fallback)
