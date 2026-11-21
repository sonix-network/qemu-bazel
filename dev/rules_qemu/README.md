# Source-built rules_qemu toolchain example

The adapter consumes `@qemu//toolchain:type` and provides the
`rules_qemu` 0.3.0 system toolchain. The same test target uses Linux/KVM or
Windows/WHPX according to the execution platform. It checks the emulator and
`qemu-img`, then boots a small real-mode guest and checks its serial output.
The boot case reports a skip when the accelerator is unavailable.

On Linux x86-64, run `bazel test --test_output=all //:system_probe_test`
from this directory. On Windows x86-64, supply the absolute registry URL as
in the root README:

```powershell
bazel --ignore_all_rc_files test --registry=file:///C:/src/qemu-bazel --registry=https://bcr.bazel.build --repo_env=BAZEL_DO_NOT_DETECT_CPP_TOOLCHAIN=1 --test_output=all //:system_probe_test
```
