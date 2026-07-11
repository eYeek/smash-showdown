"""Build a grouped SmashMC custom move reference from the generated database."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GROUPS = [
    ("mega-info", "Mega"),
    ("paradox-info", "Paradox"),
    ("fusion-info", "Fusion"),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def move_summary(move: dict[str, Any]) -> tuple[str, str, str]:
    name = str(move.get("name") or "").strip() or "Unknown"
    desc = str(move.get("desc") or "").strip()
    effect = str(move.get("shortDesc") or "").strip()
    return name, desc or "-", effect or "-"


def entry_rows(entry: dict[str, Any]) -> list[str]:
    moves = entry.get("customMoves") or []
    if not moves:
        return [
            "| "
            + " | ".join([
                markdown_escape(str(entry["name"])),
                "-",
                "No custom move parsed from Discord evidence.",
                "-",
                markdown_escape(str(entry.get("threadUrl") or "")),
            ])
            + " |"
        ]

    rows = []
    for index, move in enumerate(moves):
        move_name, desc, effect = move_summary(move)
        rows.append(
            "| "
            + " | ".join([
                markdown_escape(str(entry["name"]) if index == 0 else ""),
                markdown_escape(move_name),
                markdown_escape(desc),
                markdown_escape(effect),
                markdown_escape(str(entry.get("threadUrl") or "")),
            ])
            + " |"
        )
    return rows


def main() -> None:
    root = repo_root()
    database_path = root / "data" / "smashmc" / "smash_database.json"
    output_path = root / "data" / "smashmc" / "custom_move_reference.md"
    database = json.loads(database_path.read_text(encoding="utf-8"))
    entries = list(database["pokemon"])

    lines = [
        "# SmashMC Custom Move Reference",
        "",
        "Generated from `data/smashmc/smash_database.json`.",
        "",
        "| Group | Pokemon count | With custom move |",
        "| --- | ---: | ---: |",
    ]

    for forum, title in GROUPS:
        group_entries = [entry for entry in entries if entry.get("forum") == forum]
        with_moves = sum(1 for entry in group_entries if entry.get("customMoves"))
        lines.append(f"| {title} | {len(group_entries)} | {with_moves} |")

    lines.append("")

    for forum, title in GROUPS:
        group_entries = sorted(
            [entry for entry in entries if entry.get("forum") == forum],
            key=lambda entry: str(entry["name"]).lower(),
        )
        lines.extend([
            f"## {title}",
            "",
            "| Pokemon | Custom move | Discord description | Discord effect text | Thread |",
            "| --- | --- | --- | --- | --- |",
        ])
        for entry in group_entries:
            lines.extend(entry_rows(entry))
        lines.append("")

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {output_path.relative_to(root)}")


if __name__ == "__main__":
    main()
