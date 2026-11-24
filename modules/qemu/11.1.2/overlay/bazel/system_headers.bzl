"""Re-export a cc_library dependency with its include directories as system includes.

Third-party headers included via -I inherit QEMU's strict warning flags such as
-Wundef. Promoting their include paths to system_includes passes them with
-isystem so compiler diagnostics remain focused on QEMU sources.
"""

load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc/common:cc_info.bzl", "CcInfo")

def _system_headers_impl(ctx):
    dep_cc = ctx.attr.dep[CcInfo]
    cc = dep_cc.compilation_context
    comp = cc_common.create_compilation_context(
        headers = cc.headers,
        system_includes = depset(transitive = [cc.system_includes, cc.includes]),
        quote_includes = cc.quote_includes,
        framework_includes = cc.framework_includes,
        defines = cc.defines,
        local_defines = cc.local_defines,
    )
    return [
        DefaultInfo(files = ctx.attr.dep[DefaultInfo].files),
        CcInfo(
            compilation_context = comp,
            linking_context = dep_cc.linking_context,
        ),
    ]

system_headers = rule(
    implementation = _system_headers_impl,
    attrs = {
        "dep": attr.label(mandatory = True, providers = [CcInfo]),
    },
)
