#!/usr/bin/env python3
"""Recover files that a workflow printed into its log as gzip+base64 blocks.

Usage: unpack_log.py job.log out-dir
"""
import base64
import gzip
import os
import re
import sys

STAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?")


def main() -> int:
    log, out = sys.argv[1], sys.argv[2]
    current, chunks = None, []
    with open(log, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = STAMP.sub("", raw.rstrip("\n"))
            if line.startswith("=====BEGIN "):
                current, chunks = line[len("=====BEGIN "):].strip(), []
            elif line.startswith("=====END ") and current:
                dest = os.path.join(out, current)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as w:
                    w.write(gzip.decompress(base64.b64decode("".join(chunks))))
                print("recovered", dest)
                current = None
            elif current:
                chunks.append(line.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
