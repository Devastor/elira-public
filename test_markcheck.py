"""Автотесты для markcheck.py.

Запуск:
    pytest projects/markcheck/test_markcheck.py -v
"""

import pytest
import markcheck


def test_read_lines_missing_file(tmp_path):
    assert markcheck.read_lines(tmp_path / "nope.md") == []


def test_read_lines_existing_file(tmp_path):
    path = tmp_path / "list.md"
    path.write_text("- [ ] one\n- [x] two\n", encoding="utf-8")
    assert markcheck.read_lines(path) == ["- [ ] one", "- [x] two"]


def test_write_lines_creates_parent_dirs(tmp_path):
    path = tmp_path / "sub" / "dir" / "list.md"
    markcheck.write_lines(path, ["- [ ] task"])
    assert path.read_text(encoding="utf-8") == "- [ ] task\n"


def test_write_lines_keeps_no_trailing_newline_clean(tmp_path):
    path = tmp_path / "list.md"
    markcheck.write_lines(path, ["line"])
    assert path.read_text(encoding="utf-8") == "line\n"


def test_is_checkbox_line():
    assert markcheck.is_checkbox_line("- [ ] task")
    assert markcheck.is_checkbox_line("* [x] task")
    assert markcheck.is_checkbox_line("+ [X] task")
    assert markcheck.is_checkbox_line("  - [ ]  task  ")
    assert not markcheck.is_checkbox_line("- [ ]task")
    assert not markcheck.is_checkbox_line("## Heading")
    assert not markcheck.is_checkbox_line("plain text")


def test_collect_items():
    lines = ["# Todo", "- [ ] alpha", "- [x] beta", "text", "* [ ] gamma"]
    items = markcheck.collect_items(lines)
    assert len(items) == 3
    assert items[0] == {"index": 1, "checked": False, "text": "alpha"}
    assert items[1] == {"index": 2, "checked": True, "text": "beta"}
    assert items[2] == {"index": 4, "checked": False, "text": "gamma"}


def test_set_checked():
    lines = ["- [ ] task"]
    item = markcheck.collect_items(lines)[0]
    assert markcheck.set_checked(lines, item, True)
    assert lines == ["- [x] task"]
    assert markcheck.set_checked(lines, item, False)
    assert lines == ["- [ ] task"]


def test_select_item_by_number():
    items = markcheck.collect_items(["- [ ] a", "- [x] b"])
    assert markcheck.select_item(items, "1") == 0
    assert markcheck.select_item(items, "2") == 1


def test_select_item_out_of_range(capsys):
    items = markcheck.collect_items(["- [ ] a"])
    assert markcheck.select_item(items, "5") is None
    assert "out of range" in capsys.readouterr().err


def test_select_item_by_substring():
    items = markcheck.collect_items(["- [ ] hello world", "- [ ] goodbye"])
    assert markcheck.select_item(items, "hello") == 0
    assert markcheck.select_item(items, "good") == 1


def test_select_item_no_match(capsys):
    items = markcheck.collect_items(["- [ ] hello"])
    assert markcheck.select_item(items, "missing") is None
    assert "no item matches" in capsys.readouterr().err


def test_select_item_multiple_matches(capsys):
    items = markcheck.collect_items(["- [ ] same", "- [ ] same", "- [ ] other"])
    assert markcheck.select_item(items, "same") is None
    err = capsys.readouterr().err
    assert "multiple items match" in err
    assert "1, 2" in err


def test_next_heading_index():
    lines = ["# One", "text", "## Two", "more", "# Three"]
    assert markcheck.next_heading_index(lines, 0) == 2
    assert markcheck.next_heading_index(lines, 2) == 4
    assert markcheck.next_heading_index(lines, 4) == len(lines)
    assert markcheck.next_heading_index(lines, 1) == 2


def test_find_section_insert_index_no_items():
    lines = ["# Section", "plain text"]
    assert markcheck.find_section_insert_index(lines, "section") == 1


def test_find_section_insert_index_after_last_item():
    lines = ["# Section", "- [ ] first", "- [x] second", "tail"]
    assert markcheck.find_section_insert_index(lines, "section") == 3


