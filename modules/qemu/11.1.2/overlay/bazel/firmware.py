"""Stage the selected release ROMs in a QEMU -L directory."""

from pathlib import Path
from shutil import copyfile
import sys


def main(output, *inputs):
    directory = Path(output)
    sources = [Path(p) for p in inputs]
    names = {source.name for source in sources}
    if len(names) != len(sources):
        raise ValueError("duplicate firmware filenames")
    directory.mkdir(parents=True, exist_ok=True)
    for source in sources:
        copyfile(source, directory / source.name)


if __name__ == "__main__":
    main(*sys.argv[1:])
