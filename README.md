# QEMU Bazel registry

This is a standalone Bazel index registry in the Bazel Central Registry (BCR)
layout. Bazel verifies and extracts the upstream QEMU 11.1.2 release and applies
its checked-in, individually pinned overlay. No materialization step is needed.

**This downstream overlay is AI-generated. It is not part of upstream QEMU and
is not supported by the QEMU project.** It builds a static Linux x86-64 system
emulator with KVM and without TCG; it is not a general replacement for QEMU's
Meson build. The published module does not select or register a compiler.
Build generators use pinned Python 3.12.

## Build and test

On Linux x86-64 with Bazel 9.3.2 (or Bazelisk):

```sh
cd dev
bazel build @qemu//:qemu-system-x86_64 @qemu//:qemu-system-x86_64_info
bazel test @qemu//:kvm_smoke_test
```

The example consumer registers Zig/musl and uses `file://%workspace%/..` for
this registry, followed by `https://bcr.bazel.build` for dependencies. Other
consumers can declare `bazel_dep(name = "qemu", version = "11.1.2")`, add
`--registry=file:///absolute/path/to/this/checkout` followed by the BCR URL,
and supply their own Linux x86-64 C toolchain with a static libc.

The smoke test checks version, accelerator, machine, device, and trace
registration. It does not need `/dev/kvm` and does not boot a guest. To run a
VM, supply `/dev/kvm` and use `-L /path/to/qemu/pc-bios` for the release's
prebuilt firmware. The module does not install QEMU, build firmware, or package
a runtime. Use `--distdir` to point Bazel at a locally downloaded archive if
needed; the [release and overlay pins](modules/qemu/11.1.2/source.json) still
apply.

## Configure the module

The default `minimal` profile enables the i440fx machine and required devices,
without Pixman or SLIRP and with `nop` tracing. To use the broader device set,
Pixman, SLIRP, and `simple` tracing, put this in the root `MODULE.bazel`:

```starlark
qemu = use_extension("@qemu//bazel/config:targets.bzl", "qemu_targets")
qemu.configure(profile = "consumer")
```

The root module can also supply its own `.mak` file as `devices`, choose
`device_mode = "allnoconfig"` or `"defconfig"`, and select any subset of
`["pixman", "slirp"]` as `features`. GLib and zlib are required. The
`trace_backends` choices are `simple`, `log`, and `nop` (`nop` must stand alone).
Only `accelerators = ["kvm"]` is supported. Configuration applies to the whole
module, not to individual executables.

## Build provenance

`@qemu//:qemu-system-x86_64_info` exports `QemuBuildInfo` (from
`@qemu//bazel:info.bzl`), with `elf` and `configuration` output groups. Its
schema-1 `qemu-system-x86_64_info.manifest.json` records the measured ELF and
configuration hashes, resolved Kconfig symbols, toolchain metadata, and source
provenance. The manifest action rejects an ELF with `PT_INTERP` or `DT_NEEDED`.
Optional patch and lock fields are empty or null for this unpatched registry
release.

## Validation and developer tools

The default profile built with Bazel 9.3.2 and Zig/musl, and the registration
smoke test passed. The registry and pre-reorganization builds produced
byte-identical outputs in separate Bazel output bases with a shared disk cache:

| Output | SHA-256 |
| --- | --- |
| Static ELF | `d17d1f2b6fa7280764b317a8ae0b7a07ad854a0f52a94a26783c60aec062caec` |
| Provenance manifest | `8425470a3562aa129792e9517e7e5a8e0b0fb52f4c83e7b71655513ebf17092b` |

The registration smoke test is not a KVM guest boot or a runtime-compatibility
test. The musl build uses QEMU's `sigaltstack` coroutine backend rather than
`ucontext`; it also disables the AVX512BW XBZRLE optimization for Zig/Clang.

Run `python3 -m unittest discover -s dev/tools` from the registry root to check
the complete overlay pin map and the manifest verifier. Update the affected
integrities in `source.json` whenever overlay files change. The BCR presubmit
consumer under `overlay/bazel/presubmit/` uses the same toolchains as `dev/`.

Optional helpers in [`dev/tools/`](dev/tools/):

- `compare.py` compares Bazel `aquery --output=jsonproto
  'mnemonic("CppCompile", deps(@qemu//:qemu-system-x86_64))'` output and Meson
  `ninja -t commands qemu-system-x86_64` output. Pass
  `--bazel-source-prefix external/qemu+/` for the registry build.
- `compare_runtime.py BAZEL_BINARY MESON_BINARY` compares registration output,
  ELF hashes and shared dependencies without starting a guest.
- `cache_receipt.py` summarizes Bazel `--execution_log_json_file` logs by
  action mnemonic and cache outcome.
