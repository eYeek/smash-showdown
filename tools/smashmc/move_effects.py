"""Structured battle effects for documented SmashMC signature moves."""

from __future__ import annotations

from typing import Any


MOVE_EFFECTS: dict[str, dict[str, Any]] = {}


def add(ids: str, **effect: Any) -> None:
    for move_id in ids.split():
        MOVE_EFFECTS.setdefault(move_id, {}).update(effect)


add(
    "piercingjetstream vortexblast arcticcrush metallicshredder razorrapids "
    "geniusgrudge beyondthevoid momentousmagma grandcannon",
    critRatio=4,
)
add("searingscales frozenmalice primordialreckoning aquaticcleaver", critRatio=2)

for move_id, amount in {
    "angeliclance": 45,
    "divinedepletion": 40,
    "shiningflare": 35,
    "prismaticonslaught": 35,
    "piercingpermafrost": 50,
}.items():
    add(move_id, drain=[amount, 100])

for move_id, amount in {
    "supernovastrike": 50,
    "descentfromgrace": 33,
    "plasmaslash": 30,
    "boltblitz": 25,
    "soulsteeler": 50,
    "lionslightning": 50,
}.items():
    add(move_id, recoil=[amount, 100])

for move_id, hits in {
    "celestialsting": 2,
    "draconickunai": 3,
    "etherealassault": 3,
    "triplejawclamp": 3,
    "rocketsredglare": 2,
    "fivefangferocity": 5,
    "lightningbarrage": 3,
    "phantomstampede": 5,
}.items():
    add(move_id, multihit=hits)

for move_id, boosts in {
    "revenantsseverance": {"spe": 1},
    "aquaticcleaver": {"spe": 1},
    "underworldawakened": {"atk": 2, "spe": 2, "spd": -1},
    "seadragonsroar": {"atk": 1},
    "tribeamcannon": {"atk": -1, "spa": -1},
    "skyslicer": {"spe": 1},
    "beyondthevoid": {"atk": 1, "spe": 1},
    "momentousmagma": {"spe": 1},
    "flashstep": {"spe": 1},
    "hydroelectricpower": {"spa": 2, "spe": 2},
    "midnighthowl": {"atk": 1, "def": -1, "spa": 1, "spd": -1, "spe": 1},
    "overlordsobliteration": {"def": -1, "spd": -1},
    "primordialreckoning": {"def": -1, "spd": -1},
    "ascendeddarkness": {"atk": -1, "def": -1, "spd": -1},
    "slitheringserpent": {"atk": 1, "def": 1, "spe": 1},
}.items():
    add(move_id, self={"boosts": boosts})

for move_id, boosts in {
    "davyjonesanchor": {"spe": -1},
    "terraterror": {"spe": -1, "spd": -1},
    "ghoulsnightmare": {"spd": -1},
    "gravitonpulse": {"spe": -1},
    "electroshocktherapy": {"def": -1, "spd": -1},
}.items():
    add(move_id, boosts=boosts)

for move_id, chance, boosts in [
    ("skyforgedsurge", 10, {"spe": -1}),
    ("lustrouslance", 50, {"def": -1}),
    ("darkreckoning", 20, {"spd": -1}),
    ("geneticdistortion", 50, {"spd": -1}),
    ("lightninglunge", 30, {"spe": -1}),
    ("flamingcosmos", 50, {"spd": -1}),
    ("shimmeringskullsmash", 50, {"def": -1}),
]:
    add(move_id, secondary={"chance": chance, "boosts": boosts})

for move_id, chance, status in [
    ("gigatonvolcano", 80, "brn"),
    ("heavenlyblast", 30, "psn"),
    ("ancientflame", 25, "brn"),
    ("aquaticinferno", 25, "brn"),
    ("supernovastrike", 20, "brn"),
    ("venomousguillotine", 30, "psn"),
    ("roaroftheinferno", 50, "brn"),
    ("sorcererscurse", 10, "brn"),
    ("shadowsurge", 10, "par"),
    ("rocketsredglare", 10, "brn"),
    ("torrentialcurrent", 15, "par"),
    ("blacklightning", 10, "par"),
]:
    add(move_id, secondary={"chance": chance, "status": status})

