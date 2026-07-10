'use strict';

const assert = require('../assert');
const common = require('../common');

const smash = common.mod('gen9smashmc');
let battle;

describe('SmashMC custom moves', () => {
	afterEach(() => {
		battle?.destroy();
		battle = null;
	});

	it('loads representative standard and bespoke effects', () => {
		const dex = smash.dex;
		assert.equal(dex.moves.get('shadowinfusion').volatileStatus, 'leechseed');
		assert.deepEqual(dex.moves.get('angeliclance').drain, [45, 100]);
		assert.deepEqual(dex.moves.get('supernovastrike').recoil, [50, 100]);
		assert.equal(dex.moves.get('etherealassault').multihit, 3);
		assert.equal(dex.moves.get('prismaticonslaught').priority, 3);
		assert.equal(dex.moves.get('fullmoonscurse').target, 'allAdjacentFoes');
		assert.equal(typeof dex.moves.get('aquaticinferno').basePowerCallback, 'function');
		assert.equal(typeof dex.moves.get('dimensionaldistortion').onHit, 'function');
		assert.equal(dex.moves.get('phantomsgrudge').status, 'tox');
		assert.equal(dex.moves.get('thunderousphoenix').priority, 1);
		assert.equal(dex.moves.get('thunderousphoenix').critRatio, 4);
		assert.deepEqual(dex.moves.get('thunderousphoenix').recoil, [30, 100]);
	});

	it('applies Shadow Infusion Leech Seed in battle', () => {
		battle = smash.createBattle([[
			{ species: 'Mew', ability: 'synchronize', moves: ['shadowinfusion'] },
		], [
			{ species: 'Chansey', ability: 'naturalcure', moves: ['splash'] },
		]]);
		battle.makeChoices('move shadowinfusion', 'move splash');
		assert(battle.p2.active[0].volatiles['leechseed']);
	});

	it('applies exact stat changes and self-trapping setup effects', () => {
		battle = smash.createBattle([[
			{ species: 'Mew', ability: 'synchronize', moves: ['underworldawakened'] },
		], [
			{ species: 'Chansey', ability: 'naturalcure', moves: ['splash'] },
		]]);
		battle.makeChoices('move underworldawakened', 'move splash');
		const user = battle.p1.active[0];
		assert.equal(user.boosts.atk, 2);
		assert.equal(user.boosts.spe, 2);
		assert.equal(user.boosts.spd, -1);
		assert(user.trapped);
	});

	it('uses burned-target power for Aquatic Inferno', () => {
		const move = smash.dex.moves.get('aquaticinferno');
		assert.equal(move.basePowerCallback(null, { status: '' }), 105);
		assert.equal(move.basePowerCallback(null, { status: 'brn' }), 130);
	});

	it('uses canonical Mega formes and generated Mega Stones', () => {
		const mega = smash.dex.species.get('Espeon-Mega');
		const stone = smash.dex.items.get('Espeonite');
		assert.equal(mega.baseSpecies, 'Espeon');
		assert.equal(mega.forme, 'Mega');
		assert.equal(mega.requiredItem, 'Espeonite');
		assert.equal(stone.megaStone.Espeon, 'Espeon-Mega');

		battle = smash.createBattle([[
			{ species: 'Espeon', ability: 'synchronize', item: 'espeonite', moves: ['psychic'] },
		], [
			{ species: 'Chansey', ability: 'naturalcure', moves: ['splash'] },
		]]);
		battle.makeChoices('move psychic mega', 'move splash');
		assert.equal(battle.p1.active[0].species.name, 'Espeon-Mega');
	});
});
