"""Trace sink. Every capability the grader checks for (retrieval, tool/execute, model,
memory_read/write, reflect) lands here as one JSONL line. The grader reads this file, so an
honest trace is a faithful record of your run. When no trace file is set, events are dropped.
"""
import json


class Trace:
    def __init__(self, path=None):
        self.path = path

    def __call__(self, type, **kw):
        if not self.path:
            return
        with open(self.path, "a") as f:
            f.write(json.dumps({"type": type, **kw}) + "\n")
