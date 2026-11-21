"""Expose the resolved rules_qemu toolchain to the native-host test."""

_SYSTEM_TOOLCHAIN = Label("@rules_qemu//qemu:exec_toolchain_type")

def _runfile(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return ctx.workspace_name + "/" + file.short_path

def _system_probe_data_impl(ctx):
    qemu = ctx.toolchains[_SYSTEM_TOOLCHAIN]
    if (qemu.system_target, qemu.target_arch, qemu.machine) != ("x86_64-softmmu", "x86_64", "q35"):
        fail("expected the source-built x86_64 q35 system toolchain")
    manifest = ctx.actions.declare_file(ctx.label.name + ".json")
    ctx.actions.write(manifest, json.encode({
        "accelerator": qemu.accel,
        "emulator": _runfile(ctx, qemu.qemu_system),
        "firmware": _runfile(ctx, qemu.system_data_anchor),
        "image_tool": _runfile(ctx, qemu.qemu_img),
    }))
    return DefaultInfo(
        files = depset([manifest]),
        runfiles = ctx.runfiles(
            files = [manifest, qemu.qemu_system, qemu.qemu_img, qemu.system_data_anchor],
            transitive_files = qemu.system_data_files,
        ),
    )

system_probe_data = rule(
    implementation = _system_probe_data_impl,
    toolchains = [_SYSTEM_TOOLCHAIN],
)
