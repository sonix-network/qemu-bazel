# Use QEMU's pinned Zig MinGW toolchain and the unmodified BCR dependencies.
param([string]$Work)
$ErrorActionPreference = 'Stop'
# Nonzero exits for the explicitly incompatible targets are expected below.
$PSNativeCommandUseErrorActionPreference = $false
$env:USE_BAZEL_VERSION = '9.3.2'
$startup = @()
if ($Work) {
    New-Item -Force -ItemType Directory -Path $Work | Out-Null
    $root = (Resolve-Path -LiteralPath $Work).Path
    $startup += "--output_user_root=$root"
}
$flags = @('--jobs=2', '--local_resources=cpu=2', '--verbose_failures')

Push-Location (Join-Path $PSScriptRoot '../../example')
try {
    bazelisk @startup build @flags '@glib//glib' '@glib//gmodule' '@glib//glib/tests:unicode' '@glib//glib/tests:win32'
    $status = $LASTEXITCODE
    Write-Host "Windows MinGW GLib/GModule/test binaries build exit=$status"
    if ($status -ne 0) { exit $status }

    foreach ($target in '@glib//gobject', '@glib//gio') {
        $output = bazelisk @startup build @flags $target 2>&1 | Out-String
        $status = $LASTEXITCODE
        if ($status -eq 0 -or $output -notmatch 'is incompatible and cannot be built') {
            Write-Host $output
            throw "Expected a platform incompatibility for $target; got exit $status"
        }
        Write-Host "${target}: rejected as incompatible with Windows MinGW (exit=$status)"
    }
    Write-Host 'WINDOWS_GLIB_MINGW_SCOPE_PASSED'
} finally { Pop-Location }
