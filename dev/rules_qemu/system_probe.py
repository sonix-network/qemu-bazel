"""Check the source-built tools and boot a bare-metal x86 guest when possible."""

import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from python.runfiles import runfiles


def accelerator_available(accelerator):
    if accelerator == "kvm":
        import fcntl

        try:
            with open("/dev/kvm", "rb+", buffering=0) as kvm:
                return fcntl.ioctl(kvm, 0xAE00, 0) == 12
        except OSError:
            return False
    try:
        platform = ctypes.WinDLL("WinHvPlatform.dll", use_last_error=True)
    except OSError:
        return False
    present = ctypes.c_uint32()
    if platform.WHvGetCapability(0, ctypes.byref(present), ctypes.sizeof(present), None) or not present.value:
        return False
    partition = ctypes.c_void_p()
    if platform.WHvCreatePartition(ctypes.byref(partition)):
        return False
    platform.WHvDeletePartition(partition)
    return True


def run(*args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT, text=True, timeout=30)


class SystemProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        locations = runfiles.Create()
        with open(locations.Rlocation(sys.argv[1]), encoding="utf-8") as manifest:
            configuration = json.load(manifest)
        cls.accelerator = configuration["accelerator"]
        cls.emulator = locations.Rlocation(configuration["emulator"])
        cls.image_tool = locations.Rlocation(configuration["image_tool"])
        cls.bios = locations.Rlocation(configuration["firmware"] + "/bios-256k.bin")

    def test_registration(self):
        self.assertEqual(self.accelerator, "whpx" if os.name == "nt" else "kvm")
        self.assertIn("QEMU emulator version 11.1.2", run(self.emulator, "--version"))
        self.assertEqual(run(self.emulator, "-accel", "help").splitlines()[1:], [self.accelerator])
        self.assertTrue(Path(self.bios).stat().st_size)
        self.assertIn("qemu-img version 11.1.2", run(self.image_tool, "--version"))
        with tempfile.TemporaryDirectory() as directory:
            disk = Path(directory, "disk.qcow2")
            run(self.image_tool, "create", "-f", "qcow2", disk, "1M")
            self.assertEqual(json.loads(run(self.image_tool, "info", "--output=json", disk))["format"], "qcow2")

    def test_boot(self):
        if not accelerator_available(self.accelerator):
            self.skipTest(f"{self.accelerator.upper()} unavailable in this environment")
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            disk = directory / "boot.img"
            serial = directory / "serial.log"
            # In real mode, write a marker to COM1 and exit with (0x2a << 1) | 1.
            marker = b"QEMU boot OK"
            code = bytearray(bytes.fromhex(
                "ba fb 03 b0 03 ee "  # COM1 line control: 8 data bits, DLAB off
                "ba f8 03"           # COM1 transmit register
            ))
            for byte in marker:
                code.extend((0xB0, byte, 0xEE))  # mov al, byte; out dx, al
            code.extend(bytes.fromhex("ba f4 00 b0 2a ee fa f4 eb fd"))
            sector = code.ljust(510, b"\0") + bytes.fromhex("55 aa")
            disk.write_bytes(sector.ljust(1024 * 1024, b"\0"))
            qemu = subprocess.run(
                [
                    self.emulator, "-L", str(Path(self.bios).parent), "-machine", "q35",
                    "-accel", self.accelerator, "-display", "none", "-monitor", "none",
                    "-serial", f"file:{serial}", "-nic", "none",
                    "-device", "isa-debug-exit,iobase=0xf4,iosize=0x4",
                    "-drive", f"file={disk},format=raw", "-boot", "c",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=30,
                text=True,
            )
            self.assertEqual(qemu.returncode, 85, qemu.stderr)
            self.assertIn(marker, serial.read_bytes())


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
