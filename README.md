# QEMU Bazel registry

This is a standalone Bazel index registry in the Bazel Central Registry (BCR)
layout. Bazel verifies and extracts the upstream QEMU 11.1.2 release and applies
its checked-in, individually pinned overlay. No materialization step is needed.

**This downstream overlay is AI-generated. It is not part of upstream QEMU and
is not supported by the QEMU project.** It builds a static Linux x86-64 system
emulator with KVM and includes a Windows x86-64 overlay for WHPX. Both
use accelerator-specific builds without TCG. The published module does not select or register a compiler.
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

## Windows x86-64

Use Bazel 9.3.2 and its required x64 Visual C++ runtime. The developer
workspaces register the Windows GNU toolchain from
`hermetic_cc_toolchain` 4.3.0, which supplies Zig 0.15.2 and MinGW headers
and import libraries. The workspaces also apply a pinned patch to enable
archive and link response files for the Windows toolchain. A consumer
using the same toolchain can copy the override and patch from [`dev/`](dev/).
From `dev/` or `dev/default/` in PowerShell, run:

```powershell
bazel build @qemu//:qemu-system-x86_64
bazel test @qemu//:whpx_smoke_test
```

On a slim Windows image, `launcher_maker.exe` can exit with `-1073741515`
when the x64 Visual C++ runtime is absent. Stage the DLLs from Bazel's
embedded JDK beside the maker in the Bazel install cache. Expose the same
DLL directory to the test processes with `--test_env`. The developer
workspaces use an empty build-action `PATH` for both profiles.

```powershell
$installBase = bazel info install_base
$runtime = Join-Path $installBase 'embedded_tools/jdk/bin'
$launcher = Join-Path $installBase 'embedded_tools/tools/launcher'
foreach ($dll in 'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll') {
    Copy-Item -LiteralPath (Join-Path $runtime $dll) -Destination $launcher
}
bazel test "--test_env=PATH=$runtime" @qemu//:whpx_smoke_test
```

The registration test runs version and help commands without launching a
guest. A guest run requires the Windows Hypervisor Platform feature
(`HypervisorPlatform`), a running hypervisor accessible to the emulator,
and `-accel whpx`. Use `-L` with the directory containing the release
firmware. Availability depends on the Windows environment. Issue #2 records
the capability and partition checks on both a process-isolated container and
a HostProcess session.

Rules can request `@qemu//toolchain:type` and access it through
`ctx.toolchains`. The module registers the Linux/KVM and Windows/WHPX
implementations by execution OS and CPU. The selected toolchain exposes
`emulator` (a `FilesToRunProvider`), `accelerator`, `runtime_files` (a
depset of firmware and emulator runfiles), `version`, and `provenance`.
The overlay configures native builds on the Bazel host. The ELF build
manifest target applies to the Linux binary.

## Configure the module

With no configuration tag, `minimal` seeds Kconfig with `CONFIG_Q35=y`
and `CONFIG_ISA_DEBUG=y` for the example guest. Run it with `-machine q35`.
This profile omits the i440FX `pc` alias, Pixman, and SLIRP, and uses `nop`
tracing.
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
The accelerator defaults to KVM on Linux and WHPX on Windows. Supply
`accelerators = ["kvm"]` or `accelerators = ["whpx"]` to require a particular
accelerator on its supported host. Configuration applies to the whole module.

The `minimal` profile resolves the same devices on Linux and Windows. In
`default`, Windows retains q35, i440FX, Pixman, SLIRP, and simple tracing.
It omits the Linux- or KVM-dependent device options for guest Hyper-V
(VMBus and test devices), Xen emulation, VFIO/IOMMUFD, ivshmem, host input,
virtio-mem, VT-d acceleration, SEV, SGX, TDX, and the OVMF device option.

## Use with `rules_qemu`

The [toolchain example](dev/rules_qemu/) adapts the source-built emulator,
`qemu-img`, and staged `pc-bios` data to `rules_qemu` 0.3.0. A single test
checks toolchain resolution and boots a bare-metal guest using the selected
accelerator. The boot test reports a skip when KVM or WHPX is unavailable.

### Run a bare-metal x86-64 Rust binary

From a Linux or Windows x86-64 host with Bazel 9.3.2 or Bazelisk, run the same target:

```sh
cd example
bazel build //:x86_64_uart_test
bazel test --test_strategy=standalone --test_output=all //:x86_64_uart_test
```

[`example/`](example/) pins Rust 1.91.1 with `rules_rust`. A platform transition
builds the `no_std` guest for `x86_64-unknown-none` with the pinned `rust-lld`.
The test runner and QEMU are native x86-64 executables. The `rules_qemu`
adapter resolves the source-built emulator, firmware and accelerator for the
execution platform. Linux uses pinned Zig/musl with KVM. Windows uses pinned
Zig/MinGW with WHPX.

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

The test is tagged `manual` and the example workflow invokes it explicitly.
It prints `SKIP` if it cannot open `/dev/kvm` on Linux or create a WHPX
partition on Windows. On Linux, the standalone test strategy exposes `/dev/kvm`
to the test. Build actions still use the restricted action environment.

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
`@qemu//:kvm_smoke_test`. These Linux measurements predate the addition of
`CONFIG_ISA_DEBUG` to `minimal`.

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
