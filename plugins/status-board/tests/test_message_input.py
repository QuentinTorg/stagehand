"""Paste safety and batching, including the actual curses/PTY input boundary."""

from collections import deque
import curses
import fcntl
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import board


class MessageInputTests(unittest.TestCase):
    def reader(self, text):
        keys = deque(text)
        screen = Mock()
        def read():
            if not keys:
                raise curses.error()
            return keys.popleft()
        screen.get_wch.side_effect = read
        return board.MessageInput(screen), keys

    def test_unbracketed_text_batches_without_eating_send_or_navigation(self):
        reader, _ = self.reader("x" * 3000 + "\r" + "next" + "\x10q")
        self.assertEqual(reader.read(batch=True), board.InsertText("x" * 3000))
        self.assertEqual(reader.read(batch=True), "\r")
        self.assertEqual(reader.read(batch=True), board.InsertText("next"))
        self.assertEqual(reader.read(batch=True), board.SHORTCUT_PREFIX)
        self.assertEqual(reader.read(), "q")

    def test_fragmented_paste_preserves_unicode_and_newlines_not_commands(self):
        reader, keys = self.reader("\x1b[200~café ☃\r")
        self.assertEqual(reader.read(), board.InsertText("café ☃\n"))
        self.assertTrue(reader.pasting)
        keys.extend("\nnext\tline\x07\x10\rfinish\x1b[20")
        self.assertEqual(reader.read(), board.InsertText("next\tline\nfinish"))
        self.assertTrue(reader.pasting)
        keys.extend("1~\r")
        self.assertEqual(reader.read(), board.InsertText(""))
        self.assertFalse(reader.pasting)
        self.assertEqual(reader.read(), "\r")
        self.assertEqual(reader.screen.keypad.call_args.args, (True,))

    def test_escape_does_not_discard_following_typing(self):
        reader, _ = self.reader("\x1bqhello")
        self.assertEqual(reader.read(), "\x1b")
        self.assertEqual(reader.read(batch=True), board.InsertText("qhello"))

    def test_repeat_batches_preserve_mixed_edit_and_command_order(self):
        keys = [curses.KEY_LEFT] * 100 + [curses.KEY_DC] * 20 + list("new") + ["\x7f"] * 5 + ["\r"]
        reader, _ = self.reader(keys)
        self.assertEqual(reader.read(batch=True), board.RepeatedKey(curses.KEY_LEFT, 100))
        self.assertEqual(reader.read(batch=True), board.RepeatedKey(curses.KEY_DC, 20))
        self.assertEqual(reader.read(batch=True), board.InsertText("new"))
        self.assertEqual(reader.read(batch=True), board.RepeatedKey("\x7f", 5))
        self.assertEqual(reader.read(batch=True), "\r")

    def test_repeated_backspace_edits_in_one_batch_and_flushes_on_exit(self):
        with tempfile.TemporaryDirectory() as root:
            args = SimpleNamespace(tasks=Path(root) / "tasks", offline=True)
            path = board.draft_path(args, None)
            board.save_draft(path, "x" * 5000)
            reader, _ = self.reader(["\x7f"] * 500 + [board.SHORTCUT_PREFIX])
            reader.screen.getmaxyx.return_value = (74, 220)
            with patch.object(board.curses, "curs_set"), patch.object(
                board, "save_draft", wraps=board.save_draft
            ) as save:
                editor = board.compose(reader.screen, args, None, input_reader=reader)
                for _ in range(10):
                    try:
                        next(editor)
                    except StopIteration as result:
                        self.assertIs(result.value, board.SHORTCUT_REQUEST)
                        break
                else:
                    self.fail("Repeated keys were not processed in a bounded number of frames")
            self.assertEqual(path.read_text(), "x" * 4500)
            save.assert_called_once_with(path, "x" * 4500)

    def test_draft_debounce_deadline_and_failed_save_keep_latest_text(self):
        with tempfile.TemporaryDirectory() as root, patch.object(board.time, "monotonic") as clock:
            path = Path(root) / "draft"
            draft = board.Draft(path)
            clock.return_value = 0
            draft.update("a")
            clock.return_value = .1
            draft.flush()
            self.assertFalse(path.exists())
            clock.return_value = .15
            draft.update("ab")
            clock.return_value = .3
            draft.flush()
            self.assertFalse(path.exists())
            clock.return_value = .36
            draft.flush()
            self.assertEqual(path.read_text(), "ab")
            # Continuous input still reaches disk once the maximum dirty age expires.
            for tick in range(4, 15):
                clock.return_value = tick / 10
                draft.update(str(tick))
                draft.flush()
            clock.return_value = 1.41
            draft.flush()
            self.assertEqual(path.read_text(), "14")
            draft.update("unsaved")
            with patch.object(board, "save_draft", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    draft.flush(force=True)
                with self.assertRaises(OSError):
                    draft.save("")
            self.assertEqual(draft.text, "unsaved")
            self.assertEqual(draft.saved, "14")
            draft.flush(force=True)
            self.assertEqual(path.read_text(), "unsaved")
            with patch.object(board, "save_draft") as save:
                draft.flush(force=True)
                save.assert_not_called()

    def test_large_paste_yields_bounded_chunks_without_losing_text(self):
        text = "λ" * 20000
        reader, _ = self.reader("\x1b[200~" + text + "\x1b[201~")
        chunks = [reader.read().text]
        while reader.pasting:
            chunks.append(reader.read().text)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(chunk) <= 8192 for chunk in chunks))
        self.assertEqual(len(chunks), 3)

    def test_real_terminal_paste_is_batched_and_only_explicit_enter_sends(self):
        # Isolate the terminal and mock delivery: no live agent receives test text.
        source = '''
import curses, json, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
import board
root = Path(sys.argv[2])
board.board_snapshot = lambda *args: ([], [], {"status": "idle"})
board.controller_snapshot = lambda *args: {"status": "idle", "output": "Ready"}
saves = 0
original_save = board.save_draft
def save(path, text):
    global saves
    saves += 1
    original_save(path, text)
    (root / "saves").write_text(str(saves))
board.save_draft = save
def send(args, row, text):
    (root / "sent").write_text(text)
    return True, "Delivered"
board.send_message = send
curses.wrapper(board.display, SimpleNamespace(tasks=root / "tasks", offline=True, interval=5))
'''
        with tempfile.TemporaryDirectory() as root:
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 74, 220, 0, 0))
            process = subprocess.Popen([sys.executable, "-c", source, str(Path(board.__file__).parent), root],
                                       stdin=slave, stdout=slave, stderr=slave,
                                       env=dict(os.environ, TERM="xterm-256color"), start_new_session=True)
            os.close(slave)
            output = bytearray()
            def wait_for(predicate):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .01)[0]:
                        output.extend(os.read(master, 65536))
                    if predicate():
                        return
                self.fail(f"Terminal did not reach expected state: {output[-1500:]!r}")
            draft = Path(root) / "board-drafts" / "orchestrator.txt"
            sent, saves = Path(root) / "sent", Path(root) / "saves"
            def draft_is(text):
                return draft.exists() and draft.read_text() == text
            try:
                wait_for(lambda: b"\x1b[?2004h" in output)
                text = "café ☃ " * 400
                os.write(master, ("\x1b[200~" + text + "\r\nnext\x07\x10\x1b[20").encode())
                expected = text + "\nnext"
                wait_for(lambda: draft_is(expected))
                self.assertFalse(sent.exists())
                self.assertLessEqual(int(saves.read_text()), 2)
                os.write(master, b"1~")
                # Another paste proves a split end marker restored normal input.
                os.write(master, b"\x1b[200~!\x1b[201~")
                wait_for(lambda: draft_is(expected + "!"))
                self.assertFalse(sent.exists())
                # Fast repeat input must not leave a long deletion backlog after
                # key release, or force a filesystem write for every Backspace.
                before = int(saves.read_text())
                os.write(master, b"\x7f" * 500)
                expected = (expected + "!")[:-500]
                wait_for(lambda: draft_is(expected))
                self.assertLessEqual(int(saves.read_text()) - before, 2)
                os.write(master, b"\r")
                wait_for(lambda: sent.exists())
                self.assertEqual(sent.read_text(), expected)
                os.write(master, b"\x10q")
                wait_for(lambda: b"\x1b[?2004l" in output)
                process.wait(timeout=5)
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)


if __name__ == "__main__":
    unittest.main()
