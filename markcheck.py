#!/usr/bin/env python3
"""markcheck - работа с чек-листами в Markdown.

Команды:
  list    показать все пункты
  add     добавить новый пункт
  done    отметить пункт выполненным
  undone  снять отметку
  toggle  переключить отметку
  remove  удалить пункт
  stats   показать статистику

Примеры:
  markcheck -f tasks.md list
  markcheck -f tasks.md add "написать документацию"
  markcheck -f tasks.md done 3
  markcheck -f tasks.md done "документация"
  markcheck -f tasks.md stats
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

__version__ = "1.0.0"

CHECKBOX_RE = __import__("re").compile(
    r"^(\s*[-*+]\s+)\[([ xX])\]([ \t]*)(.*)$"
)
HEADING_RE = __import__("re").compile(r"^#{1,6}\s+(.*)$")


def read_lines(path: Path) -> List[str]:
    """Читает Markdown-файл и возвращает строки.

    Если файла нет - возвращает пустой список, чтобы команды вида add
    могли создать файл с нуля.
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return text.splitlines()


def write_lines(path: Path, lines: List[str]) -> None:
    """Записывает строки обратно в файл, создавая директории при необходимости."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    if lines and not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def is_checkbox_line(line: str) -> bool:
    return CHECKBOX_RE.match(line) is not None


def collect_items(lines: List[str]) -> List[Dict[str, object]]:
    """Собирает все чек-боксы в список с положением в файле и состоянием."""
    items: List[Dict[str, object]] = []
    for idx, line in enumerate(lines):
        match = CHECKBOX_RE.match(line)
        if match:
            items.append(
                {
                    "index": idx,
                    "checked": match.group(2).lower() == "x",
                    "text": match.group(4),
                }
            )
    return items


def set_checked(lines: List[str], item: Dict[str, object], checked: bool) -> bool:
    """Перезаписывает строку чек-бокса в нужное состояние."""
    line = lines[item["index"]]  # type: ignore[index]
    match = CHECKBOX_RE.match(line)
    if not match:
        return False
    state = "x" if checked else " "
    lines[item["index"]] = f"{match.group(1)}[{state}]{match.group(3)}{match.group(4)}"  # type: ignore[index]
    return True


def select_item(items: List[Dict[str, object]], target: str) -> Optional[int]:
    """Находит пункт по номеру (1-based) или по подстроке текста."""
    try:
        number = int(target)
    except ValueError:
        needle = target.casefold()
        matches = [
            i for i, item in enumerate(items)
            if needle in str(item["text"]).casefold()
        ]
        if not matches:
            print(
                "markcheck: error: no item matches this text",
                file=sys.stderr,
            )
            return None
        if len(matches) > 1:
            listed = ", ".join(str(i + 1) for i in matches)
            print(
                f"markcheck: error: multiple items match: {listed}",
                file=sys.stderr,
            )
            return None
        return matches[0]

    if number < 1 or number > len(items):
        print(
            f"markcheck: error: item number {number} is out of range "
            f"(have {len(items)} items)",
            file=sys.stderr,
        )
        return None
    return number - 1


def next_heading_index(lines: List[str], start: int) -> int:
    """Индекс следующего заголовка после start, либо len(lines)."""
    for i in range(start + 1, len(lines)):
        if HEADING_RE.match(lines[i]):
            return i
    return len(lines)


def find_section_insert_index(lines: List[str], section: str) -> Optional[int]:
    """Ищет позицию для вставки нового пункта под указанным заголовком."""
    for i, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if not match:
            continue
        if section.casefold() in match.group(1).casefold():
            end = next_heading_index(lines, i)
            last_check_index: Optional[int] = None
            for j in range(i + 1, end):
                if is_checkbox_line(lines[j]):
                    last_check_index = j
            if last_check_index is not None:
                return last_check_index + 1
            return i + 1
    return None


def cmd_list(args: argparse.Namespace, path: Path, lines: List[str]) -> int:
    items = collect_items(lines)
    if not items:
        print(f"No checklist items in {path}.")
        return 0
    for i, item in enumerate(items, start=1):
        mark = "x" if item["checked"] else " "
        print(f"{i:3d}. [{mark}] {item['text']}")
    return 0


def cmd_add(args: argparse.Namespace, path: Path, lines: List[str]) -> int:
    text = args.text.strip()
    if not text:
        print("markcheck: error: task text cannot be empty", file=sys.stderr)
        return 2

    new_line = f"- [ ] {text}"
    if args.section:
        insert_at = find_section_insert_index(lines, args.section)
        if insert_at is None:
            print(
                f"markcheck: error: section {args.section!r} not found",
                file=sys.stderr,
            )
            return 1
    else:
        insert_at = len(lines)

    lines.insert(insert_at, new_line)
    try:
        write_lines(path, lines)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"markcheck: error: {exc}", file=sys.stderr)
        return 1

    print(f"Added: {text}")
    return 0


def cmd_done(args: argparse.Namespace, path: Path, lines: List[str]) -> int:
    return set_item_checked(args, path, lines, True)


def cmd_undone(args: argparse.Namespace, path: Path, lines: List[str]) -> int:
    return set_item_checked(args, path, lines, False)


def set_item_checked(
    args: argparse.Namespace,
    path: Path,
    lines: List[str],
    checked: bool,
) -> int:
    items = collect_items(lines)
    idx = select_item(items, args.target)
    if idx is None:
        return 1

    item = items[idx]
    if bool(item["checked"]) == checked:
        state_word = "done" if checked else "open"
        print(f"Item {idx + 1} is already {state_word}; no change.")
        return 0

    set_checked(lines, item, checked)
    try:
        write_lines(path, lines)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"markcheck: error: {exc}", file=sys.stderr)
        return 1

    state_word = "done" if checked else "open"
    print(f"{idx + 1}: {state_word} - {item['text']}")
    return 0


def cmd_toggle(args: argparse.Namespace, path: Path, lines: List[str]) -> int:
    items = collect_items(lines)
    idx = select_item(items, args.target)
    if idx is None:
        return 1

    item = items[idx]
    new_checked = not bool(item["checked"])
    set_checked(lines, item, new_checked)
    try:
        write_lines(path, lines)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"markcheck: error: {exc}", file=sys.stderr)
        return 1

    state_word = "done" if new_checked else "open"
    print(f"{idx + 1}: {state_word} - {item['text']}")
    return 0


def cmd_remove(args: argparse.Namespace, path: Path, lines: List[str]) -> int:
    items = collect_items(lines)
    idx = select_item(items, args.target)
    if idx is None:
        return 1

    item = items[idx]
    del lines[item["index"]]  # type: ignore[index]
    try:
        write_lines(path, lines)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"markcheck: error: {exc}", file=sys.stderr)
        return 1

    print(f"Removed: {item['text']}")
    return 0


def cmd_stats(args: argparse.Namespace, path: Path, lines: List[str]) -> int:
    items = collect_items(lines)
    total = len(items)
    if total == 0:
        print(f"No checklist items in {path}.")
        return 0

    done = sum(1 for item in items if item["checked"])
    open_count = total - done
    progress = done / total * 100.0

    print(f"File: {path}")
    print(f"Items: {total}")
    print(f"Done: {done}")
    print(f"Open: {open_count}")
    print(f"Progress: {progress:.1f}%")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markcheck",
        description="Work with Markdown checklists.",
    )
    parser.add_argument(
        "-f",
        "--file",
        default="checklist.md",
        help="path to Markdown file (default: checklist.md)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", aliases=["ls"], help="list checklist items")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="add a new checklist item")
    p_add.add_argument("text", help="task text")
    p_add.add_argument(
        "-s",
        "--section",
        help="heading under which to add the item",
    )
    p_add.set_defaults(func=cmd_add)

    p_done = sub.add_parser("done", aliases=["check"], help="mark item as done")
    p_done.add_argument("target", help="item number or text substring")
    p_done.set_defaults(func=cmd_done)

    p_undone = sub.add_parser(
        "undone",
        aliases=["uncheck", "todo"],
        help="mark item as not done",
    )
    p_undone.add_argument("target", help="item number or text substring")
    p_undone.set_defaults(func=cmd_undone)

    p_toggle = sub.add_parser("toggle", help="toggle item state")
    p_toggle.add_argument("target", help="item number or text substring")
    p_toggle.set_defaults(func=cmd_toggle)

    p_remove = sub.add_parser("remove", aliases=["rm"], help="remove item")
    p_remove.add_argument("target", help="item number or text substring")
    p_remove.set_defaults(func=cmd_remove)

    p_stats = sub.add_parser("stats", help="show checklist statistics")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    path = Path(args.file).expanduser()
    try:
        lines = read_lines(path)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"markcheck: error: {exc}", file=sys.stderr)
        return 1

    return args.func(args, path, lines)


if __name__ == "__main__":
    raise SystemExit(main())