#!/usr/bin/env python3
"""Entry program for make.fun's news-image-20261118 bounty.

The entry is one image that sums up the world news of Wednesday
18 November 2026, drawn as a newspaper front page: a dated masthead over
six illustrated stories -- the APEC summit opening in Shenzhen, US and
Iranian strikes traded over the Gulf, Ukraine's strike on the Crimean
Bridge, Nvidia's record $116bn quarter as Anthropic's market debut
priced, the Gaza ceasefire warning, and Voyager 1 nearing one light-day
from Earth.

The picture itself is committed beside this file as ``entry.png`` (a
whole PNG, 1024 x 1024, well under the 1 MiB gate). This program's job
is deliberately small and exact: validate the payload against the
competition's gate, then copy it byte for byte to the output directory,
so the grader's two runs produce identical bytes every time.

Run it the way the grader does (no network, standard library only):

    python3 main.py            # writes /output/entry.png

Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for
/output:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import hashlib
import os
import sys
from pathlib import Path

# The gate: a whole PNG or JPEG, at most 1 MiB, at most 1024 x 1024.
MAX_BYTES = 1_048_576
MAX_SIDE = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def payload_bytes() -> bytes:
    """Read the committed image and check it against the gate's rules."""
    path = Path(__file__).resolve().parent / "entry.png"
    data = path.read_bytes()
    if data.startswith(PNG_MAGIC):
        # IHDR: width and height are big-endian uint32 at bytes 16..24.
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
    elif data.startswith(JPEG_MAGIC):
        width = height = 0  # dimensions checked when the image was made
    else:
        raise SystemExit("entry.png is neither a PNG nor a JPEG image")
    if len(data) > MAX_BYTES:
        raise SystemExit(f"entry.png is {len(data)} bytes; the gate allows {MAX_BYTES}")
    if width > MAX_SIDE or height > MAX_SIDE:
        raise SystemExit(f"entry.png is {width}x{height}; the gate allows {MAX_SIDE}x{MAX_SIDE}")
    return data


def main() -> int:
    data = payload_bytes()
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    target.write_bytes(data)
    if target.read_bytes() != data:
        raise SystemExit("write verification failed: output differs from payload")
    digest = hashlib.sha256(data).hexdigest()
    print(f"wrote {target} ({len(data)} bytes, sha256 {digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
