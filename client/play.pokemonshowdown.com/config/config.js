(() => {
	const local = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
	const host = location.host || 'localhost:8000';
	const protocol = local ? 'http' : 'https';
	const port = local ? Number(location.port || 8000) : 443;

	window.Config = {
		version: 'smash-public-registered-login',
		requireRegisteredNames: true,
		sockjsprefix: '/showdown',
		bannedHosts: [],
		whitelist: [],
		routes: {
			root: host,
			client: host,
			assets: 'play.pokemonshowdown.com',
			dex: 'dex.pokemonshowdown.com',
			replays: 'replay.pokemonshowdown.com',
			users: 'pokemonshowdown.com/users',
			teams: 'teams.pokemonshowdown.com',
		},
		defaultserver: {
			id: 'smashshowdown',
			host: location.hostname || 'localhost',
			port,
			httpport: port,
			altport: port,
			protocol,
			prefix: '/showdown',
			registered: true,
		},
		customcolors: {},
	};
})();
