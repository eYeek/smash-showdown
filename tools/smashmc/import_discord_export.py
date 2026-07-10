#!/usr/bin/env python3
"""Import DiscordChatExporter JSON into SmashMC custom_pokemon.json."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
TYPE_NAMES = {
    "normal", "fire", "water", "electric", "grass", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
    "dragon", "dark", "steel", "fairy",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
TIER_ALIASES = {
    "ou": "OU",
    "smashou": "OU",
    "uu": "UU",
    "smashuu": "UU",
    "uber": "Uber",
    "ubers": "Uber",
    "smashuber": "Uber",
    "smashubers": "Uber",
    "ag": "AG",
    "anythinggoes": "AG",
    "smashag": "AG",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def to_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def clean_markdown(text: str) -> str:
    text = re.sub(r"<a?:[^:]+:\d+>", " ", text)
    text = re.sub(r":[A-Za-z0-9_+-]+:", " ", text)
    text = text.replace("__", "").replace("**", "").replace("*", "")
    text = re.sub(r"[`\u200b]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -:\t\r\n")


def clean_line(line: str) -> str:
    return clean_markdown(line.strip())


def message_lines(content: str) -> list[str]:
    return [line for raw in content.splitlines() if (line := clean_line(raw))]


def title_case_type(value: str) -> str | None:
    candidate = to_id(value)
    if candidate in TYPE_NAMES:
        return candidate.capitalize()
    return None


def parse_name(content: str) -> str:
    first_line = next((line for line in content.splitlines() if clean_line(line)), "")
    bold = re.findall(r"(?:\*\*|__)+\s*([^*_:\n][^*\n_]*?)\s*(?:\*\*|__)+", first_line)
    if bold:
        return clean_line(bold[0])
    return clean_line(first_line)


def normalize_tier(value: str) -> str:
    return TIER_ALIASES.get(to_id(value), "")


def parse_tier(content: str) -> str:
    for raw in content.splitlines():
        line = clean_line(raw)
        if not line:
            continue
        tier_match = re.match(r"(?i)^tier\s*:?\s*(.+)$", line)
        if tier_match:
            tier = normalize_tier(tier_match.group(1))
            if tier:
                return tier
        tier = normalize_tier(line)
        if tier:
            return tier
    return ""


def parse_types(content: str) -> list[str]:
    type_label = re.search(r"(?im)^\s*(?:\*\*)?type(?:\*\*)?\s*:\s*(.+)$", content)
    if type_label:
        parsed = [type_name for part in re.split(r"[/x,|]", type_label.group(1)) if (type_name := title_case_type(part))]
        if parsed:
            return parsed[:2]

    for raw in content.splitlines():
        line = clean_line(raw)
        parsed = [type_name for part in re.split(r"\s*(?:/|x)\s*", line) if (type_name := title_case_type(part))]
        if len(parsed) >= 2:
            return parsed[:2]
    emoji_types = [match.capitalize() for match in re.findall(r":([A-Za-z]+):", content) if match.lower() in TYPE_NAMES]
    return emoji_types[:2]


def parse_stats(content: str) -> dict[str, int]:
    stats: dict[str, int] = {}
    patterns = {
        "hp": r"HP",
        "atk": r"Atk|Attack",
        "def": r"Def|Defense",
        "spa": r"SpAtk|SpA|Sp\.?\s*Atk|Special Attack",
        "spd": r"SpDef|SpD|Sp\.?\s*Def|Special Defense",
        "spe": r"Spd|Spe|Speed",
    }
    for key, pattern in patterns.items():
        match = re.search(rf"(?im)^\s*(?:\*\*)?(?:{pattern})(?:\*\*)?\s*:?\s*(\d{{1,3}})\b", content)
        if match:
            stats[key] = int(match.group(1))
    return stats


def stat_line_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if re.match(r"(?i)^hp\s*:?\s*\d{1,3}\b", line):
            return index
    return -1


def parse_abilities(content: str) -> list[str]:
    lines = message_lines(content)
    abilities: list[str] = []
    seen: set[str] = set()

    single = re.search(r"(?im)^\s*(?:\*\*)?ability(?:ies)?(?:\*\*)?\s*:?\s*(.+)$", content)
    if single and clean_line(single.group(1)):
        for part in re.split(r"[,/|]|\band\b", clean_line(single.group(1)), flags=re.IGNORECASE):
            add_unique(abilities, seen, part)

    for index, line in enumerate(lines):
        if re.match(r"(?i)^abilities?$", line):
            for candidate in lines[index + 1:]:
                if is_section_stop_line(candidate):
                    break
                add_unique(abilities, seen, candidate)
            break

    if abilities:
        return abilities

    start = stat_line_index(lines)
    if start >= 0:
        for candidate in lines[start + 6:start + 9]:
            if is_section_stop_line(candidate):
                break
            if re.search(r"\d", candidate):
                continue
            add_unique(abilities, seen, candidate)
    return abilities


def is_section_stop_line(line: str) -> bool:
    return (
        set(line) == {"="} or
        re.search(r"(?i)^(hp|stats|spawn location|tier|signature move)\b", line) is not None
    )


def add_unique(values: list[str], seen: set[str], raw: str) -> None:
    value = clean_line(raw)
    value = re.sub(r"(?i)^hidden ability\s*:?", "", value).strip()
    value_id = to_id(value)
    if value and value_id and value_id not in seen:
        values.append(value)
        seen.add(value_id)


def parse_signature_moves(content: str) -> list[str]:
    separator = content.find("==========================")
    tail = content[separator:] if separator >= 0 else content
    heading = re.search(r"(?is)(?:signature move|=+).*?(?:\*\*|__)\s*([^*_:\n][^*\n_]*?)\s*(?:\*\*|__)", tail)
    if heading:
        return [clean_line(heading.group(1))]
    return []


def safe_filename(filename: str, fallback: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".png"
    stem = Path(filename or "").stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-") or fallback
    return f"{stem}{suffix}"


def relative_to_repo(path: Path) -> str:
    return str(path.relative_to(repo_root())).replace("\\", "/")


def download_attachment(url: str, path: Path, timeout: int = 45) -> bool:
    if path.exists() and path.stat().st_size > 0:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "SmashShowdownImporter/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            path.write_bytes(response.read())
        return True
    except urllib.error.URLError as error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(error):
            print(f"warning: failed to download {url}: {error}", file=sys.stderr)
            return False
        try:
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                path.write_bytes(response.read())
            return True
        except (urllib.error.URLError, TimeoutError, OSError) as retry_error:
            print(f"warning: failed to download {url}: {retry_error}", file=sys.stderr)
            return False
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        print(f"warning: failed to download {url}: {error}", file=sys.stderr)
        return False


def forum_name(channel_name: str, filename: str) -> str:
    text = f"{channel_name} {filename}".lower()
    if "mega" in text:
        return "mega-info"
    if "paradox" in text:
        return "paradox-info"
    if "fusion" in text:
        return "fusion-info"
    return channel_name


def message_url(guild_id: str, channel_id: str, message_id: str) -> str:
    return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


def convert_message(payload: dict[str, Any], message: dict[str, Any], source_file: Path, output_dir: Path) -> dict[str, Any] | None:
    content = str(message.get("content") or "")
    name = parse_name(content)
    pokemon_id = to_id(name)
    if not pokemon_id:
        return None

    guild = payload.get("guild") if isinstance(payload.get("guild"), dict) else {}
    channel = payload.get("channel") if isinstance(payload.get("channel"), dict) else {}
    channel_name = str(channel.get("name") or "")
    guild_id = str(guild.get("id") or "")
    channel_id = str(channel.get("id") or "")
    message_id = str(message.get("id") or "")
    forum = forum_name(channel_name, source_file.name)

    images: list[dict[str, str]] = []
    sprites: list[str] = []
    gifs: list[str] = []
    for index, attachment in enumerate(message.get("attachments") or []):
        if not isinstance(attachment, dict):
            continue
        url = str(attachment.get("url") or "")
        filename = safe_filename(str(attachment.get("fileName") or ""), f"{message_id}-{index}")
        local_path = output_dir / "assets" / "sprites" / pokemon_id / f"{message_id}-{index}-{filename}"
        if url and download_attachment(url, local_path):
            local = relative_to_repo(local_path)
            images.append({"path": local, "source_filename": filename})
            if local_path.suffix.lower() == ".gif":
                gifs.append(local)
            else:
                sprites.append(local)

    return {
        "name": name,
        "id": pokemon_id,
        "forum": forum,
        "message_id": message_id,
        "thread_id": message_id,
        "thread_url": message_url(guild_id, channel_id, message_id) if guild_id and channel_id and message_id else "",
        "typing": parse_types(content),
        "tier": parse_tier(content),
        "base_stats": parse_stats(content),
        "abilities": parse_abilities(content),
        "moves": parse_signature_moves(content),
        "items": [],
        "images": images,
        "sprites": sprites,
        "gifs": gifs,
        "evidence": [{
            "message_id": message_id,
            "author": str((message.get("author") or {}).get("name") or ""),
            "created_at": str(message.get("timestamp") or ""),
            "content": content,
            "attachments": images,
        }],
    }


def import_exports(input_dir: Path, output_path: Path) -> int:
    root = repo_root()
    output_dir = output_path.parent
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source_file in sorted(input_dir.glob("*.json")):
        payload = json.loads(source_file.read_text(encoding="utf-8"))
        messages = payload.get("messages")
        if not isinstance(messages, list):
            continue
        for message in messages:
            if not isinstance(message, dict):
                continue
            entry = convert_message(payload, message, source_file, output_dir)
            if not entry or entry["id"] in seen:
                continue
            entries.append(entry)
            seen.add(entry["id"])

    output = {
        "schema_version": 1,
        "source": "DiscordChatExporter JSON",
        "source_dir": relative_to_repo(input_dir) if input_dir.is_relative_to(root) else str(input_dir),
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pokemon": sorted(entries, key=lambda entry: (entry["forum"], entry["id"])),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Imported {len(entries)} Pokemon into {output_path}")
    return len(entries)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="exported data from discord custom pokemon")
    parser.add_argument("--output", default="data/smashmc/custom_pokemon.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        import_exports(repo_root() / args.input_dir, repo_root() / args.output)
        return 0
    except Exception as error:
        print(f"import_discord_export.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
