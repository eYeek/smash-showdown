#!/usr/bin/env python3
"""Export SmashMC custom Pokemon data using discord.py.

This follows the Delta Showdown-style architecture:
- login as a Discord bot
- connect to the configured guild
- open the SmashMC custom Pokemon forum channels
- iterate every thread with thread.history(limit=None, oldest_first=True)
- download image/GIF attachments immediately while reading Discord

The exported JSON never depends on Discord CDN URLs at runtime. It stores local
asset paths, message evidence, and thread URLs only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


try:
    import discord
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    discord = None


FORUM_NAMES = ("fusion-info", "paradox-info", "mega-info")
STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
TYPE_NAMES = {
    "normal", "fire", "water", "electric", "grass", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
    "dragon", "dark", "steel", "fairy",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def clean_line(line: str) -> str:
    line = re.sub(r"^[>\-\*\u2022\s]+", "", line.strip())
    return re.sub(r"\s+", " ", line).strip()


def split_values(value: str) -> list[str]:
    value = re.sub(r"\([^)]*\)", "", value)
    parts = re.split(r"[,/|;]|\band\b", value, flags=re.IGNORECASE)
    return [clean_line(part) for part in parts if clean_line(part)]


def title_case_type(value: str) -> str | None:
    candidate = to_id(value)
    if candidate in TYPE_NAMES:
        return candidate.capitalize()
    return None


def parse_labeled_value(text: str, labels: tuple[str, ...]) -> str:
    label_re = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?im)^\s*(?:{label_re})\s*[:\-]\s*(.+)$", text)
    return clean_line(match.group(1)) if match else ""


def parse_name(thread_name: str, text: str) -> str:
    explicit = parse_labeled_value(text, ("name", "pokemon", "pokémon", "species"))
    if explicit:
        return explicit
    name = re.sub(r"^\s*(fusion|paradox|mega)\s*[:\-]\s*", "", thread_name, flags=re.IGNORECASE)
    return clean_line(name)


def parse_types(text: str) -> list[str]:
    value = parse_labeled_value(text, ("type", "typing", "types"))
    types = [type_name for part in split_values(value) if (type_name := title_case_type(part))]
    return types[:2]


def parse_stats(text: str) -> dict[str, int]:
    stats: dict[str, int] = {}
    stat_patterns = {
        "hp": r"HP",
        "atk": r"Atk|Attack",
        "def": r"Def|Defense",
        "spa": r"SpA|Sp\.?\s*Atk|Special Attack",
        "spd": r"SpD|Sp\.?\s*Def|Special Defense",
        "spe": r"Spe|Speed",
    }
    for key, pattern in stat_patterns.items():
        match = re.search(rf"(?i)\b(?:{pattern})\b\s*[:\-]?\s*(\d{{1,3}})", text)
        if match:
            stats[key] = int(match.group(1))
    if len(stats) == 6:
        return stats

    value = parse_labeled_value(text, ("base stats", "stats", "bst"))
    numbers = [int(num) for num in re.findall(r"\b\d{1,3}\b", value)]
    if len(numbers) >= 6:
        return dict(zip(STAT_KEYS, numbers[:6]))
    return stats


def parse_abilities(text: str) -> list[str]:
    value = parse_labeled_value(text, ("ability", "abilities"))
    return split_values(value)


def parse_moves(text: str) -> list[str]:
    value = parse_labeled_value(text, ("moves", "move pool", "movepool", "learnset"))
    moves = split_values(value)
    if moves:
        return moves

    lines = text.splitlines()
    capture = False
    collected: list[str] = []
    for line in lines:
        normalized = clean_line(line)
        if re.match(r"(?i)^(moves|move pool|movepool|learnset)\s*[:\-]?\s*$", normalized):
            capture = True
            continue
        if capture and re.match(r"(?i)^(ability|abilities|type|typing|stats|base stats|items?)\s*[:\-]", normalized):
            break
        if capture and normalized:
            collected.extend(split_values(normalized))
    return collected


def parse_items(text: str) -> list[str]:
    value = parse_labeled_value(text, ("item", "items", "required item", "held item"))
    return split_values(value)


def is_image_attachment(attachment: Any) -> bool:
    content_type = (attachment.content_type or "").lower()
    suffix = Path(attachment.filename or "").suffix.lower()
    return content_type.startswith("image/") or suffix in IMAGE_EXTENSIONS


def safe_filename(filename: str, fallback: str) -> str:
    suffix = Path(filename).suffix
    stem = Path(filename).stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-") or fallback
    suffix = re.sub(r"[^A-Za-z0-9.]+", "", suffix)[:12]
    return f"{stem}{suffix}"


def relative_to_repo(path: Path) -> str:
    return str(path.relative_to(repo_root())).replace("\\", "/")


async def save_attachment(attachment: Any, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    await attachment.save(destination, use_cached=True)


async def read_thread_messages(thread: Any, output_dir: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    evidence: list[dict[str, Any]] = []
    sprites: list[str] = []
    gifs: list[str] = []
    pokemon_id = to_id(thread.name)

    async for message in thread.history(limit=None, oldest_first=True):
        message_assets: list[str] = []
        for index, attachment in enumerate(message.attachments):
            if not is_image_attachment(attachment):
                continue
            filename = safe_filename(attachment.filename, f"{message.id}-{index}")
            local_path = output_dir / "assets" / "sprites" / pokemon_id / f"{message.id}-{index}-{filename}"
            await save_attachment(attachment, local_path)
            local_asset = relative_to_repo(local_path)
            message_assets.append(local_asset)
            if local_path.suffix.lower() == ".gif":
                gifs.append(local_asset)
            else:
                sprites.append(local_asset)

        evidence.append({
            "message_id": str(message.id),
            "author": str(message.author),
            "created_at": message.created_at.isoformat(),
            "content": message.content,
            "attachments": message_assets,
        })

    return evidence, sprites, gifs


def build_entry(
    thread: Any,
    forum_name: str,
    evidence: list[dict[str, Any]],
    sprites: list[str],
    gifs: list[str],
) -> dict[str, Any]:
    text = "\n".join(item["content"] for item in evidence)
    name = parse_name(thread.name, text)
    pokemon_id = to_id(name)
    return {
        "name": name,
        "id": pokemon_id,
        "forum": forum_name,
        "thread_id": str(thread.id),
        "thread_url": thread.jump_url,
        "typing": parse_types(text),
        "base_stats": parse_stats(text),
        "abilities": parse_abilities(text),
        "moves": parse_moves(text),
        "items": parse_items(text),
        "sprites": sprites,
        "gifs": gifs,
        "evidence": evidence,
    }


async def iter_forum_threads(forum: Any) -> list[Any]:
    threads: dict[int, Any] = {thread.id: thread for thread in getattr(forum, "threads", [])}
    async for thread in forum.archived_threads(limit=None):
        threads[thread.id] = thread
    return sorted(threads.values(), key=lambda thread: thread.created_at or thread.id)


def get_forum(guild: Any, forum_name: str) -> Any:
    for channel in guild.channels:
        if channel.name == forum_name:
            if discord is not None and not isinstance(channel, discord.ForumChannel):
                raise RuntimeError(f"Channel '{forum_name}' exists but is not a Discord forum.")
            return channel
    raise RuntimeError(f"Missing Discord forum channel: {forum_name}")


class SmashMCExporterClient(discord.Client if discord is not None else object):
    def __init__(self, args: argparse.Namespace):
        if discord is None:
            raise RuntimeError("discord.py is required. Install it with: python -m pip install discord.py")
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.args = args
        self.result_code = 1

    async def on_ready(self) -> None:
        try:
            await self.export()
            self.result_code = 0
        except Exception as error:
            print(f"export.py: {error}", file=sys.stderr)
            self.result_code = 1
        finally:
            await self.close()

    async def export(self) -> None:
        guild_id = self.args.guild_id or os.environ.get("SMASHMC_GUILD_ID")
        if not guild_id:
            raise RuntimeError("SMASHMC_GUILD_ID is required to connect directly to the SmashMC guild.")

        guild = self.get_guild(int(guild_id))
        if guild is None:
            guild = await self.fetch_guild(int(guild_id))
        if guild is None:
            raise RuntimeError(f"Bot is not connected to guild {guild_id}.")

        output_dir = repo_root() / "data" / "smashmc"
        output_dir.mkdir(parents=True, exist_ok=True)
        pokemon: list[dict[str, Any]] = []

        for forum_name in FORUM_NAMES:
            forum = get_forum(guild, forum_name)
            threads = await iter_forum_threads(forum)
            for thread in threads:
                evidence, sprites, gifs = await read_thread_messages(thread, output_dir)
                if not evidence:
                    continue
                entry = build_entry(thread, forum_name, evidence, sprites, gifs)
                if entry["name"] and entry["id"]:
                    pokemon.append(entry)

        payload = {
            "schema_version": 2,
            "source": "SmashMC Discord",
            "forums": list(FORUM_NAMES),
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pokemon": sorted(pokemon, key=lambda entry: entry["id"]),
        }
        target = output_dir / "custom_pokemon.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Exported {len(pokemon)} Pokemon to {target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", help="Discord bot token. Defaults to DISCORD_TOKEN.")
    parser.add_argument("--guild-id", help="SmashMC Discord guild ID. Defaults to SMASHMC_GUILD_ID.")
    return parser


async def run_export(args: argparse.Namespace) -> int:
    token = args.token or os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is required to scrape SmashMC Discord.")

    client = SmashMCExporterClient(args)
    await client.start(token)
    return client.result_code


def main() -> int:
    try:
        return asyncio.run(run_export(build_parser().parse_args()))
    except Exception as error:
        print(f"export.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
