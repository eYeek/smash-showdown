#!/usr/bin/env python3
"""Export SmashMC learnsets from the in-game /movelist command.

Discord does not contain authoritative learnsets. This exporter reads Pokemon
from data/smashmc/custom_pokemon.json, logs into SmashMC through a Minecraft
client backend, runs /groudon once to leave the hub, then queries:

    /movelist <PokemonNameWithSpacesRemoved>

It writes resumable progress to data/smashmc/learnsets.json.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


COLOR_CODE_RE = re.compile(r"(?:\u00c2?\u00a7.|&[0-9A-FK-ORa-fk-or]|\?[0-9A-FK-ORa-fk-or])")
MOVE_NAME_RE = re.compile(r'name:\s*"([^"]+)"')
CUSTOM_MOVE_ID_RE = re.compile(r"[a-z][a-z0-9_]*")
URL_RE = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
DEFAULT_OUTPUT = Path("data/smashmc/learnsets.json")
DEFAULT_FAILURE_LOG = Path("data/smashmc/learnset_failures.json")
_KNOWN_MOVE_IDS: set[str] | None = None


@dataclass
class MovelistParseResult:
    moves: list[str]
    raw_lines: list[str]
    cleaned_lines: list[str]
    stop_reason: str


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def command_name(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def is_mega_form_name(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return normalized.startswith("mega ") or normalized.endswith(" mega") or " mega " in normalized


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def strip_minecraft_formatting(text: str) -> str:
    return COLOR_CODE_RE.sub("", text).replace("\r", "").strip()


def clean_evidence(lines: list[str]) -> list[str]:
    return [cleaned for line in lines if (cleaned := strip_minecraft_formatting(line))]


def known_move_ids() -> set[str]:
    global _KNOWN_MOVE_IDS
    if _KNOWN_MOVE_IDS is not None:
        return _KNOWN_MOVE_IDS

    root = repo_root()
    move_ids: set[str] = set()
    for path in [root / "data" / "moves.ts", *sorted((root / "data" / "mods").glob("*/moves.ts"))]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        move_ids.update(to_id(match.group(1)) for match in MOVE_NAME_RE.finditer(text))
    _KNOWN_MOVE_IDS = move_ids
    return move_ids


def is_ignored_chat_line(line: str) -> bool:
    if not line:
        return True
    lowered = line.lower()
    ignored_fragments = (
        "vote and get rewards",
        "vote for the server",
        "with /vote",
        "broadcast",
        "joined the game",
        "left the game",
        "received",
        "balance",
        "money",
        "coins",
    )
    return URL_RE.search(line) is not None or any(fragment in lowered for fragment in ignored_fragments)


def is_move_token(token: str) -> bool:
    token = token.strip()
    if not token or URL_RE.search(token):
        return False
    if "/" in token or ":" in token:
        return False
    if to_id(token) in known_move_ids():
        return True
    return CUSTOM_MOVE_ID_RE.fullmatch(token) is not None


def split_move_line(line: str) -> tuple[list[str], str | None]:
    if is_ignored_chat_line(line):
        return [], f"ignored chat resumed: {line}"
    tokens = [token.strip() for token in line.split(",")]
    if not tokens or any(not token for token in tokens):
        return [], f"invalid comma-separated move line: {line}"
    invalid = [token for token in tokens if not is_move_token(token)]
    if invalid:
        return [], f"unrecognised move token: {invalid[0]}"
    return tokens, None


def parse_movelist_details(pokemon_name: str, lines: list[str]) -> MovelistParseResult:
    """Parse a /movelist response while preserving move order."""

    header_re = re.compile(rf"^{re.escape(pokemon_name)}'?s\s+Move\s+List\s*:?\s*$", re.IGNORECASE)
    moves: list[str] = []
    seen: set[str] = set()
    in_list = False
    cleaned_lines: list[str] = []
    stop_reason = "move list header not found"

    for raw_line in lines:
        line = strip_minecraft_formatting(raw_line)
        if line:
            cleaned_lines.append(line)
        if not line:
            continue
        if header_re.match(line) or re.search(r"\bMove\s+List\s*:?\s*$", line, re.IGNORECASE):
            in_list = True
            stop_reason = "reached end of captured chat"
            continue
        if not in_list:
            continue
        if line.startswith("/") or re.search(r"\b(error|unknown command|not found|no moves)\b", line, re.IGNORECASE):
            stop_reason = f"server returned non-movelist response: {line}"
            break

        line_moves, reason = split_move_line(line)
        if reason:
            stop_reason = reason
            break
        for move in line_moves:
            move_id = to_id(move)
            if move_id in seen:
                continue
            moves.append(move)
            seen.add(move_id)

    if moves and stop_reason == "move list header not found":
        stop_reason = "reached end of captured chat"
    return MovelistParseResult(moves=moves, raw_lines=lines, cleaned_lines=cleaned_lines, stop_reason=stop_reason)


def parse_movelist_response(pokemon_name: str, lines: list[str]) -> list[str]:
    return parse_movelist_details(pokemon_name, lines).moves


def load_custom_pokemon(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise RuntimeError(f"Missing {path}. Run export.py first.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("pokemon")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError(f"{path} contains no Pokemon entries.")

    pokemon: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        pokemon_id = to_id(name)
        if not name or not pokemon_id or pokemon_id in seen:
            continue
        if is_mega_form_name(name):
            continue
        pokemon.append({"id": pokemon_id, "name": name, "command_name": command_name(name)})
        seen.add(pokemon_id)
    return pokemon


def load_requested_pokemon(names: str) -> list[dict[str, str]]:
    pokemon: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_name in names.split(","):
        name = raw_name.strip()
        pokemon_id = to_id(name)
        if not name or not pokemon_id or pokemon_id in seen:
            continue
        if is_mega_form_name(name):
            continue
        pokemon.append({"id": pokemon_id, "name": name, "command_name": command_name(name)})
        seen.add(pokemon_id)
    if not pokemon:
        raise RuntimeError("--names did not contain any Pokemon names.")
    return pokemon


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


class MinecraftBackend:
    async def connect(self) -> None:
        raise NotImplementedError

    def status(self) -> dict[str, Any]:
        raise NotImplementedError

    async def refresh_status(self) -> dict[str, Any]:
        return self.status()

    async def close(self) -> None:
        raise NotImplementedError

    async def command(self, command: str, wait_seconds: float) -> list[str]:
        raise NotImplementedError

    async def command_test(self, command: str) -> dict[str, Any]:
        raise NotImplementedError


class ForgeAutomationBackend(MinecraftBackend):
    """Backend that talks to the local Forge 1.16.5 automation mod."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.base_url = (args.automation_url or os.environ.get("SMASHMC_AUTOMATION_URL") or "http://127.0.0.1:17616").rstrip("/")
        self.token = args.automation_token or os.environ.get("SMASHMC_AUTOMATION_TOKEN") or ""
        self.last_message_id = 0
        self.ready_status: dict[str, Any] = {}

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["X-SmashMC-Automation-Token"] = self.token
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as error:
            raise RuntimeError(
                "Unable to reach SmashMC Forge automation mod. "
                "Start Minecraft Forge 36.2.35 with the mod installed first."
            ) from error
        return json.loads(body or "{}")

    async def _request_async(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._request, method, path, payload, timeout)

    async def connect(self) -> None:
        deadline = time.monotonic() + self.args.connect_timeout
        while time.monotonic() < deadline:
            status = await self._request_async("GET", "/status", timeout=5.0)
            if status.get("inGame"):
                self.ready_status = status
                messages = await self._request_async("GET", "/messages?since=0", timeout=5.0)
                self.last_message_id = int(messages.get("next") or 0) - 1
                return
            await asyncio.sleep(1)
        raise RuntimeError("Timed out waiting for the Forge automation mod to report an in-game client.")

    def status(self) -> dict[str, Any]:
        return self.ready_status

    async def refresh_status(self) -> dict[str, Any]:
        self.ready_status = await self._request_async("GET", "/status", timeout=5.0)
        return self.ready_status

    async def _drain_messages(self) -> list[str]:
        response = await self._request_async("GET", f"/messages?since={self.last_message_id}", timeout=5.0)
        lines: list[str] = []
        for message in response.get("messages") or []:
            try:
                self.last_message_id = max(self.last_message_id, int(message.get("id") or 0))
            except (TypeError, ValueError):
                pass
            text = str(message.get("text") or "").strip()
            if text:
                lines.append(text)
        return lines

    async def command(self, command: str, wait_seconds: float) -> list[str]:
        await self._drain_messages()
        await self._request_async("POST", "/command", {"command": command}, timeout=5.0)
        await asyncio.sleep(wait_seconds)
        return await self._drain_messages()

    async def command_test(self, command: str) -> dict[str, Any]:
        await self._drain_messages()
        print("READY")
        print(f"SENDING COMMAND: {command}")
        await self._request_async("POST", "/command", {"command": command}, timeout=5.0)
        print("COMMAND SENT")
        await asyncio.sleep(15)
        status = await self._request_async("GET", "/status", timeout=5.0)
        lines = await self._drain_messages()
        return {"status": status, "lines": lines}

    async def close(self) -> None:
        if self.args.keep_client_connected:
            return
        try:
            await self._request_async("POST", "/disconnect", {}, timeout=5.0)
        except RuntimeError:
            return


