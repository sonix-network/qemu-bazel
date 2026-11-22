# QEMU Bazel overlay

This is a downstream Bazel build, not QEMU's upstream build system. The
upstream release archive is unchanged. The overlay is maintained in
[sonix-network/qemu-bazel](https://github.com/sonix-network/qemu-bazel).
The `qemu` module builds the x86-64 system emulator natively for Linux
(KVM, static) and Windows (WHPX), without TCG. It does not replace the
`rules_qemu` toolchain rules. Consumers supply a compatible C toolchain.

The checked-in BUILD files describe QEMU's source sets. Device selection
runs QEMU's Kconfig generator under rules_python's managed host interpreter;
other generators run in build actions. The emulator, its build information,
`@qemu//:firmware` (a `-L` directory), raw release `pc-bios` files, package
metadata, and x86-64 `qemu-img` for the `rules_qemu` adapter are public.
The directory stages SeaBIOS, the PVH and VAPIC ROMs, and release device ROMs
selected by the configured Kconfig symbols. Other build targets are internal.

GLib, PCRE2, and libslirp resolve through Bzlmod. The GLib and PCRE2 registry
revisions support the pinned Zig toolchains without private copies or
registry URLs in the build rules. The Linux presubmit builds and checks
registration and firmware in `minimal` and `default` without booting a guest.
The Windows presubmit builds the emulator for each profile on Bazel 9.x;
it does not run QEMU or require WHPX.

The first registry version is `11.1.2`. Later registry-only changes for the
same QEMU release use new versions and directories `11.1.2.bcr.1`,
`11.1.2.bcr.2`, and so on, without editing a published version.
