# QEMU Bazel registry

This is a standalone Bazel index registry in the Bazel Central Registry (BCR)
layout. Bazel verifies and extracts the upstream QEMU 11.1.2 release and applies
its checked-in, individually pinned overlay. No materialization step is needed.

The first registry version for this release is `11.1.2`, in
`modules/qemu/11.1.2/`. Published versions are immutable. For build-only fixes
against the same upstream tarball, add a new registry version and directory
using `11.1.2.bcr.1`, `11.1.2.bcr.2`, and so on. Keep the directory name,
`module(version = ...)`, and the version listed in `metadata.json` in sync.
Do not use `11.1.2-r0`: Bazel sorts it before `11.1.2`.

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

## Use with `rules_qemu`

The [toolchain example](dev/rules_qemu/) registers the source-built emulator,
`qemu-img`, and staged `pc-bios` data with `rules_qemu` 0.3.0. It tests toolchain
resolution without `/dev/kvm`. The QEMU module itself does not register
`rules_qemu` toolchains or depend on that module.

### Run a bare-metal x86-64 Rust binary

From a Linux x86-64 host with Bazel 9.3.2 or Bazelisk:

```sh
cd example
bazel build //:x86_64_uart_test  # Build-only check; no /dev/kvm needed.
bazel test --test_strategy=local //:x86_64_uart_test  # Requires /dev/kvm.
```

[`example/`](example/) pins Rust 1.91.1 with `rules_rust`. A platform transition
builds the `no_std` guest for `x86_64-unknown-none` with the pinned `rust-lld`.
The test runner and source-built QEMU are native Linux x86-64 executables;
QEMU uses pinned Zig/musl. The runner resolves the emulator and its data
through a `rules_qemu` system toolchain; it does not use an installed QEMU.

Both profiles have q35 and `isa-serial` (COM1). The example uses `default`
because `minimal` omits `isa-debug-exit`. QEMU loads the guest ELF via `-kernel`.
Its PVH entry note points to a small 32-bit trampoline that enters long mode
before calling Rust. The test requires exactly `hello from x86_64` on COM1
and QEMU exit status 85 from `isa-debug-exit`.

PVH direct boot still uses firmware. The example stages `bios-256k.bin`
(SeaBIOS) and `pvh.bin` (the PVH option ROM) from the SHA-256-pinned QEMU
11.1.2 release and passes their runfiles directory via `-L`. It also stages
`kvmvapic.bin`: QEMU requests this optional ROM and warns if it is missing,
although the PVH guest does not need it. The example uses no host firmware
installation, disk image, or network.

The runtime test is tagged `manual` and `requires-kvm`: wildcard test runs
and the build-only example presubmit do not boot it. Run it explicitly on
an x86-64 host where the current user can open `/dev/kvm`. The local test
strategy exposes the device to the test; the build actions remain sandboxed.
There is no TCG fallback.

## Build provenance

`@qemu//:qemu-system-x86_64_info` exports `QemuBuildInfo` (from
`@qemu//bazel:info.bzl`), with `elf` and `configuration` output groups. Its
schema-1 `qemu-system-x86_64_info.manifest.json` records the measured ELF and
configuration hashes, resolved Kconfig symbols, toolchain metadata, and source
provenance. The manifest action rejects an ELF with `PT_INTERP` or `DT_NEEDED`.
Optional patch and lock fields are empty or null for this unpatched registry
release.

## Package metadata and licensing

The top-level QEMU Bazel package defaults to `@qemu//:package_metadata`
([`package_metadata`](https://github.com/bazel-contrib/supply-chain) 0.0.15).
It supplies `pkg:generic/qemu@11.1.2` and `GPL-2.0-only` with the upstream
`COPYING` text for SBOM and license collectors. This is the license of the
emulator as a whole, as described in the release's `LICENSE`, not an inventory
of every source file. For example, the compiled sources `util/cutils.c` and
`util/oslib-posix.c` carry their own MIT notices.

The pinned GLib build overlay also uses `package_metadata`, retaining its
separate `LGPL-2.1-or-later` declaration. This replaces the QEMU module's direct
`rules_license` dependency; other dependencies may still use `rules_license`.

This repository's own files (the Bazel overlay, registry metadata, developer
tools and example) are licensed under the [Apache License 2.0](LICENSE). QEMU
itself, which the overlay builds, keeps its upstream licenses described above.

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
