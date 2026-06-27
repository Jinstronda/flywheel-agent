"""Cross-task memory. On the graded run memory is FLYWHEEL_MEMORY_DIR, a persistent directory that
survives across tasks. Whatever you write under it (this JSON file, or your own sqlite / vector DB
bundled in your image) IS your memory. There is no memory service; FLYWHEEL_MEMORY_URL is not set
on the graded run, so the url path below stays dormant and the JSON-file path is what runs. The
optional url is kept only for a self-hosted store you stand up yourself.

It survives across the whole task stream on the memory-ON run and is wiped between tasks on the
memory-OFF run. The gap between the two arms is part of your grade, so a memory you never read is
worth nothing: store what generalizes (procedures, login patterns, solved-task recipes), recall
it on later tasks.
"""
import json
import os
import urllib.request


class Memory:
    def __init__(self, dir, trace, url=None):
        self.url = (url or "").rstrip("/")
        self.dir = dir
        self.path = os.path.join(dir, "memory.json")
        self._t = trace
        os.makedirs(dir, exist_ok=True)

    def _post(self, path, body=None):
        req = urllib.request.Request(self.url + path, data=json.dumps(body or {}).encode(),
                                     headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    def _load(self):
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception:
            return {}

    def read(self):
        if self.url:
            return self._post("/read")
        self._t("memory_read")
        return self._load()

    def write(self, key, value):
        if self.url:
            return self._post("/write", {"key": key, "value": value})
        self._t("memory_write", key=key)
        d = self._load()
        d[key] = value
        with open(self.path, "w") as f:
            json.dump(d, f)
