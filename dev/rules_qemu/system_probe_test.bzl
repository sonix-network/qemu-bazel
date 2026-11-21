"""Check the system toolchain's runfiles without creating a VM."""

_SYSTEM_TOOLCHAIN = Label("@rules_qemu//qemu:exec_toolchain_type")

def _runfile(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return ctx.workspace_name + "/" + file.short_path

def _system_probe_test_impl(ctx):
    qemu = ctx.toolchains[_SYSTEM_TOOLCHAIN]
    if (qemu.system_target, qemu.target_arch, qemu.machine, qemu.accel) != (
        "x86_64-softmmu",
        "x86_64",
        "q35",
        "kvm",
    ):
        fail("expected the source-built x86_64 q35/KVM system toolchain")

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.expand_template(
        template = ctx.file._script,
        output = script,
        substitutions = {
            "{qemu_system}": _runfile(ctx, qemu.qemu_system),
            "{qemu_img}": _runfile(ctx, qemu.qemu_img),
            "{pc_bios}": _runfile(ctx, qemu.system_data_anchor),
        },
        is_executable = True,
    )
    return DefaultInfo(
        executable = script,
        runfiles = ctx.runfiles(
            files = [qemu.qemu_system, qemu.qemu_img, qemu.system_data_anchor],
            transitive_files = qemu.system_data_files,
        ),
    )

system_probe_test = rule(
    implementation = _system_probe_test_impl,
    attrs = {"_script": attr.label(default = "//:system_probe.sh", allow_single_file = True)},
    test = True,
    toolchains = [_SYSTEM_TOOLCHAIN],
)
