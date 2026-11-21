#!/usr/bin/env python3
"""Compare the QEMU translation units and C flags in two build graphs.

Inputs: Ninja `-t commands qemu-system-x86_64` and Bazel
`aquery --output=jsonproto 'mnemonic("CppCompile", deps(TARGET))'`.
Use --bazel-source-prefix external/qemu+/ for an index registry consumer.
This reports differences; it does not treat different graphs as equivalent.
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shlex


def collect(commands, source_key):
    objects = Counter()
    flags = defaultdict(Counter)
    for argv in commands:
        if "-c" not in argv or "-o" not in argv:
            continue
        source = source_key(argv[argv.index("-c") + 1])
        if source is None or not source.endswith(".c"):
            continue
        objects[source] += 1
        flags[source].update(flag for flag in argv if flag.startswith((
            "-D", "-U", "-W", "-std=", "-O", "-g", "-m", "-pthread", "-f",
        )) and not flag.startswith(("-frandom-seed=", "-fdiagnostics-color")))
    return objects, flags


def compare(bazel, meson):
    bazel_objects, bazel_flags = bazel
    meson_objects, meson_flags = meson
    for label, counts in (("Bazel", bazel_objects), ("Meson", meson_objects)):
        if not counts:
            raise ValueError(f"no QEMU compile actions found for {label}")
        print(f"{label}: {sum(counts.values())} objects, {len(counts)} distinct sources")
    for label, counts in (("Bazel-only", bazel_objects - meson_objects),
                          ("Meson-only", meson_objects - bazel_objects)):
        print(f"{label} objects: {sum(counts.values())}")
        for path, count in sorted(counts.items()):
            print(f"  {count} {path}")
    for label, left, right in (("Bazel-only", bazel_flags, meson_flags),
                               ("Meson-only", meson_flags, bazel_flags)):
        delta = Counter()
        for path in left.keys() & right.keys():
            delta.update(left[path] - right[path])
        print(f"{label} flags on shared sources (occurrences):")
        for flag, count in sorted(delta.items()):
            print(f"  {count:5d} {flag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bazel_aquery", type=Path)
    parser.add_argument("meson_commands", type=Path)
    parser.add_argument("--bazel-source-prefix", default="")
    args = parser.parse_args()

    def bazel_key(path):
        if path.startswith("bazel-out/"):
            path = path.split("/bin/", 1)[-1]
        if args.bazel_source_prefix:
            if not path.startswith(args.bazel_source_prefix):
                return None
            return path.removeprefix(args.bazel_source_prefix)
        return None if path.startswith("external/") else path

    def meson_key(path):
        if "/qemu-11.1.2/" in path:
            return path.split("/qemu-11.1.2/", 1)[1]
        return None if path.startswith(("../", "/")) else path

    actions = json.loads(args.bazel_aquery.read_text())["actions"]
    bazel = collect((action.get("arguments", []) for action in actions
                     if action["mnemonic"] == "CppCompile"), bazel_key)
    with args.meson_commands.open() as stream:
        # Ninja also prints generator commands. Only the C compiler has
        # both a -c source and an -o object in this reference build.
        meson = collect((shlex.split(line) for line in stream
                         if " -c " in line and " -o " in line), meson_key)
    compare(bazel, meson)


if __name__ == "__main__":
    main()
