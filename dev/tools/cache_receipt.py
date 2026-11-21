#!/usr/bin/env python3
"""Summarize Bazel's --execution_log_json_file by mnemonic and cache result."""

import argparse
from collections import Counter
import json
from pathlib import Path


def spawns(stream):
    # Bazel concatenates SpawnExec JSON objects directly (including `}{`).
    decoder = json.JSONDecoder()
    buf = ""
    while chunk := stream.read(1024 * 1024):
        buf += chunk
        i = 0
        while i < len(buf):
            if buf[i].isspace():
                i += 1
                continue
            try:
                spawn, i = decoder.raw_decode(buf, i)
            except json.JSONDecodeError:
                break  # The next chunk may complete this object.
            yield spawn
        buf = buf[i:]
    if buf.strip():
        raise ValueError("invalid or incomplete execution log")


def summarize(log):
    counts = Counter()
    with log.open() as stream:
        for spawn in spawns(stream):
            runner = spawn.get("runner", "")
            if spawn.get("cacheHit", False) or runner in ("disk cache hit", "remote cache hit"):
                state = "hit"
            elif not spawn.get("cacheable", False):
                state = "uncacheable"
            else:
                state = "miss"
            counts[spawn["mnemonic"], state] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    counts = summarize(args.log)
    for (mnemonic, state), count in sorted(counts.items()):
        print(f"{count:6d} {mnemonic:24s} {state}")
    totals = Counter()
    for (_, state), count in counts.items():
        totals[state] += count
    total = totals["hit"] + totals["miss"]
    if total:
        print(f"{totals['hit']}/{total} cacheable spawns hit ({totals['hit'] / total:.2%}); "
              f"{totals['uncacheable']} uncacheable spawns")


if __name__ == "__main__":
    main()
