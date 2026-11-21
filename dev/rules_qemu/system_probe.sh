#!/bin/sh
set -eu
export LC_ALL=C

qemu=$TEST_SRCDIR/{qemu_system}
qemu_img=$TEST_SRCDIR/{qemu_img}
pc_bios=$TEST_SRCDIR/{pc_bios}

fail() {
    printf '%s\n' "$1" >&2
    exit 1
}

version=$("$qemu" --version)
case "$version" in
    'QEMU emulator version 11.1.2'*) ;;
    *) fail "Unexpected system emulator: $version" ;;
esac

accel=$("$qemu" -accel help)
case "$accel" in
    'Accelerators supported in QEMU binary:
kvm') ;;
    *) fail "Expected KVM only: $accel" ;;
esac

machines=$("$qemu" -machine help)
case "$machines" in
    *'q35 '*'(alias of pc-q35-'*) ;;
    *) fail "q35 is not registered: $machines" ;;
esac

[ -s "$pc_bios/bios-256k.bin" ] || fail "Missing BIOS in toolchain runfiles"
img_version=$("$qemu_img" --version)
case "$img_version" in
    'qemu-img version 11.1.2'*) ;;
    *) fail "Unexpected image tool: $img_version" ;;
esac
"$qemu_img" create -f qcow2 "$TEST_TMPDIR/disk.qcow2" 1M
info=$("$qemu_img" info --output=json "$TEST_TMPDIR/disk.qcow2")
case "$info" in
    *'"format": "qcow2"'*) ;;
    *) fail "Unexpected image format: $info" ;;
esac
printf '%s\n' 'Resolved source-built QEMU, qemu-img, and release BIOS; no VM started.'
