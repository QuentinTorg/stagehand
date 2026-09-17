"""Preserve preview links without sending source terminal controls to the host."""

import codecs
import re
from urllib.parse import urlsplit


def safe_link(value):
    # OSC payloads are untrusted terminal output, not commands or host escapes.
    if not value or len(value) > 8192 or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
        return None
    try:
        return value if urlsplit(value).scheme.lower() in {"http", "https", "file", "mailto"} else None
    except ValueError:
        return None


class LinkStream:
    """Extract bounded OSC 8 strings, including sequences split across frames."""

    start = re.compile(r"\x1b[\]PX^_]|[\x90\x98\x9d\x9e\x9f]|\x1b$")

    def __init__(self, feed, set_link):
        self.feed_text, self.set_link = feed, set_link
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.pending = ""

    def feed(self, data):
        text = self.pending + self.decoder.decode(data)
        self.pending = ""
        while text:
            match = self.start.search(text)
            if not match:
                self.feed_text(text)
                return
            self.feed_text(text[:match.start()])
            text = text[match.start():]
            opener = match.group()
            if opener == "\x1b":
                self.pending = text
                return
            osc = opener in {"\x1b]", "\x9d"}
            end = re.search(r"\x1b\\|\x9c|\x07" if osc else r"\x1b\\|\x9c", text[len(opener):])
            if end is None:
                if len(text) > 65536:
                    raise ValueError("Preview control string exceeds supported length")
                self.pending = text
                return
            payload = text[len(opener):len(opener) + end.start()]
            if osc and payload.startswith("8;"):
                parts = payload.split(";", 2)
                self.set_link(safe_link(parts[2]) if len(parts) == 3 else None)
            # Other string controls (including clipboard writes) never escape.
            text = text[len(opener) + end.end():]


def link_sgr(style):
    values = ["0"]
    for enabled, code in ((style.bold, "1"), (style.dim, "2"), (style.italic, "3"),
                          (style.underline, "4"), (style.reverse, "7")):
        if enabled:
            values.append(code)
    for color, prefix in ((style.foreground, "38"), (style.background, "48")):
        if isinstance(color, tuple):
            values.extend([prefix, "2", *(str(c) for c in color)])
        elif color >= 0:
            values.extend([prefix, "5", str(color)])
    return "\x1b[" + ";".join(values) + "m"


class LinkedScreen:
    """Add OSC 8 after curses paints; Herdr remains responsible for activation."""

    def __init__(self, screen, output):
        self.screen, self.output = screen, output
        self.links, self.previous = {}, {}

    def __getattr__(self, name):
        return getattr(self.screen, name)

    def erase(self):
        self.links = {}
        return self.screen.erase()

    def preview_row(self, y, runs):
        self.links[y] = tuple(runs)

    def refresh(self):
        height, width = self.screen.getmaxyx()
        current = {y: tuple(run for run in runs if run[0] + run[2] < width)
                   for y, runs in self.links.items() if 0 <= y < height}
        # Repaint changed/removed link rows so invisible old targets cannot survive
        # a scroll, view switch, resize, or a link whose label stayed unchanged.
        for y in self.previous.keys() | current.keys():
            if 0 <= y < height and self.previous.get(y) != current.get(y):
                self.screen.redrawln(y, 1)
        self.screen.refresh()
        chunks = []
        for y, runs in current.items():
            for x, text, _, style in runs:
                url = safe_link(style.hyperlink)
                if url:
                    chunks.append(f"\x1b[{y + 1};{x + 1}H{link_sgr(style)}\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\")
        if chunks:
            # Curses owns cursor and rendition state. Preserve both around the
            # bounded text overlay, including while the message editor is active.
            self.output.write("\x1b7" + "".join(chunks) + "\x1b8")
            self.output.flush()
        self.previous = current
