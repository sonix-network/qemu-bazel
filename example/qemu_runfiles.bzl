"""Keep the runner and emulator native; transition only the guest ELF."""

_QEMU_SYSTEM = Label("@rules_qemu//qemu:exec_toolchain_type")

_guest_platform = transition(
    implementation = lambda _settings, _attr: {
        "//command_line_option:platforms": [str(Label("//:x86_64_baremetal"))],
    },
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)

def _runfile(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return ctx.workspace_name + "/" + file.short_path

def _qemu_runfiles_impl(ctx):
    qemu = ctx.toolchains[_QEMU_SYSTEM]
    if (qemu.system_target, qemu.machine, qemu.accel) != ("x86_64-softmmu", "q35", "kvm"):
        fail("expected the x86-64 q35/KVM system toolchain")
    (guest,) = ctx.files.guest
    files = [qemu.qemu_system, qemu.system_data_anchor, guest]
    manifest = ctx.actions.declare_file(ctx.label.name + ".txt")
    ctx.actions.write(manifest, "\n".join([_runfile(ctx, file) for file in files]) + "\n")
    return DefaultInfo(
        files = depset([manifest]),
        runfiles = ctx.runfiles(
            files = files + [manifest],
            transitive_files = qemu.system_data_files,
        ),
    )

qemu_runfiles = rule(
    implementation = _qemu_runfiles_impl,
    attrs = {
        "guest": attr.label(cfg = _guest_platform, mandatory = True),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
    toolchains = [_QEMU_SYSTEM],
)
