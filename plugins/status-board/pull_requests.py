"""Best-effort PR lifecycle hints; they never advance a task's workflow state."""

from concurrent.futures import ThreadPoolExecutor
import json
import re
import subprocess
import time
from urllib.parse import urlsplit


def fetch_state(url):
    parsed = urlsplit(url)
    path = re.fullmatch(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)/?", parsed.path)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or not path:
        return None
    # Preserve Enterprise hosts; never turn a displayed link into a shell command.
    response = subprocess.run(
        ["gh", "api", "--hostname", parsed.netloc,
         f"repos/{path[1]}/{path[2]}/pulls/{path[3]}", "--jq", "{state: .state, merged_at: .merged_at}"],
        capture_output=True, text=True, check=True, timeout=5,
    )
    data = json.loads(response.stdout)
    if not isinstance(data, dict):
        return None
    if data.get("state") == "closed":
        return "merged" if data.get("merged_at") else "closed"
    return "open" if data.get("state") == "open" else None


class PullRequestStates:
    """Bounded asynchronous reads keep GitHub latency out of keyboard/mouse handling."""

    def __init__(self, interval=120):
        self.interval = interval
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="board-pr-state")
        self.pending, self.cached = {}, {}

    def snapshot(self, urls):
        wanted = set(urls)
        now = time.monotonic()
        for url, future in list(self.pending.items()):
            if future.done():
                try:
                    state = future.result()
                except (OSError, ValueError, TypeError, subprocess.SubprocessError):
                    state = None
                self.cached[url] = (state, now)
                del self.pending[url]
            elif url not in wanted and future.cancel():
                del self.pending[url]
        self.cached = {url: value for url, value in self.cached.items() if url in wanted}
        for url in wanted:
            if url not in self.pending and now - self.cached.get(url, (None, -float("inf")))[1] >= self.interval:
                self.pending[url] = self.pool.submit(fetch_state, url)
        return {url: self.cached[url][0] for url in wanted if url in self.cached and self.cached[url][0]}

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)


def marker(state):
    return {"closed": "×", "merged": "✓"}.get(state, "")
