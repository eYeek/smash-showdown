'use strict';

const isProduction = process.env.NODE_ENV === 'production';
const publicHost = process.env.SMASH_SHOWDOWN_HOST || 'smash-showdown.onrender.com';

exports.port = Number(process.env.PORT || 8000);
exports.bindaddress = '0.0.0.0';
exports.wsdeflate = null;
exports.ssl = null;
exports.proxyip = false;

exports.serverid = 'smashshowdown';
exports.servername = 'Smash Showdown';
exports.serverdesc = 'SmashMC custom Pokemon Showdown server.';

exports.routes = {
	root: publicHost,
	client: publicHost,
	dex: 'dex.pokemonshowdown.com',
	replays: 'replay.pokemonshowdown.com',
	users: 'pokemonshowdown.com/users',
};

// Smash Showdown does not run a dedicated login server yet.
exports.noguestsecurity = true;
exports.loginserver = 'https://play.pokemonshowdown.com/';

// Render free instances have limited memory. A single-process server is slower
// under heavy load, but much more stable for the first public deployment.
exports.subprocesses = isProduction ? 0 : {
	network: 0,
	simulator: 1,
	validator: 1,
	verifier: 1,
	chatdb: 1,
	modlog: 1,
	pm: 1,
	datasearch: 1,
	battlesearch: 1,
	friends: 1,
};

exports.crashguard = true;
exports.backdoor = false;
exports.repl = false;
exports.watchconfig = false;
exports.logchat = false;
exports.logchallenges = false;
exports.reportjoins = false;
exports.reportbattles = false;
exports.reportbattlejoins = false;
exports.allowrequestingties = true;
exports.disablehotpatchall = true;
