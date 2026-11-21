"""Check that the registry pins exactly the files it overlays."""

import base64
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "qemu"
RELEASE = MODULE / "11.1.2"


def integrity(digest):
    return "sha256-" + base64.b64encode(digest).decode("ascii")


class RegistryTest(unittest.TestCase):
    def test_source_pin_matches_provenance(self):
        metadata = json.loads((MODULE / "metadata.json").read_text())
        source = json.loads((RELEASE / "source.json").read_text())
        provenance = json.loads((RELEASE / "overlay/bazel/source_provenance.json").read_text())
        version = RELEASE.name
        self.assertIn(version, metadata["versions"])
        self.assertEqual(provenance["qemu_version"], version)
        self.assertEqual(source["url"], f"https://download.qemu.org/qemu-{version}.tar.xz")
        self.assertEqual(source["strip_prefix"], f"qemu-{version}")
        self.assertEqual(source["integrity"], integrity(bytes.fromhex(provenance["source_sha256"])))

    def test_overlay_pins_match_disk(self):
        source = json.loads((RELEASE / "source.json").read_text())
        overlay = RELEASE / "overlay"
        files = sorted(p for p in overlay.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        actual = {p.relative_to(overlay).as_posix(): integrity(hashlib.sha256(p.read_bytes()).digest())
                  for p in files}
        self.assertEqual(actual, source["overlay"])

    def test_default_workspace_only_adds_the_profile_tag(self):
        dev = ROOT / "dev"
        for name in ("BUILD.bazel", ".bazelversion", "zig-windows-params.patch"):
            self.assertEqual((dev / "default" / name).read_bytes(), (dev / name).read_bytes())
        self.assertEqual((dev / "default/MODULE.bazel").read_text(),
                         (dev / "MODULE.bazel").read_text()
                         + '\nqemu = use_extension("@qemu//bazel/config:targets.bzl", "qemu_targets")\n'
                         'qemu.configure(profile = "default")\n')

    def test_presubmit_workspaces_use_the_same_toolchains_and_profiles(self):
        for subdir, override in [(".", "../.."), ("default", "../../..")]:
            with self.subTest(workspace=subdir):
                presubmit = RELEASE / "overlay/bazel/presubmit" / subdir
                dev = ROOT / "dev" / subdir
                self.assertEqual((presubmit / "BUILD.bazel").read_bytes(),
                                 (dev / "BUILD.bazel").read_bytes())
                self.assertEqual((presubmit / "zig-windows-params.patch").read_bytes(),
                                 (dev / "zig-windows-params.patch").read_bytes())
                self.assertEqual((presubmit / "MODULE.bazel").read_text(),
                                 (dev / "MODULE.bazel").read_text()
                                 + f'\nlocal_path_override(module_name = "qemu", path = "{override}")\n')


if __name__ == "__main__":
    unittest.main()