add("darknessflame", status="brn", self={"volatileStatus": "mustrecharge"})
add("mechanizedvenom divinefart phantomsgrudge", status="tox")
add("smolderingsmash", secondary={"chance": 30, "self": {"status": "brn"}}, flags={"defrost": 1})
add("wraithswrath", secondary={"chance": 15, "self": {"status": "brn"}})
add("etherealassault", secondary={"chance": 10, "volatileStatus": "flinch"})
add(
    "elementalobliteration",
    secondaries=[
        {"chance": 10, "status": "brn"},
        {"chance": 10, "status": "frz"},
        {"chance": 10, "status": "par"},
    ],
)
add(
    "plumedoom",
    secondaries=[
        {"chance": 15, "status": "psn"},
        {"chance": 15, "status": "brn"},
    ],
)
add(
    "plasmablaze",
    secondaries=[
        {"chance": 10, "status": "par"},
        {"chance": 25, "self": {"boosts": {"spa": 1}}},
    ],
)

add("absolutezero", weather="snow", critRatio=4)
add("frostyfarewell frostbittenflurry", weather="snow")
add("tropicalremap", weather="raindance", terrain="grassyterrain")
add("rosewhip", sideCondition="spikes")
add("shadowinfusion", volatileStatus="leechseed")
add("fairysdarkdescent triplejawclamp tropicaltirade", volatileStatus="partiallytrapped")
add("magiciansescape", selfSwitch=True)
add("wyvernswrath", ignoreDefensive=True)
add("terrestrialrevolt", ignoreImmunity=True)
add("chaoticthrashing", self={"volatileStatus": "lockedmove"})
add("fullmoonscurse", target="allAdjacentFoes")
add("aquaticblessing guardiansideals fairykingscry infinityunleashed hydroelectricpower midnighthowl slitheringserpent underworldawakened wishfulgrace", target="self")
add("aquaticblessing", heal=[1, 2])
add("infinityunleashed", boosts={"atk": 1, "def": 1, "spa": 1, "spd": 1, "spe": 1})
add("guardiansideals", boosts={"def": 1, "spa": 1, "spd": 1})
add("fairykingscry", boosts={"atk": 2, "def": 2, "spe": 2}, flags={"charge": 1})
add("playfulhaunting", boosts={"atk": -2, "spa": -2}, selfSwitch=True)
add("soaringslash searingsmash draconickunai boltblitz thunderousphoenix", priority=1)
add("thunderousphoenix", critRatio=4, recoil=[30, 100], flags={"contact": 1})
add("prismaticonslaught", priority=3)
add("beyondthevoid", pp=1)


