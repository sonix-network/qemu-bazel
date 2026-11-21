"""Check QEMU registration without starting a guest."""

import subprocess
import sys

from python.runfiles import runfiles


def main():
    emulator = runfiles.Create().Rlocation(sys.argv[1])
    profile = sys.argv[2]

    def output(*args):
        result = subprocess.run(
            [emulator, *args], check=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr

    version = output("--version")
    if not version.startswith("QEMU emulator version 11.1.2"):
        raise AssertionError(version)
    accelerators = output("-accel", "help").splitlines()
    if accelerators[1:] != ["whpx"]:
        raise AssertionError(accelerators)
    if profile != "custom":
        machines = {line.split()[0] for line in output("-machine", "help").splitlines() if line.strip()}
        has_i440fx = "pc" in machines or any(m.startswith("pc-i440fx-") for m in machines)
        if "q35" not in machines or has_i440fx != (profile == "qemu-default"):
            raise AssertionError(machines)
    for flag, entry in [("-device", 'name "isa-serial"'), ("-trace", "handle_hmp_command")]:
        help_text = output(flag, "help")
        if entry not in help_text:
            raise AssertionError(help_text)


if __name__ == "__main__":
    main()
