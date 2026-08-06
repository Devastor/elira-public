# markcheck

Markdown checklist tool.

## Files

- `markcheck.py` - CLI tool for working with Markdown checklists.
- `test_markcheck.py` - pytest suite for `markcheck.py`.

## Usage

Commands: `list`, `add`, `done`, `undone`, `toggle`, `remove`, `stats`.

Examples:

    python markcheck.py -f tasks.md list
    python markcheck.py -f tasks.md add "write documentation"
    python markcheck.py -f tasks.md done 3
    python markcheck.py -f tasks.md undone "documentation"
    python markcheck.py -f tasks.md toggle 2
    python markcheck.py -f tasks.md remove 4
    python markcheck.py -f tasks.md stats

## Development

Run tests:

    python -m pytest test_markcheck.py -v
