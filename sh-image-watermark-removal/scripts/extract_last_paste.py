"""Extract the most recently pasted image from the local opencode session DB.

Pasted images never become file paths in the message text - opencode stores
them as base64 data URLs inside the `part` table of opencode.db. This script
pulls the newest one out to a real file.

Usage:
  python extract_last_paste.py [output.png]
"""
import base64
import json
import os
import sqlite3
import sys

DB = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "opencode.db")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "pasted-image.png"
    if not os.path.exists(DB):
        sys.exit(f"opencode.db not found: {DB}")
    con = sqlite3.connect(DB)
    # newest parts first; part.data is JSON like {"type":"file","url":"data:image/png;base64,..."}
    rows = con.execute(
        "select data from part order by time_created desc limit 500"
    )
    for (data,) in rows:
        try:
            d = json.loads(data)
        except (TypeError, ValueError):
            continue
        url = d.get("url", "") if isinstance(d, dict) else ""
        if d.get("type") == "file" and url.startswith("data:image"):
            b64 = url.split(",", 1)[1]
            with open(out, "wb") as f:
                f.write(base64.b64decode(b64))
            print("saved:", os.path.abspath(out))
            return
    sys.exit("no pasted image found in recent parts")


if __name__ == "__main__":
    main()
