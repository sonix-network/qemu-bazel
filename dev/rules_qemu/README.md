# Use a source-built emulator with `rules_qemu`

```sh
cd dev/rules_qemu
bazel test //:system_probe_test
```

This uses the local registry and `rules_qemu` 0.3.0 from BCR. The test resolves
`@rules_qemu//qemu:exec_toolchain_type`, checks the selected QEMU version, q35
and KVM registrations, checks the release BIOS in the toolchain's runfiles,
and creates and inspects a small qcow2 file. It does not start a VM and does not
need `/dev/kvm`.

## Registration

By default, the [`rules_qemu` extension][extension] uses SHA-256-pinned Linux
prebuilts from `hermeticbuild/qemu-prebuilt`: QEMU 11.0.0 (artifact release
11.0.0.1), separate user and system binaries, `qemu-img`, and `share/qemu` data.
Its `system_toolchain` tag selects a guest architecture via consumer-owned
`target_settings`; it does not take a binary or data override. Its generated
registrations cover Linux x86-64 and AArch64 execution hosts. `qemu_binary`
uses the distinct user-mode `toolchain_type`, not a system toolchain.

To replace the system binary, use the public [`qemu_system_toolchain` rule][api]
directly and register your own `toolchain()` as in [BUILD.bazel](BUILD.bazel).
There is no filename rewrite: the rule accepts a single-file executable label
and this registry already exports `@qemu//:qemu-system-x86_64`. The other
required inputs here are `@qemu//:qemu-img` and a tree artifact staged from
`@qemu//:pc-bios-files`. Use a directory File as `system_data_anchor`, not a
single firmware file: consumers use the anchor as the directory passed to
`-L`. The filegroup exposes files from the pinned release; it neither builds
firmware nor reproduces every file Meson would install under `share/qemu`.

Both executable inputs use the execution configuration. This example registers
an x86-64 Linux **musl** execution platform so Bazel builds them with Zig/musl.
The toolchain advertises `x86_64-softmmu`, machine `q35`, and accelerator `kvm`
(an explicit override of the API's `tcg` default). For consumers of
`target_toolchain_type`, register the same implementation under that type too.
If you also register the prebuilts, use disjoint `target_settings` or explicit
registration priority to select the intended system toolchain.

## Limits

- The registry builds only a Linux x86-64 system emulator. It cannot replace
  `rules_qemu`'s user-mode or other architecture prebuilts.
- Both registry profiles are KVM-only. A VM requires `/dev/kvm`; `-S` does not
  avoid accelerator initialization. The upstream QMP and boot smokes start a
  VM, and the x86 boot smoke also needs virtio-blk and `isa-debug-exit`, which
  the q35-only `minimal` device set does not provide. This example checks
  wiring and registration, not boot or firmware compatibility.
- The example uses the registry's no-tag `minimal` profile. A consumer can
  select `qemu_targets.configure(profile = "default")` for the broader device
  set without changing the emulator label or toolchain type. That does not add
  TCG.
- There is no Bzlmod naming collision: `qemu` is the source module and
  `rules_qemu` owns the toolchain types. The `qemu_targets` and `qemu`
  extensions have different defining labels and purposes. The source module
  does not depend on or register `rules_qemu`.

[extension]: https://github.com/hermeticbuild/rules_qemu/blob/v0.3.0/qemu/extension/qemu.bzl
[api]: https://github.com/hermeticbuild/rules_qemu/blob/v0.3.0/qemu/qemu_system_toolchain.bzl
