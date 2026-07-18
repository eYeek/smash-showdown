'use strict';

const https = require('https');
const fs = require('fs');
const path = require('path');
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
	replays: `${publicHost}/replays`,
	users: 'pokemonshowdown.com/users',
};

exports.localreplays = true;

// Smash Showdown does not run a dedicated login server yet.
exports.noguestsecurity = true;
exports.loginserver = 'https://play.pokemonshowdown.com/';
exports.requireregisterednames = true;

exports.customhttpresponse = function customHttpResponse(req, res) {
	if (!req.url) return false;

	const replayMatch = req.url.match(/^\/replays(?:\/([A-Za-z0-9-]+)(?:\.json)?)?(?:[?#].*)?$/);
	if (replayMatch) {
		const replayid = replayMatch[1]?.toLowerCase();
		if (!replayid) {
			res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'});
			res.end(renderReplayIndex());
			return true;
		}
		const replayFile = path.join(__dirname, '..', 'logs', 'replays', `${replayid}.json`);
		fs.readFile(replayFile, 'utf8', (error, data) => {
			if (error) {
				res.writeHead(404, {'Content-Type': 'text/plain; charset=utf-8'});
				res.end('Replay not found.');
				return;
			}
			if (req.url.includes('.json')) {
				res.writeHead(200, {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'});
				res.end(data);
				return;
			}
			let replay;
			try {
				replay = JSON.parse(data);
			} catch {
				res.writeHead(500, {'Content-Type': 'text/plain; charset=utf-8'});
				res.end('Replay data is invalid.');
				return;
			}
			res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'});
			res.end(renderReplay(replay));
		});
		return true;
	}

	if (!/^\/~~[^/]+\/action\.php(?:\?|$)/.test(req.url)) return false;

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
			...(req.headers.cookie ? {Cookie: req.headers.cookie} : {}),
		},
		timeout: 15000,
	}, upstreamRes => {
		let data = '';
		upstreamRes.setEncoding('utf8');
		upstreamRes.on('data', chunk => {
			data += chunk;
		});
		upstreamRes.on('end', () => {
			const headers = {
				'Content-Type': upstreamRes.headers['content-type'] || 'text/plain; charset=utf-8',
				'Cache-Control': 'no-store',
			};
			const setCookie = upstreamRes.headers['set-cookie'];
			if (setCookie) {
				headers['Set-Cookie'] = setCookie.map(cookie =>
					cookie.replace(/;\s*Domain=[^;]+/i, '')
				);
			}
			res.writeHead(upstreamRes.statusCode || 200, headers);
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

function escapeHTML(value) {
	return String(value ?? '').replace(/[&<>"]/g, char => ({
		'&': '&amp;',
		'<': '&lt;',
		'>': '&gt;',
		'"': '&quot;',
	}[char]));
}

function escapeReplayLog(value) {
	return String(value ?? '').replace(/\//g, '\\/');
}

function renderReplayIndex() {
	return `<!DOCTYPE html>
<meta charset="utf-8" />
<title>Smash Showdown replays</title>
<body style="font-family:Verdana,sans-serif;padding:24px">
<h1>Smash Showdown replays</h1>
<p>Replays are available by direct link after a battle is uploaded.</p>
</body>`;
}

function renderReplay(replay) {
	const players = Array.isArray(replay.players) ? replay.players : [];
	const p1 = players[0] || 'Player 1';
	const p2 = players[1] || 'Player 2';
	const title = `${replay.format || 'Battle'} replay: ${p1} vs. ${p2}`;
	return `<!DOCTYPE html>
<meta charset="utf-8" />
<title>${escapeHTML(title)}</title>
<style>
html,body{font-family:Verdana,sans-serif;font-size:10pt;margin:0;padding:0}
body{padding:12px 0}
.wrapper{max-width:1180px;margin:0 auto}
.replay-title{text-align:center;font-weight:normal}
</style>
<div class="wrapper replay-wrapper">
<input type="hidden" name="replayid" value="${escapeHTML(replay.id)}" />
<div class="battle"></div><div class="battle-log"></div><div class="replay-controls"></div><div class="replay-controls-2"></div>
<h1 class="replay-title"><strong>${escapeHTML(replay.format || 'Battle')}</strong><br />${escapeHTML(p1)} vs. ${escapeHTML(p2)}</h1>
<script type="text/plain" class="battle-log-data">${escapeReplayLog(replay.log)}</script>
</div>
<script>
let daily = Math.floor(Date.now()/1000/60/60/24);
document.write('<script src="https://${exports.routes.client}/js/replay-embed.js?version'+daily+'"><'+'/script>');
</script>`;
}

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
