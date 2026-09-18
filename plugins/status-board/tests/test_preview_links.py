"""Link targets follow rendered text; activation stays with the host terminal."""

import io
import os
from pathlib import Path
import select
import subprocess
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parents[1]))
import board
from preview_links import LinkedScreen, LinkStream, safe_link
from live_terminal import TerminalGrid, pyte
from test_live_terminal import frame


def osc(url):
    return f"\x1b]8;;{url}\x1b\\"


class LinkTests(unittest.TestCase):
    def test_fragmented_utf8_and_control_strings(self):
        text, links = [], []
        stream = LinkStream(text.append, links.append)
        data = (osc("https://example.com/pr/1") + "café" + osc("") +
                "\x1b]52;c;secret\x07" + "\x1bPignored\x1b]8;;https://fake\x1b\\").encode()
        for byte in data:
            stream.feed(bytes([byte]))
        self.assertEqual("".join(text), "café")
        self.assertEqual(links, ["https://example.com/pr/1", None])

    def test_unsafe_targets_and_unbounded_controls_are_rejected(self):
        for value in ("javascript:alert(1)", "command:run", "/relative/path", "https://host/\x1b[2J",
                      "https://host/\x9c", "https://host/\n", "http://[", "https://" + "a" * 8192):
            self.assertIsNone(safe_link(value))
        for value in ("https://github.carnegierobotics.com/a/b/pull/1", "file:///tmp/a.cc:12", "mailto:a@example.com"):
            self.assertEqual(safe_link(value), value)
        stream = LinkStream(Mock(), Mock())
        with self.assertRaises(ValueError):
            stream.feed(b"\x1b]8;;" + b"a" * 65536)

    def test_snapshot_links_survive_sgr_resets_and_wrapping(self):
        lines = list(board.styled_lines(osc("https://example.com") + "abc\x1b[0mdef" + osc("") + "!"))
        wrapped = list(board.wrap_styled(lines[0], 3))
        self.assertEqual([str(line) for line in wrapped], ["abc", "def", "!"])
        self.assertEqual(wrapped[1].styles[0].hyperlink, "https://example.com")
        self.assertIsNone(wrapped[-1].styles[0].hyperlink)

    def test_overlay_preserves_cursor_and_styles_and_clears_removed_targets(self):
        screen, output = Mock(), io.StringIO()
        screen.getmaxyx.return_value = (20, 80)
        linked = LinkedScreen(screen, output)
        style = board.TerminalStyle(foreground=4, bold=True, hyperlink="https://example.com")
        line = board.StyledText("Read PR", [style] * 7)
        board.draw_preview_line(linked, 3, line, Mock(), 80)
        linked.refresh()
        rendered = output.getvalue()
        self.assertTrue(rendered.startswith("\x1b7"))
        self.assertTrue(rendered.endswith("\x1b8"))
        self.assertIn("\x1b[4;2H\x1b[0;1;38;5;4m", rendered)
        self.assertIn(osc(style.hyperlink) + "Read PR" + osc(""), rendered)
        screen.redrawln.assert_called_with(3, 1)
        linked.erase()
        screen.redrawln.reset_mock()
        output.seek(0)
        output.truncate()
        linked.refresh()
        screen.redrawln.assert_called_once_with(3, 1)
        self.assertEqual(output.getvalue(), "")

    def test_changed_target_with_identical_label_forces_row_repaint(self):
        screen = Mock()
        screen.getmaxyx.return_value = (20, 80)
        linked = LinkedScreen(screen, io.StringIO())
        for url in ("https://example.com/old", "https://example.com/new"):
            linked.erase()
            linked.preview_row(2, [(1, "link", 4, board.TerminalStyle(hyperlink=url))])
            screen.redrawln.reset_mock()
            linked.refresh()
            screen.redrawln.assert_called_once_with(2, 1)

    def test_offscreen_and_right_edge_links_are_not_written(self):
        screen, output = Mock(), io.StringIO()
        screen.getmaxyx.return_value = (5, 10)
        linked = LinkedScreen(screen, output)
        run = (8, "xx", 2, board.TerminalStyle(hyperlink="https://example.com"))
        linked.preview_row(2, [run])
        linked.preview_row(8, [run])
        linked.refresh()
        self.assertEqual(output.getvalue(), "")

    def test_pr_cells_expose_each_host_target_without_forcing_solid_underline(self):
        screen, output = Mock(), io.StringIO()
        screen.getmaxyx.return_value = (20, 80)
        linked = LinkedScreen(screen, output)
        urls = ["https://github.com/team/a/pull/1", "https://github.carnegierobotics.com/team/b/pull/2"]
        text, spans = board.pr_cell({"prs": urls + ["https://github.com/team/c/pull/3", "https://github.com/team/c/pull/4"]}, 10)
        board.draw_pr_links(linked, 2, 10, text, spans, selected=True)
        linked.refresh()
        rendered = output.getvalue()
        for url in urls:
            self.assertIn(osc(url), rendered)
        self.assertEqual(len(linked.links[2]), 2)
        self.assertTrue(all(run[3].reverse and not run[3].underline for run in linked.links[2]))
        self.assertNotIn("+2", rendered)  # Overflow is an in-board control, not a URL.
        linked.erase()
        linked.refresh()
        screen.redrawln.assert_called_with(2, 1)

    def test_wrapped_detail_pr_links_keep_their_native_targets(self):
        screen = Mock()
        screen.getmaxyx.return_value = (40, 60)
        linked = LinkedScreen(screen, io.StringIO())
        row = {"action": "", "color": 3, "objective": "", "prs": [
            "https://github.com/team/long-repository-name/pull/1",
            "https://github.carnegierobotics.com/team/another-repository/pull/2"]}
        for y, (line, _, spans) in enumerate(board.detail_lines(row, 40)):
            if spans:
                board.draw_pr_links(linked, y, 1, line, spans)
        self.assertEqual({run[3].hyperlink for runs in linked.links.values() for run in runs}, set(row["prs"]))
        self.assertTrue(all(not run[3].reverse for runs in linked.links.values() for run in runs))


