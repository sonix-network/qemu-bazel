"""Unit tests for the ELF gate used by the Bazel manifest action."""

import hashlib
import json
from pathlib import Path
import runpy
import struct
import tempfile
import unittest

MANIFEST = runpy.run_path(str(
    Path(__file__).resolve().parents[2]
    / "modules/qemu/11.1.2/overlay/bazel/build_manifest.py"
))
main = MANIFEST["main"]
static_elf = MANIFEST["static_elf"]
verifier_inputs = MANIFEST["verifier_inputs"]


PINS = {
    "qemu_version": "11.1.2",
    "source_sha256": "a" * 64,
    "patch_series_sha256": "b" * 64,
    "patches": [{"name": name, "sha256": "c" * 64} for name in ["second", "first"]],
    "build_inputs_lock_sha256": "d" * 64,
    "runtime_tools_lock_sha256": "e" * 64,
}
CONFIG = {
    "configure_args": ["--enable-kvm", "--disable-modules"],
    "profile": "consumer",
    "config_host": {"CONFIG_MODULES": False},
}


def sample(segment, tag=0):
    data = bytearray(64 + 56 + 32)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", data, 16, 3, 62)
    struct.pack_into("<Q", data, 32, 64)
    struct.pack_into("<HH", data, 54, 56, 1)
    struct.pack_into("<IIQQQQQQ", data, 64, segment, 0, 120, 0, 0, 32, 32, 0)
    struct.pack_into("<qQ", data, 120, tag, 0)
    return data


class ManifestTest(unittest.TestCase):
    def test_accepts_static_elf_and_static_pie(self):
        static_elf(sample(1))  # PT_LOAD
        static_elf(sample(2, 21))  # PT_DYNAMIC with DT_DEBUG, not DT_NEEDED

    def test_rejects_runtime_loader_and_shared_libraries(self):
        with self.assertRaisesRegex(ValueError, "PT_INTERP"):
            static_elf(sample(3))
        with self.assertRaisesRegex(ValueError, "DT_NEEDED"):
            static_elf(sample(2, 1))

    def test_manifest_measures_elf_and_preserves_patch_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            elf, config, out = (Path(tmp) / name for name in ["elf", "config.json", "manifest.json"])
            data = sample(1)
            elf.write_bytes(data)
            config.write_text(json.dumps(CONFIG))
            main([str(elf), str(config), str(out), json.dumps({**PINS, "schema": 99}),
                  json.dumps({"compiler": "clang", "libc": "musl"})])
            receipt = json.loads(out.read_text())
            expected = {
                "schema": 1,
                **PINS,
                "configure_args": CONFIG["configure_args"],
                "modules": False,
                "elf_size": len(data),
                "elf_sha256": hashlib.sha256(data).hexdigest(),
                "dt_needed": [],
            }
            self.assertEqual({key: receipt[key] for key in expected}, expected)
            self.assertIs(receipt["modules"], False)
            self.assertEqual(receipt["runtime"], {"linkage": "static", "interpreter": None, "libc": "musl"})
            self.assertEqual(receipt["configuration"], CONFIG)

    def test_verifier_input_shape_and_modules(self):
        with self.assertRaisesRegex(ValueError, "configure_args"):
            verifier_inputs(PINS, {**CONFIG, "configure_args": ["--enable-kvm", False]})
        with self.assertRaisesRegex(ValueError, "disable loadable modules"):
            verifier_inputs(PINS, {**CONFIG, "config_host": {"CONFIG_MODULES": True}})


if __name__ == "__main__":
    unittest.main()
