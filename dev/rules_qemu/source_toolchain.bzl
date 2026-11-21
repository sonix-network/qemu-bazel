"""Adapt the QEMU module toolchain to the rules_qemu system toolchain API."""

load("@rules_qemu//qemu:qemu_system_toolchain.bzl", "QemuSystemToolchainInfo")

_QEMU_TOOLCHAIN = Label("@qemu//toolchain:type")

def _impl(ctx):
    qemu = ctx.toolchains[_QEMU_TOOLCHAIN]
    info = QemuSystemToolchainInfo(
        accel = qemu.accelerator,
        machine = "q35",
        qemu_img = ctx.file.qemu_img,
        qemu_system = qemu.emulator.executable,
        system_data_anchor = ctx.file.system_data,
        system_data_files = depset([ctx.file.system_data], transitive = [qemu.runtime_files]),
        system_target = "x86_64-softmmu",
        target_arch = "x86_64",
    )
    return [
        info,
        platform_common.ToolchainInfo(
            accel = info.accel,
            machine = info.machine,
            qemu_img = info.qemu_img,
            qemu_system = info.qemu_system,
            qemu_system_info = info,
            system_data_anchor = info.system_data_anchor,
            system_data_files = info.system_data_files,
            system_target = info.system_target,
            target_arch = info.target_arch,
        ),
    ]

source_toolchain = rule(
    implementation = _impl,
    attrs = {
        "qemu_img": attr.label(allow_single_file = True, cfg = "exec", mandatory = True),
        "system_data": attr.label(allow_single_file = True, cfg = "exec", mandatory = True),
    },
    toolchains = [_QEMU_TOOLCHAIN],
)
