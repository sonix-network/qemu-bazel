"""Boot the bare-metal Rust ELF with the resolved native QEMU toolchain."""

import os
from pathlib import Path
import subprocess
import sys
import unittest

from accelerator import accelerator_available
from python.runfiles import runfiles


class UartTest(unittest.TestCase):
    def test_pvh_uart_and_debug_exit(self):
        locations = runfiles.Create()
        manifest = Path(locations.Rlocation(sys.argv[1]))
        accelerator, qemu, firmware, kernel = manifest.read_text(encoding="utf-8").splitlines()
        self.assertEqual(accelerator, "whpx" if os.name == "nt" else "kvm")
        bios = Path(locations.Rlocation(firmware + "/bios-256k.bin")).parent
        for rom in ("bios-256k.bin", "pvh.bin", "kvmvapic.bin"):
            self.assertTrue((bios / rom).is_file(), f"missing staged firmware: {rom}")
        if not accelerator_available(accelerator):
            self.skipTest(f"{accelerator.upper()} is unavailable on this host")

        serial = Path(os.environ["TEST_TMPDIR"]) / "uart.log"
        environment = {"LC_ALL": "C"}
        if os.name == "nt":
            # The Windows crypto provider needs SystemRoot during QEMU startup.
            environment["SystemRoot"] = os.environ["SystemRoot"]
        qemu = subprocess.run(
            [
                locations.Rlocation(qemu), "-L", str(bios), "-machine", "q35",
                "-accel", accelerator, "-cpu", "host", "-m", "64M", "-nodefaults",
                "-nic", "none", "-display", "none", "-monitor", "none",
                "-serial", f"file:{serial}", "-no-reboot",
                "-device", "isa-debug-exit,iobase=0xf4,iosize=4",
                "-kernel", locations.Rlocation(kernel),
            ],
            env=environment,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(qemu.returncode, 85, (qemu.stdout, qemu.stderr))
        self.assertEqual(serial.read_bytes(), b"hello from x86_64\n")
        print(f"{accelerator} COM1: hello from x86_64\nQEMU exit status: 85")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