def load_backend(args: argparse.Namespace) -> MinecraftBackend:
    if args.backend != "forge":
        raise RuntimeError(f"Unsupported backend: {args.backend}")
    return ForgeAutomationBackend(args)


async def query_movelist(
    backend: MinecraftBackend,
    pokemon_name: str,
    pokemon_command_name: str,
    retries: int,
    response_wait: float,
) -> tuple[list[str], list[str]]:
    command = f"/movelist {pokemon_command_name}"
    last_lines: list[str] = []
    for attempt in range(1, retries + 2):
        print(f"Issuing {command} (attempt {attempt})")
        lines = await backend.command(command, response_wait)
        last_lines = clean_evidence(lines)
        moves = parse_movelist_response(pokemon_name, lines)
        if moves:
            return moves, last_lines
    return [], last_lines


def validation_sample() -> tuple[str, list[str]]:
    path = repo_root() / DEFAULT_OUTPUT
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            preferred = list(raw.items())
            preferred.sort(key=lambda item: 0 if "vote" in json.dumps(item[1]).lower() else 1)
            for name, payload in preferred:
                if isinstance(payload, dict) and isinstance(payload.get("evidence"), list):
                    return str(name), [str(line) for line in payload["evidence"]]
    return (
        "Iron Abyss",
        [
            "Iron Abyss's Move List:",
            "Ominous Wind\u00a7a, Quick Attack\u00a7a, Dark Pulse\u00a7a",
            "Vote and Get Rewards",
            "Vote for the server in order to win money",
        ],
    )


