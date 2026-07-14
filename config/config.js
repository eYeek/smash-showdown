'use strict';

const https = require('https');
const {URLSearchParams} = require('url');

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
exports.requireregisterednames = true;

exports.customhttpresponse = function customHttpResponse(req, res) {
	if (!req.url || !/^\/~~[^/]+\/action\.php(?:\?|$)/.test(req.url)) return false;

	const rawBody = Buffer.isBuffer(req.body) ? req.body.toString('utf8') : '';
	const params = new URLSearchParams(rawBody);
	params.set('serverid', exports.serverid);
	if (exports.servertoken) params.set('servertoken', exports.servertoken);

	const body = params.toString();
	const upstream = https.request({
		hostname: 'play.pokemonshowdown.com',
		path: '/action.php',
		method: 'POST',
		headers: {
			'Content-Type': 'application/x-www-form-urlencoded',
			'Content-Length': Buffer.byteLength(body),
			'User-Agent': 'Smash Showdown login proxy',
		},
		timeout: 15000,
	}, upstreamRes => {
		let data = '';
		upstreamRes.setEncoding('utf8');
		upstreamRes.on('data', chunk => {
			data += chunk;
		});
		upstreamRes.on('end', () => {
			res.writeHead(upstreamRes.statusCode || 200, {
				'Content-Type': upstreamRes.headers['content-type'] || 'text/plain; charset=utf-8',
				'Cache-Control': 'no-store',
			});
			res.end(data);
		});
	});
	upstream.on('timeout', () => upstream.destroy(new Error('Login server timed out')));
	upstream.on('error', error => {
		res.writeHead(502, {
			'Content-Type': 'text/plain; charset=utf-8',
			'Cache-Control': 'no-store',
		});
		res.end(`]${JSON.stringify({error: `Could not contact the Pokemon Showdown login server: ${error.message}`})}`);
	});
	upstream.end(body);
	return true;
};

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
