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

Validation is structural, not a magic-byte sniff: for a PNG the whole
chunk stream is walked, IHDR must come first, every critical chunk's
CRC is checked, and IEND must end the file exactly -- a corrupted
payload fails loudly here instead of being written out as a broken
image. The write itself is atomic (temp file, fsync, rename), and the
written file's sha256 is compared against the payload's before the
program reports success.

Run it the way the grader does (no network, standard library only):

    python3 main.py            # writes /output/entry.png

Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for
/output:

    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import hashlib
import os
import sys
import zlib
from pathlib import Path

# The gate: a whole PNG or JPEG, at most 1 MiB, at most 1024 x 1024.
MAX_BYTES = 1_048_576
MAX_SIDE = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
# PNG chunk types whose corruption breaks decoding; their CRCs are
# verified while walking the stream. Ancillary chunks are skipped.
CRITICAL_CHUNKS = frozenset({b"IHDR", b"PLTE", b"IDAT", b"IEND"})


def check_png(data: bytes) -> tuple[int, int]:
    """Walk a PNG's chunk stream, verifying its structure and CRCs.

    Returns ``(width, height)`` from IHDR. Raises SystemExit on any
    defect -- a truncated chunk, IHDR out of place, a bad CRC on a
    critical chunk, a missing IEND, or bytes trailing IEND -- so a
    corrupted payload never reaches the output directory.
    """
    pos = len(PNG_MAGIC)
    width = height = 0
    seen_iend = False
    while pos < len(data):
        # Each chunk is: 4-byte length, 4-byte type, data, 4-byte CRC.
        if pos + 8 > len(data):
            raise SystemExit("entry.png is truncated inside a chunk header")
        length = int.from_bytes(data[pos:pos + 4], "big")
        ctype = data[pos + 4:pos + 8]
        end = pos + 8 + length + 4
        if end > len(data):
            raise SystemExit(f"entry.png is truncated inside chunk {ctype!r}")
        body = data[pos + 8:pos + 8 + length]
        if ctype in CRITICAL_CHUNKS:
            stored_crc = int.from_bytes(data[pos + 8 + length:end], "big")
            if zlib.crc32(ctype + body) & 0xFFFFFFFF != stored_crc:
                raise SystemExit(f"entry.png has a bad CRC in chunk {ctype.decode()}")
        if ctype == b"IHDR":
            if pos != len(PNG_MAGIC):
                raise SystemExit("entry.png: IHDR is not the first chunk")
            width = int.from_bytes(body[0:4], "big")
            height = int.from_bytes(body[4:8], "big")
        pos = end
        if ctype == b"IEND":
            seen_iend = True
            break
    if not seen_iend:
        raise SystemExit("entry.png has no IEND chunk")
    if pos != len(data):
        raise SystemExit("entry.png has trailing bytes after IEND")
    return width, height


def payload_bytes() -> bytes:
    """Read the committed image and check it against the gate's rules."""
    path = Path(__file__).resolve().parent / "entry.png"
    data = path.read_bytes()
    if data.startswith(PNG_MAGIC):
        width, height = check_png(data)
    elif data.startswith(JPEG_MAGIC):
        width = height = 0  # dimensions checked when the image was made
    else:
        raise SystemExit("entry.png is neither a PNG nor a JPEG image")
    if len(data) > MAX_BYTES:
        raise SystemExit(f"entry.png is {len(data)} bytes; the gate allows {MAX_BYTES}")
    if width > MAX_SIDE or height > MAX_SIDE:
        raise SystemExit(f"entry.png is {width}x{height}; the gate allows {MAX_SIDE}x{MAX_SIDE}")
    return data


def write_atomically(target: Path, data: bytes) -> None:
    """Write ``data`` to ``target`` via a temp file and a rename.

    The temp file lives in the same directory, is flushed and fsynced,
    and is then renamed over the target, so a crash mid-write can never
    leave a torn entry.png behind: readers see the old file or the
    complete new one, nothing in between.
    """
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)


def main() -> int:
    data = payload_bytes()
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    write_atomically(target, data)
    digest = hashlib.sha256(data).hexdigest()
    written = hashlib.sha256(target.read_bytes()).hexdigest()
    if written != digest:
        raise SystemExit("write verification failed: output differs from payload")
    print(f"wrote {target} ({len(data)} bytes, sha256 {digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
