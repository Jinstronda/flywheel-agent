"""Download AppWorld's task data with a progress bar, a timeout, and resumable retries.

  python tools/download_data.py        # writes into $APPWORLD_ROOT/data (default ./aw/data)

Why this exists: `appworld download data` (the upstream CLI) buffers the whole bundle into RAM
with `requests.get()` and no timeout and no progress, so it prints "around 15 seconds" and then
goes silent. On a slow link, a VPN, or a proxy in front of AWS S3 it can stall forever with no
output. This streams the same bundle (~33 MB) to disk in chunks, shows progress, times out a dead
socket, and resumes with a Range request on retry, then unpacks it with AppWorld's own routine.
The result is byte-identical to the upstream command.
"""
import os
import sys
import time

import requests

from appworld.common.constants import PASSWORD, SALT
from appworld.common.path_store import path_store
from appworld.common.utils import unpack_bundle

URL = "https://s3.us-west-2.amazonaws.com/appworld.dev/data-0.1.0.bundle"
CHUNK = 1 << 16  # 64 KB
RETRIES = 5


def _bar(done, total, started):
    pct = done / total if total else 0
    width = 30
    fill = int(width * pct)
    mb = done / 1e6
    speed = done / max(time.time() - started, 1e-9) / 1e6
    tail = f"{mb:5.1f} MB" + (f" / {total/1e6:.1f} MB" if total else "")
    sys.stdout.write(f"\r  [{'#'*fill}{'.'*(width-fill)}] {pct*100:5.1f}%  {tail}  {speed:4.1f} MB/s")
    sys.stdout.flush()


def fetch(url, dest):
    """Stream to dest with progress; resume from partial bytes across retries."""
    for attempt in range(1, RETRIES + 1):
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with requests.get(url, stream=True, timeout=(30, 60), headers=headers) as r:
                if r.status_code not in (200, 206):
                    raise requests.HTTPError(f"status {r.status_code}")
                total = int(r.headers.get("Content-Length", 0)) + have
                started = time.time()
                with open(dest, "ab" if have else "wb") as f:
                    for chunk in r.iter_content(CHUNK):
                        f.write(chunk)
                        have += len(chunk)
                        _bar(have, total, started)
            print()
            return
        except (requests.RequestException, OSError) as e:
            print(f"\n  attempt {attempt}/{RETRIES} failed ({e}); retrying...")
            time.sleep(3)
    raise SystemExit("download failed after retries; check your network/VPN/proxy and try again.")


def main():
    if os.path.exists(path_store.data):
        print(f"data already at {path_store.data}, removing it.")
        import shutil
        shutil.rmtree(path_store.data)
    os.makedirs(path_store.temp, exist_ok=True)
    bundle = os.path.join(path_store.temp, "data-0.1.0.bundle")
    print(f"downloading data -> {path_store.data}")
    fetch(URL, bundle)
    os.makedirs(path_store.data, exist_ok=True)
    unpack_bundle(bundle_file_path=bundle, base_directory=path_store.root, password=PASSWORD, salt=SALT)
    os.remove(bundle)
    print(f"data prepared at: {path_store.data}")


if __name__ == "__main__":
    main()
