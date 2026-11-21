#!/usr/bin/env python3
"""Compare registered QEMU interfaces without starting a guest."""

import argparse
import difflib
import hashlib
import os
from pathlib import Path
import subprocess


CHECKS = [
    ("--version",),
    ("-accel", "help"),
    ("-machine", "help"),
    ("-device", "help"),
    ("-trace", "help"),
]


def output(binary, args):
    result = subprocess.run(
        [binary, *args], env={**os.environ, "LC_ALL": "C"},
        check=True, text=True, capture_output=True,
    )
    if result.stderr:
        raise ValueError(f"{binary} {' '.join(args)} wrote to stderr: {result.stderr.strip()}")
    lines = result.stdout.splitlines(keepends=True)
    # Type and trace registration order can differ with link order.
    return sorted(lines) if args[-1] == "help" else lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bazel_binary", type=Path)
    parser.add_argument("meson_binary", type=Path)
    args = parser.parse_args()
    binaries = [args.bazel_binary.resolve(), args.meson_binary.resolve()]
    for label, binary in zip(("Bazel", "Meson"), binaries):
        with binary.open("rb") as stream:
            print(f"{label} ELF SHA-256: {hashlib.file_digest(stream, 'sha256').hexdigest()}")
        dynamic = subprocess.check_output(["readelf", "-d", binary], text=True)
        print(f"{label} DT_NEEDED:", ", ".join(line.partition("[")[2].split("]")[0]
                                              for line in dynamic.splitlines() if "(NEEDED)" in line))

    success = True
    for argv in CHECKS:
        bazel, meson = (output(binary, argv) for binary in binaries)
        if bazel != meson:
            print(f"{' '.join(argv)}: differs")
            print("".join(difflib.unified_diff(meson, bazel, "Meson", "Bazel")), end="")
            success = False
        else:
            print(f"{' '.join(argv)}: matches ({len(bazel)} lines)")
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
