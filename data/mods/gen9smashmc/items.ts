export const Items: import('../../../sim/dex-items').ModdedItemDataTable = {
	espeonite: {
		num: -9001,
		name: "Espeonite",
		isNonstandard: "Custom",
		megaStone: { "Espeon": "Espeon-Mega", "Espeon-Mega": "Espeon-Mega" },
		itemUser: ["Espeon", "Espeon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Espeon, this item allows it to Mega Evolve.",
	},
	flareonite: {
		num: -9002,
		name: "Flareonite",
		isNonstandard: "Custom",
		megaStone: { "Flareon": "Flareon-Mega", "Flareon-Mega": "Flareon-Mega" },
		itemUser: ["Flareon", "Flareon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Flareon, this item allows it to Mega Evolve.",
	},
	glaceonite: {
		num: -9003,
		name: "Glaceonite",
		isNonstandard: "Custom",
		megaStone: { "Glaceon": "Glaceon-Mega", "Glaceon-Mega": "Glaceon-Mega" },
		itemUser: ["Glaceon", "Glaceon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Glaceon, this item allows it to Mega Evolve.",
	},
	jolteonite: {
		num: -9004,
		name: "Jolteonite",
		isNonstandard: "Custom",
		megaStone: { "Jolteon": "Jolteon-Mega", "Jolteon-Mega": "Jolteon-Mega" },
		itemUser: ["Jolteon", "Jolteon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Jolteon, this item allows it to Mega Evolve.",
	},
	leafeonite: {
		num: -9005,
		name: "Leafeonite",
		isNonstandard: "Custom",
		megaStone: { "Leafeon": "Leafeon-Mega", "Leafeon-Mega": "Leafeon-Mega" },
		itemUser: ["Leafeon", "Leafeon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Leafeon, this item allows it to Mega Evolve.",
	},
	sylveonite: {
		num: -9006,
		name: "Sylveonite",
		isNonstandard: "Custom",
		megaStone: { "Sylveon": "Sylveon-Mega", "Sylveon-Mega": "Sylveon-Mega" },
		itemUser: ["Sylveon", "Sylveon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Sylveon, this item allows it to Mega Evolve.",
	},
	umbreonite: {
		num: -9007,
		name: "Umbreonite",
		isNonstandard: "Custom",
		megaStone: { "Umbreon": "Umbreon-Mega", "Umbreon-Mega": "Umbreon-Mega" },
		itemUser: ["Umbreon", "Umbreon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Umbreon, this item allows it to Mega Evolve.",
	},
	vaporeonite: {
		num: -9008,
		name: "Vaporeonite",
		isNonstandard: "Custom",
		megaStone: { "Vaporeon": "Vaporeon-Mega", "Vaporeon-Mega": "Vaporeon-Mega" },
		itemUser: ["Vaporeon", "Vaporeon-Mega"],
		onTakeItem(item, source) {
			return !item.megaStone?.[source.baseSpecies.baseSpecies];
		},
		shortDesc: "If held by Vaporeon, this item allows it to Mega Evolve.",
	},
};
