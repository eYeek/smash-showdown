'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('../assert');

describe('SmashMC client search index', () => {
	it('preserves every upstream fuzzy-search alias after merging custom data', () => {
		const searchPath = path.resolve(__dirname, '../../client/play.pokemonshowdown.com/data/search-index.js');
		const source = fs.readFileSync(searchPath, 'utf8');
		const baseSource = source.split('/* SmashMC generated client data start */')[0];
		const context = { exports: {} };
		vm.runInNewContext(baseSource, context);

		const before = context.exports.BattleSearchIndex;
		delete require.cache[require.resolve(searchPath)];
		const generated = require(searchPath);
		const after = generated.BattleSearchIndex;
		const positions = new Map();
		for (const [index, row] of after.entries()) {
			const key = `${row[0]}|${row[1]}`;
			if (!positions.has(key)) positions.set(key, []);
			positions.get(key).push(index);
		}

		const occurrence = new Map();
		for (const row of before) {
			const key = `${row[0]}|${row[1]}`;
			const count = occurrence.get(key) || 0;
			occurrence.set(key, count + 1);
			if (typeof row[2] !== 'number') continue;

			const mergedRow = after[positions.get(key)[count]];
			const oldTarget = before[row[2]];
			const newTarget = after[mergedRow[2]];
			assert.equal(newTarget[0], oldTarget[0], `Alias ${row[0]} changed target`);
			assert.equal(newTarget[1], oldTarget[1], `Alias ${row[0]} changed type`);
		}
		assert.equal(after.length, generated.BattleSearchIndexOffset.length);
	});
});
