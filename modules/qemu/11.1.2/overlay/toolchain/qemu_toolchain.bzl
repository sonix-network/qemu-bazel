"""Execution-platform QEMU toolchain."""

load("@qemu_targets//:provenance.bzl", "SOURCE_PROVENANCE")
load("@qemu_targets//:version.bzl", "QEMU_VERSION")

def _impl(ctx):
    emulator = ctx.attr.emulator[DefaultInfo]
    return [platform_common.ToolchainInfo(
        accelerator = ctx.attr.accelerator,
        emulator = emulator.files_to_run,
        runtime_files = depset(ctx.files.runtime_files, transitive = [emulator.default_runfiles.files]),
        version = QEMU_VERSION,
        provenance = SOURCE_PROVENANCE,
    )]

qemu_toolchain = rule(
    implementation = _impl,
    attrs = {
        "accelerator": attr.string(mandatory = True, values = ["kvm", "whpx"]),
        "emulator": attr.label(cfg = "exec", executable = True, mandatory = True),
        "runtime_files": attr.label_list(allow_files = True),
    },
)
