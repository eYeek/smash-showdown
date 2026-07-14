function getSmashCustomSpecies(set: any, dex: any) {
	let species = dex.species.get(set.species);
	if (species.isNonstandard === "Custom") return species;

	const item = dex.items.get(set.item);
	const megaStone = item.megaStone;
	if (!megaStone) return null;

	let megaSpeciesName = "";
	if (typeof megaStone === "string") {
		megaSpeciesName = megaStone;
	} else {
		megaSpeciesName = megaStone[species.baseSpecies] || megaStone[species.name] || "";
	}
	if (!megaSpeciesName) return null;

	species = dex.species.get(megaSpeciesName);
	return species.isNonstandard === "Custom" ? species : null;
}

const SMASH_SPECIES_MOVE_BANS: {[speciesid: string]: {[moveid: string]: string}} = {
	espeonmega: {expandingforce: "Expanding Force"},
	jolteonmega: {risingvoltage: "Rising Voltage"},
};

function validateSmashSpeciesMoveBans(team: any[], dex: any) {
	const problems = [];
	for (const set of team) {
		const species = getSmashCustomSpecies(set, dex);
		if (!species) continue;
		const bannedMoves = SMASH_SPECIES_MOVE_BANS[species.id];
		if (!bannedMoves) continue;

		for (const moveName of set.moves || []) {
			const moveid = dex.moves.get(moveName).id;
			if (!bannedMoves[moveid]) continue;
			problems.push(`${species.name} is not allowed to have ${bannedMoves[moveid]}.`);
		}
	}
	return problems;
}

function countSmashCustoms(formatName: string, team: any[], dex: any) {
	const custom = [];
	for (const set of team) {
		const species = getSmashCustomSpecies(set, dex);
		if (species) custom.push(species);
	}

	const problems = [];
	if (formatName === "SOU") {
		const illegalCustom = custom.filter(species => !["OU", "UU"].includes(species.tier));
		if (illegalCustom.length) {
			problems.push(
				`Smash OU only allows one custom SmashMC OU Pokemon. ` +
				`${illegalCustom.map(species => species.name).join(", ")} ` +
				`${illegalCustom.length === 1 ? "is" : "are"} not Smash OU legal.`
			);
		}
		if (custom.length > 1) {
			problems.push(`Smash OU allows only one custom SmashMC OU Pokemon. Your team has ${custom.length}.`);
		}
	} else {
		const customUbers = [];
		const customOU = [];
		const illegalCustom = [];
		for (const species of custom) {
			if (species.tier === "Uber") {
				customUbers.push(species);
			} else if (["OU", "UU"].includes(species.tier)) {
				customOU.push(species);
			} else {
				illegalCustom.push(species);
			}
		}
		if (illegalCustom.length) {
			problems.push(
				`Smash Ubers only allows custom SmashMC Uber and OU Pokemon. ` +
				`${illegalCustom.map(species => species.name).join(", ")} ` +
				`${illegalCustom.length === 1 ? "is" : "are"} not Smash Ubers legal.`
			);
		}
		if (customUbers.length > 1) {
			problems.push(`Smash Ubers allows only one custom SmashMC Uber Pokemon. Your team has ${customUbers.length}.`);
		}
		if (customOU.length > 1) {
			problems.push(`Smash Ubers allows only one custom SmashMC OU Pokemon. Your team has ${customOU.length}.`);
		}
	}
	return problems;
}

function validateSOUTeam(this: any, team: any[], options: any) {
	const problems = this.baseValidateTeam(team, options) || [];
	problems.push(...countSmashCustoms("SOU", team, this.dex));
	problems.push(...validateSmashSpeciesMoveBans(team, this.dex));
	return problems.length ? problems : null;
}

function validateSUbersTeam(this: any, team: any[], options: any) {
	const problems = this.baseValidateTeam(team, options) || [];
	problems.push(...countSmashCustoms("SUbers", team, this.dex));
	problems.push(...validateSmashSpeciesMoveBans(team, this.dex));
	return problems.length ? problems : null;
}

export const Formats: import('../sim/dex-formats').FormatList = [
	{
		section: "SmashMC",
		column: 1,
	},
	{
		name: "[Gen 9] Smash OU",
		desc: "National Dex OU with one custom SmashMC OU Pokemon allowed.",
		mod: "gen9smashmc",
		searchShow: true,
		challengeShow: true,
		tournamentShow: true,
		ruleset: ["Standard NatDex", "Terastal Clause", "+Custom"],
		banlist: [
			"ND Uber", "ND AG", "Arena Trap", "Moody", "Power Construct", "Shadow Tag", "King's Rock",
			"Quick Claw", "Razor Fang", "Assist", "Baton Pass", "Last Respects", "Shed Tail",
		],
		validateTeam: validateSOUTeam,
	},
	{
		name: "[Gen 9] Smash Ubers",
		desc: "National Dex Ubers with one custom SmashMC Uber and one custom SmashMC OU Pokemon allowed.",
		mod: "gen9smashmc",
		searchShow: true,
		challengeShow: true,
		tournamentShow: true,
		ruleset: ["Standard NatDex", "!Evasion Clause", "Evasion Moves Clause", "Evasion Items Clause", "Mega Rayquaza Clause", "Terastal Clause", "+Custom"],
		banlist: ["ND AG", "Shedinja", "Assist", "Baton Pass"],
		validateTeam: validateSUbersTeam,
	},
	{
		name: "[Gen 9] SOU",
		desc: "Legacy alias for Smash OU.",
		mod: "gen9smashmc",
		searchShow: false,
		challengeShow: false,
		tournamentShow: false,
		ruleset: ["Standard NatDex", "Terastal Clause", "+Custom"],
		banlist: [
			"ND Uber", "ND AG", "Arena Trap", "Moody", "Power Construct", "Shadow Tag", "King's Rock",
			"Quick Claw", "Razor Fang", "Assist", "Baton Pass", "Last Respects", "Shed Tail",
		],
		validateTeam: validateSOUTeam,
	},
	{
		name: "[Gen 9] SUbers",
		desc: "Legacy alias for Smash Ubers.",
		mod: "gen9smashmc",
		searchShow: false,
		challengeShow: false,
		tournamentShow: false,
		ruleset: ["Standard NatDex", "!Evasion Clause", "Evasion Moves Clause", "Evasion Items Clause", "Mega Rayquaza Clause", "Terastal Clause", "+Custom"],
		banlist: ["ND AG", "Shedinja", "Assist", "Baton Pass"],
		validateTeam: validateSUbersTeam,
	},
	{
		name: "[Gen 9] SmashMC",
		desc: "Broad local testing for SmashMC custom Pokemon data.",
		mod: "gen9smashmc",
		searchShow: false,
		challengeShow: true,
		tournamentShow: false,
		ruleset: ["Standard", "+Custom"],
	},
	{
		name: "[Gen 9] SmashMC Custom Game",
		desc: "Unrestricted local testing for SmashMC custom Pokemon data.",
		mod: "gen9smashmc",
		searchShow: false,
		challengeShow: true,
		debug: true,
		ruleset: [
			"Team Preview",
			"Cancel Mod",
			"+Custom",
			"Max Team Size = 24",
			"Max Move Count = 24",
			"Max Level = 9999",
			"Default Level = 100",
		],
	},
];