RAW_EFFECTS: dict[str, list[str]] = {
    "aquaticinferno": [
        "basePowerCallback(pokemon, target) {",
        "\treturn target.status === 'brn' ? 130 : 105;",
        "},",
    ],
    "undyinggrudge": [
        "volatileStatus: \"undyinggrudge\",",
        "condition: {",
        "\tonResidualOrder: 9,",
        "\tonResidual(pokemon) { this.damage(pokemon.baseMaxhp / 12, pokemon); },",
        "},",
    ],
    "spearofanguish": [
        "volatileStatus: \"spearofanguish\",",
        "condition: {",
        "\tonResidualOrder: 9,",
        "\tonResidual(pokemon) { this.damage(pokemon.baseMaxhp / 12, pokemon); },",
        "},",
    ],
    "surgingcurrents": [
        "volatileStatus: \"surgingcurrents\",",
        "condition: {",
        "\tonResidualOrder: 9,",
        "\tonResidual(pokemon) {",
        "\t\tthis.damage(pokemon.baseMaxhp / 16, pokemon);",
        "\t\tif (this.randomChance(1, 10)) pokemon.trySetStatus('par');",
        "\t},",
        "},",
    ],
    "wingsofjustice": [
        "volatileStatus: \"wingsofjustice\",",
        "condition: {",
        "\tduration: 3,",
        "\tonStart(pokemon) { pokemon.tryTrap(); },",
        "\tonResidualOrder: 9,",
        "\tonResidual(pokemon) { this.damage(pokemon.baseMaxhp / 8, pokemon); },",
        "},",
    ],
    "eternaldamnation": [
        "volatileStatus: \"eternaldamnation\",",
        "condition: {",
        "\tduration: 5,",
        "\tonStart(pokemon) { pokemon.tryTrap(); },",
        "\tonResidualOrder: 9,",
        "\tonResidual(pokemon) { this.damage(pokemon.baseMaxhp / 10, pokemon); },",
        "},",
    ],
    "magneticmaelstrom": [
        "volatileStatus: \"magneticmaelstrom\",",
        "condition: { duration: 4, onStart(pokemon) { pokemon.tryTrap(); } },",
    ],
    "dimensionaldistortion": [
        "onHit() { if (this.field.terrain) this.field.clearTerrain(); },",
    ],
    "leviathanswrath": [
        "onAfterMove(source) { if (source.hp) source.trySetStatus('slp', source); },",
    ],
    "raginginferno": [
        "self: { volatileStatus: 'raginginferno' },",
        "condition: {",
        "\tduration: 2,",
        "\tonStart(pokemon, source, effect) { this.effectState.move = effect.id; },",
        "\tonLockMove() { return this.effectState.move; },",
        "\tonEnd(pokemon) { pokemon.addVolatile('confusion'); },",
        "},",
    ],
    "aquaticblessing": [
        "onHit(pokemon) { if (pokemon.status) pokemon.cureStatus(); },",
    ],
    "shimmeringsakura": [
        "onHit(target, source) {",
        "\tthis.boost({def: -1, spd: -1}, target, source);",
        "\tthis.heal(Math.floor((target.getStat('def', false, true) + target.getStat('spd', false, true)) / 2), source);",
        "},",
    ],
    "draconicstrike": [
        "onAfterMove(source) {",
        "\tconst types = source.getTypes().filter(type => type !== 'Dragon');",
        "\tif (types.length) source.setType(types);",
        "},",
    ],
    "wishfulgrace": [
        "slotCondition: 'Wishful Grace',",
        "condition: {",
        "\tonStart(pokemon, source) {",
        "\t\tthis.effectState.hp = source.maxhp / 2;",
        "\t\tthis.effectState.startingTurn = this.getOverflowedTurnCount();",
        "\t},",
        "\tonResidualOrder: 4,",
        "\tonResidual(target) {",
        "\t\tif (this.getOverflowedTurnCount() <= this.effectState.startingTurn) return;",
        "\t\ttarget.side.removeSlotCondition(this.getAtSlot(this.effectState.sourceSlot), 'wishfulgrace');",
        "\t},",
        "\tonEnd(target) {",
        "\t\tif (target && !target.fainted) this.heal(this.effectState.hp, target, target);",
        "\t},",
        "},",
        "onTry(pokemon) { if (pokemon.hp <= pokemon.maxhp / 2) return false; },",
        "onHit(pokemon) {",
        "\tfor (const ally of pokemon.side.pokemon) if (ally.status) ally.cureStatus();",
        "\tthis.directDamage(Math.floor(pokemon.maxhp / 2), pokemon, pokemon);",
        "},",
    ],
    "guardiansideals": [
        "onHit(pokemon) { if (pokemon.status) pokemon.cureStatus(); },",
    ],
    "fairykingscry": [
        "onTryMove(attacker, defender, move) {",
        "\tif (attacker.removeVolatile(move.id)) return;",
        "\tthis.add('-prepare', attacker, move.name);",
        "\tif (!this.runEvent('ChargeMove', attacker, defender, move)) return;",
        "\tattacker.addVolatile('twoturnmove', defender);",
        "\treturn null;",
        "},",
    ],
    "volcanicvoltage": [
        "onModifyType(move) {",
        "\tif (['sunnyday', 'desolateland'].includes(this.field.effectiveWeather())) move.type = 'Fire';",
        "},",
    ],
    "illusionistsmasterpiece": [
        "onHit(target, source) { if (!target.fainted) source.transformInto(target); },",
    ],
    "underworldawakened": [
        "volatileStatus: 'underworldawakened',",
        "condition: { onTrapPokemon(pokemon) { pokemon.tryTrap(); } },",
    ],
    "infinityunleashed": [
        "volatileStatus: 'infinityunleashed',",
        "condition: { onTrapPokemon(pokemon) { pokemon.tryTrap(); } },",
    ],
}


NO_ADDITIONAL_EFFECT = {
    "tsunamistrike",
}


def battle_effect(move_id: str) -> dict[str, Any]:
    return dict(MOVE_EFFECTS.get(move_id, {}))


def raw_effect(move_id: str) -> list[str]:
    return list(RAW_EFFECTS.get(move_id, []))