def test_find_section_insert_index_missing_section():
    lines = ["# Other", "- [ ] first"]
    assert markcheck.find_section_insert_index(lines, "missing") is None


def test_cmd_add_appends_to_end(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("- [ ] existing\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(text="new task", section=None)
    assert markcheck.cmd_add(args, path, lines) == 0
    assert path.read_text(encoding="utf-8") == "- [ ] existing\n- [ ] new task\n"
    assert "Added: new task" in capsys.readouterr().out


def test_cmd_add_empty_text(tmp_path, capsys):
    path = tmp_path / "list.md"
    lines = []
    args = argparse_namespace(text="   ", section=None)
    assert markcheck.cmd_add(args, path, lines) == 2
    assert "cannot be empty" in capsys.readouterr().err


def test_cmd_add_into_section(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("# Work\n- [ ] a\n# Personal\n- [ ] b\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(text="c", section="Personal")
    assert markcheck.cmd_add(args, path, lines) == 0
    text = path.read_text(encoding="utf-8")
    assert text == "# Work\n- [ ] a\n# Personal\n- [ ] b\n- [ ] c\n"


def test_cmd_add_section_not_found(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("# Work\n- [ ] a\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(text="x", section="Missing")
    assert markcheck.cmd_add(args, path, lines) == 1
    assert "section 'Missing' not found" in capsys.readouterr().err


def test_cmd_done_by_number(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("- [ ] first\n- [x] second\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(target="1")
    assert markcheck.cmd_done(args, path, lines) == 0
    assert path.read_text(encoding="utf-8") == "- [x] first\n- [x] second\n"
    assert "1: done - first" in capsys.readouterr().out


def test_cmd_done_by_text(tmp_path):
    path = tmp_path / "list.md"
    path.write_text("- [ ] alpha\n- [ ] beta\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(target="alpha")
    assert markcheck.cmd_done(args, path, lines) == 0
    assert path.read_text(encoding="utf-8") == "- [x] alpha\n- [ ] beta\n"


def test_cmd_done_already_done(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("- [x] done\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(target="1")
    assert markcheck.cmd_done(args, path, lines) == 0
    assert "already done" in capsys.readouterr().out


def test_cmd_undone(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("- [x] done\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(target="1")
    assert markcheck.cmd_undone(args, path, lines) == 0
    assert path.read_text(encoding="utf-8") == "- [ ] done\n"
    assert "1: open - done" in capsys.readouterr().out


def test_cmd_toggle(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("- [ ] item\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(target="1")
    assert markcheck.cmd_toggle(args, path, lines) == 0
    assert path.read_text(encoding="utf-8") == "- [x] item\n"
    assert "1: done - item" in capsys.readouterr().out


def test_cmd_remove(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("- [ ] keep\n- [ ] remove\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace(target="2")
    assert markcheck.cmd_remove(args, path, lines) == 0
    assert path.read_text(encoding="utf-8") == "- [ ] keep\n"
    assert "Removed: remove" in capsys.readouterr().out


def test_cmd_stats(tmp_path, capsys):
    path = tmp_path / "list.md"
    path.write_text("- [ ] a\n- [x] b\n- [x] c\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace()
    assert markcheck.cmd_stats(args, path, lines) == 0
    out = capsys.readouterr().out
    assert "Items: 3" in out
    assert "Done: 2" in out
    assert "Open: 1" in out
    assert "Progress: 66.7%" in out


def test_cmd_stats_no_items(tmp_path, capsys):
    path = tmp_path / "empty.md"
    path.write_text("nothing here\n", encoding="utf-8")
    lines = markcheck.read_lines(path)
    args = argparse_namespace()
    assert markcheck.cmd_stats(args, path, lines) == 0
    assert "No checklist items" in capsys.readouterr().out


def test_main_list(tmp_path, capsys):
    path = tmp_path / "tasks.md"
    path.write_text("- [ ] test\n", encoding="utf-8")
    assert markcheck.main(["-f", str(path), "list"]) == 0
    assert "1. [ ] test" in capsys.readouterr().out


def test_main_version(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        markcheck.main(["--version"])
    assert exc.value.code == 0


def argparse_namespace(**kwargs):
    from types import SimpleNamespace
    return SimpleNamespace(**kwargs)