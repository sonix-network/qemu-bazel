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

On Linux x86-64 with Bazel 9.3.2 (or Bazelisk), run these commands from the
repository root. `dev/` exercises the no-tag `minimal` profile; `dev/default/`
exercises the explicitly selected `default` profile.

```sh
for workspace in dev dev/default; do
  (
    cd "$workspace" &&
      bazel build @qemu//:qemu-system-x86_64 @qemu//:qemu-system-x86_64_info &&
      bazel test @qemu//:kvm_smoke_test
  ) || exit 1
done
```

Both workspaces register Zig/musl and use a relative `file://` URL for this
registry, followed by `https://bcr.bazel.build` for dependencies. Other
consumers can declare `bazel_dep(name = "qemu", version = "11.1.2")`, add
`--registry=file:///absolute/path/to/this/checkout` followed by the BCR URL,
and supply their own Linux x86-64 C toolchain with a static libc.

The smoke test checks version, KVM, device and trace registration. It also
requires q35 and rejects i440FX in `minimal`; it requires both in `default`.
It does not need `/dev/kvm` and does not boot a guest. To run a
VM, supply `/dev/kvm` and use `-L /path/to/qemu/pc-bios` for the release's
prebuilt firmware. The module does not install QEMU, build firmware, or package
a runtime. Use `--distdir` to point Bazel at a locally downloaded archive if
needed; the [release and overlay pins](modules/qemu/11.1.2/source.json) still
apply.

## Configure the module

With no configuration tag, `minimal` seeds Kconfig with `CONFIG_Q35=y`
and enables only what it selects. Run it with `-machine q35`; the i440FX `pc`
alias is not built. It does not enable Pixman or SLIRP and uses `nop` tracing.
Choose `default` explicitly to use QEMU's own default
x86-64 device configs (including q35 and i440FX), Pixman, SLIRP, and `simple`
tracing:

```starlark
qemu = use_extension("@qemu//bazel/config:targets.bzl", "qemu_targets")
qemu.configure(profile = "default")
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

Both developer workspaces built with Bazel 9.3.2 and Zig/musl, and both passed
`@qemu//:kvm_smoke_test`.

| Profile | Resolved device symbols | Stripped static ELF |
| --- | ---: | ---: |
| `minimal` | 57 | 6,670,104 bytes |
| `default` | 227 | 29,569,928 bytes |

The registration smoke test is not a KVM guest boot or a runtime-compatibility
test. The musl build uses QEMU's `sigaltstack` coroutine backend rather than
`ucontext`; it also disables the AVX512BW XBZRLE optimization for Zig/Clang.

Run `python3 -m unittest discover -s dev/tools` from the registry root to check
the complete overlay pin map and the manifest verifier. Update the affected
integrities in `source.json` whenever overlay files change. The BCR presubmit
is configured to test both profiles with the developer workspace toolchains.

Optional helpers in [`dev/tools/`](dev/tools/):

- `compare.py` compares Bazel `aquery --output=jsonproto
  'mnemonic("CppCompile", deps(@qemu//:qemu-system-x86_64))'` output and Meson
  `ninja -t commands qemu-system-x86_64` output. Pass
  `--bazel-source-prefix external/qemu+/` for the registry build.
- `compare_runtime.py BAZEL_BINARY MESON_BINARY` compares registration output,
  ELF hashes and shared dependencies without starting a guest.
- `cache_receipt.py` summarizes Bazel `--execution_log_json_file` logs by
  action mnemonic and cache outcome.
