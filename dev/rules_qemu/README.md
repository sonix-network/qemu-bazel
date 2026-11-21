# Source-built rules_qemu toolchain example

The adapter consumes `@qemu//toolchain:type` and provides the
`rules_qemu` 0.3.0 system toolchain. The same test target uses Linux/KVM or
Windows/WHPX according to the execution platform. It checks the emulator and
`qemu-img`, then boots a small real-mode guest and checks its serial output.
The boot case reports a skip when the accelerator is unavailable.

From this directory on Linux or Windows x86-64, run:

```sh
bazel test --test_output=all //:system_probe_test
```

The adapter registers the source-built toolchain under
`@rules_qemu//qemu:exec_toolchain_type`. It uses a registered Linux musl
execution platform on Linux, and the Bazel host platform on Windows.
The firmware is staged from the pinned release as a directory File for
`system_data_anchor`, which consumers pass to QEMU with `-L`. For rules
that use `target_toolchain_type`, register an adapter under that type too.
The source-built toolchain covers x86-64 system emulation. The rules_qemu
prebuilts can still supply user-mode and other guest architectures.