def run_parser_validation() -> int:
    pokemon_name, lines = validation_sample()
    result = parse_movelist_details(pokemon_name, lines)
    print("raw captured text:")
    for line in result.raw_lines:
        print(line)
    print()
    print("cleaned text:")
    for line in result.cleaned_lines:
        print(line)
    print()
    print("extracted move list:")
    for move in result.moves:
        print(move)
    print()
    print(f"reason parsing stopped: {result.stop_reason}")
    return 0


async def run_export(args: argparse.Namespace) -> int:
    if args.validate_parser:
        return run_parser_validation()

    if args.command:
        backend = load_backend(args)
        await backend.connect()
        try:
            result = await backend.command_test(args.command)
            status = result.get("status")
            if status:
                coordinates = status.get("coordinates") or {}
                print(f"server: {status.get('server', '')}")
                print(
                    "coordinates: "
                    f"x={coordinates.get('x')}, y={coordinates.get('y')}, z={coordinates.get('z')}"
                )
                print(f"dimension: {status.get('dimension', '')}")
            for line in result.get("lines", []):
                print(line)
            if args.parse_as:
                moves = parse_movelist_response(args.parse_as, result.get("lines", []))
                print(json.dumps({
                    args.parse_as: {
                        "command_name": command_name(args.parse_as),
                        "moves": moves,
                    },
                }, indent=2, ensure_ascii=False))
            if "lines" in result and not result.get("lines"):
                print("NO CHAT RECEIVED")
        finally:
            await backend.close()
        return 0

    if args.login_test:
        backend = load_backend(args)
        await backend.connect()
        try:
            status = backend.status()
            coordinates = status.get("coordinates") or {}
            print(f"username: {status.get('playerName') or status.get('username', '')}")
            print(f"current server: {status.get('server', '')}")
            print(
                "current coordinates: "
                f"x={coordinates.get('x')}, y={coordinates.get('y')}, z={coordinates.get('z')}"
            )
            print(f"current dimension: {status.get('dimension', '')}")
        finally:
            await backend.close()
        return 0

    root = repo_root()
    output_path = root / args.output
    failure_path = root / args.failure_log
    if args.names:
        pokemon = load_requested_pokemon(args.names)
        custom_path = "<--names>"
    else:
        custom_path = root / args.input
        pokemon = load_custom_pokemon(custom_path)
    if args.limit is not None:
        pokemon = pokemon[:args.limit]
    print(f"Loaded {len(pokemon)} Pokemon from {custom_path}")

    progress = load_json_object(output_path)
    failures = load_json_object(failure_path)
    if not isinstance(progress, dict):
        progress = {}
    if not isinstance(failures, dict):
        failures = {}

    backend = load_backend(args)
    await backend.connect()
    try:
        if args.skip_groudon:
            print("Skipping /groudon; assuming the client is already in Groudon.")
        else:
            print("Issuing /groudon to leave the hub.")
            await backend.command("/groudon", args.hub_wait)
            transfer_deadline = time.monotonic() + args.transfer_timeout
            while time.monotonic() < transfer_deadline:
                status = await backend.refresh_status()
                if status.get("groudonJoined"):
                    print("Groudon joined.")
                    break
                await asyncio.sleep(1)
            else:
                raise RuntimeError("Timed out waiting for the Forge automation mod to report Groudon joined.")
        await asyncio.sleep(args.command_delay)

        since_save = 0
        for entry in pokemon:
            name = entry["name"]
            pokemon_command_name = entry["command_name"]
            if name in progress and progress[name].get("moves") and not args.force:
                continue

            try:
                moves, evidence = await query_movelist(
                    backend,
                    name,
                    pokemon_command_name,
                    args.retries,
                    args.response_wait,
                )
                if moves:
                    progress[name] = {
                        "command_name": pokemon_command_name,
                        "moves": moves,
                        "evidence": evidence,
                        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    failures.pop(name, None)
                else:
                    failures[name] = {
                        "name": name,
                        "command_name": pokemon_command_name,
                        "error": "No moves parsed from /movelist response.",
                        "last_response": evidence,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    print(f"Failed to parse learnset for {name}", file=sys.stderr)
            except Exception as error:
                failures[name] = {
                    "name": name,
                    "command_name": pokemon_command_name,
                    "error": str(error),
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                print(f"Failed to export learnset for {name}: {error}", file=sys.stderr)

            since_save += 1
            if since_save >= args.save_every:
                save_json_atomic(output_path, progress)
                save_json_atomic(failure_path, failures)
                since_save = 0
            await asyncio.sleep(args.command_delay)

        save_json_atomic(output_path, progress)
        save_json_atomic(failure_path, failures)
    finally:
        await backend.close()

    print(f"Wrote {len(progress)} learnsets to {output_path}")
    if failures:
        print(f"{len(failures)} lookups failed; see {failure_path}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_OUTPUT.parent / "custom_pokemon.json"))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--failure-log", default=str(DEFAULT_FAILURE_LOG))
    parser.add_argument("--backend", default="forge", choices=["forge"])
    parser.add_argument("--automation-url", help="Local Forge automation URL. Defaults to SMASHMC_AUTOMATION_URL or http://127.0.0.1:17616.")
    parser.add_argument("--automation-token", help="Optional token matching SMASHMC_AUTOMATION_TOKEN.")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--command-delay", type=float, default=2.0)
    parser.add_argument("--response-wait", type=float, default=4.0)
    parser.add_argument("--hub-wait", type=float, default=6.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--skip-groudon", action="store_true", help="Assume the client is already in Groudon and start querying /movelist immediately.")
    parser.add_argument("--response-timeout", type=float, default=10.0)
    parser.add_argument("--connect-timeout", type=float, default=120.0)
    parser.add_argument("--save-every", type=int, default=5)
    parser.add_argument("--limit", type=int, help="Only query the first N Pokemon from custom_pokemon.json.")
    parser.add_argument("--names", help="Comma-separated Pokemon names to query instead of reading custom_pokemon.json.")
    parser.add_argument("--force", action="store_true", help="Re-query Pokemon already present in learnsets.json.")
    parser.add_argument("--keep-client-connected", action="store_true", help="Do not ask the Forge automation mod to disconnect on exit.")
    parser.add_argument("--login-test", action="store_true", help="Connect, print spawn status, and disconnect without exporting.")
    parser.add_argument("--command", help="Connect, send exactly one chat command, print chat for 10 seconds, and disconnect.")
    parser.add_argument("--parse-as", help="With --command, parse the captured chat as this Pokemon's movelist.")
    parser.add_argument("--validate-parser", action="store_true", help="Validate movelist parsing against captured evidence without connecting to Minecraft.")
    return parser


def main() -> int:
    try:
        return asyncio.run(run_export(build_parser().parse_args()))
    except Exception as error:
        print(f"export_learnsets.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