@unittest.skipIf(pyte is None, "Install board requirements")
class GridLinkTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "Requires a PTY")
    def test_real_curses_output_preserves_links_and_removes_them_on_next_view(self):
        import fcntl
        import pty
        import struct
        import termios
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 20, 80, 0, 0))
        script = '''
import curses, sys
import board
from preview_links import LinkedScreen
def paint(raw):
    curses.start_color()
    curses.use_default_colors()
    screen = LinkedScreen(raw, sys.stdout)
    palette = board.PreviewPalette()
    for target in ("https://example.com", None):
        screen.erase()
        style = board.TerminalStyle(foreground=4, bold=True, hyperlink=target)
        board.draw_preview_line(screen, 2, board.StyledText("PR", [style]*2), palette, 80)
        screen.move(10, 5)
        screen.refresh()
        sys.stdout.write("\\x1b]0;TEST-FRAME\\x07")
        sys.stdout.flush()
curses.wrapper(paint)
'''
        child = subprocess.Popen([sys.executable, "-c", script], stdin=slave, stdout=slave,
                                 stderr=subprocess.PIPE, cwd=Path(__file__).parents[1],
                                 env=dict(os.environ, TERM="xterm-256color"))
        os.close(slave)
        data = b""
        try:
            while select.select([master], [], [], 5)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                data += chunk
            _, error = child.communicate(timeout=5)
            self.assertEqual(child.returncode, 0, error.decode())
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            os.close(master)
        first, second, _ = data.decode().split("\x1b]0;TEST-FRAME\x07")
        grid = TerminalGrid()
        cells = grid.feed(frame(first, cols=80, rows=20))
        self.assertEqual(cells[2][1].hyperlink, "https://example.com")
        self.assertEqual((cells[2][1].fg, cells[2][1].bold), (pyte.graphics.FG_BG_256[4], True))
        self.assertEqual((grid.screen.cursor.x, grid.screen.cursor.y), (5, 10))
        cells = grid.feed(frame(second, 2, False, 80, 20))
        self.assertFalse(getattr(cells[2][1], "hyperlink", None))
        self.assertEqual(cells[2][1].data, "P")

    def test_links_follow_wrapping_edits_and_scroll(self):
        grid = TerminalGrid()
        cells = grid.feed(frame(osc("https://example.com") + "abcdefgh" + osc(""), cols=5, rows=2))
        self.assertEqual(cells[1][0].hyperlink, "https://example.com")
        cells = grid.feed(frame("\x1b[1;1HX\x1b[K", 2, False, 5, 2))
        self.assertTrue(all(not getattr(cell, "hyperlink", None) for cell in cells[0]))
        cells = grid.feed(frame("\x1b[2;1H\n", 3, False, 5, 2))
        self.assertEqual(cells[0][0].hyperlink, "https://example.com")
        self.assertTrue(all(not getattr(cell, "hyperlink", None) for cell in cells[1]))

    def test_sgr_and_wide_characters_do_not_lose_links(self):
        grid = TerminalGrid()
        cells = grid.feed(frame(osc("file:///tmp/a.cc") + "界\x1b[0me\u0301" + osc("")))
        self.assertEqual(cells[0][0].hyperlink, "file:///tmp/a.cc")
        self.assertEqual(cells[0][2].hyperlink, "file:///tmp/a.cc")
        self.assertFalse(getattr(cells[0][3], "hyperlink", None))
        line = board.live_grid_lines(cells, 20, 5)[0]
        self.assertEqual(line.styles[1].hyperlink, "file:///tmp/a.cc")
        cells = grid.feed(frame("plain", 2, True))
        self.assertFalse(getattr(cells[0][0], "hyperlink", None))

    def test_link_open_and_close_can_cross_frame_boundaries(self):
        grid = TerminalGrid()
        grid.feed(frame("\x1b]8;;https://exam"))
        cells = grid.feed(frame("ple.com\x1b\\PR", 2, False))
        self.assertEqual(cells[0][0].hyperlink, "https://example.com")
        cells = grid.feed(frame("\x1b]8;;\x07!", 3, False))
        self.assertIsNone(cells[0][2].hyperlink)


if __name__ == "__main__":
    unittest.main()
