# Reproduce the two build-only Windows BCR tasks without the local BCR
# py_binary launcher or Buildkite's host-specific C:/b output root.
param(
    [Parameter(Mandatory=$true)][string]$Work,
    [string]$Registry = (Join-Path $PSScriptRoot '../..'),
    [string]$BazelVersion = '9.3.2'
)
$ErrorActionPreference = 'Stop'
$env:USE_BAZEL_VERSION = $BazelVersion
$Registry = (Resolve-Path -LiteralPath $Registry).Path
$registryUri = [Uri]::new($Registry).AbsoluteUri
$version = '11.1.2'
if (-not (Test-Path -LiteralPath (Join-Path $Registry "modules/qemu/$version/source.json"))) {
    throw "No qemu@$version entry in $Registry"
}
New-Item -Force -ItemType Directory -Path $Work | Out-Null
$Work = (Resolve-Path -LiteralPath $Work).Path
$seed = Join-Path $Work 'seed'
$module = Join-Path $Work 'module_src'
if ((Test-Path -LiteralPath $seed) -or (Test-Path -LiteralPath $module)) {
    throw "Use a fresh work directory: $Work"
}
$root = Join-Path $Work 'out'
$cache = Join-Path $Work 'repo-cache'
$rc = @(
    "common --registry=$registryUri",
    'common --registry=https://bcr.bazel.build',
    'common --lockfile_mode=off'
)
New-Item -ItemType Directory -Path $seed | Out-Null
Set-Content -Encoding ascii -LiteralPath (Join-Path $seed 'MODULE.bazel') `
    -Value "bazel_dep(name = `"qemu`", version = `"$version`")"
Set-Content -Encoding ascii -LiteralPath (Join-Path $seed '.bazelrc') -Value $rc
Push-Location $seed
try {
    bazelisk --batch "--output_user_root=$root" vendor "--repository_cache=$cache" `
        '--vendor_dir=vendor_src' '--repo=@qemu'
    if ($LASTEXITCODE -ne 0) { throw "Bazel vendoring failed with exit $LASTEXITCODE" }
} finally { Pop-Location }
Move-Item -LiteralPath (Join-Path $seed 'vendor_src/qemu+') -Destination $module
$presubmit = Join-Path $module 'bazel/presubmit'
Add-Content -Encoding ascii -LiteralPath (Join-Path $presubmit '.bazelrc') -Value (@('') + $rc)
$flags = @(
    '--repo_env=BAZEL_DO_NOT_DETECT_CPP_TOOLCHAIN=1',
    '--incompatible_strict_action_env',
    '--action_env=PATH=',
    '--host_action_env=PATH='
)
$failed = $false
foreach ($profile in 'minimal', 'default') {
    $cwd = if ($profile -eq 'minimal') { $presubmit } else { Join-Path $presubmit 'default' }
    Push-Location $cwd
    try {
        bazelisk --batch "--output_user_root=$root" build "--repository_cache=$cache" `
            --jobs=2 --local_resources=cpu=2 @flags '@qemu//:qemu-system-x86_64'
        $status = $LASTEXITCODE
        Write-Host "Windows $profile Bazel $BazelVersion build exit=$status"
        if ($status -ne 0) { $failed = $true }
    } finally { Pop-Location }
}
if ($failed) { exit 1 }
