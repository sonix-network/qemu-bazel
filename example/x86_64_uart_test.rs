use runfiles::{rlocation, Runfiles};
use std::{fs, process::Command};

#[test]
fn pvh_uart_and_debug_exit() {
    let runfiles = Runfiles::create().unwrap();
    let config = rlocation!(runfiles, env!("BOOT_INPUTS")).unwrap();
    let contents = fs::read_to_string(config).unwrap();
    let entries: Vec<_> = contents
        .lines()
        .map(|name| rlocation!(runfiles, name).expect("missing boot input"))
        .collect();
    let [qemu, bios, kernel] = entries.as_slice() else {
        panic!("expected QEMU, its data directory, and the guest ELF");
    };
    for rom in ["bios-256k.bin", "pvh.bin", "kvmvapic.bin"] {
        assert!(bios.join(rom).is_file(), "missing staged firmware: {rom}");
    }
    drop(
        fs::OpenOptions::new()
            .read(true)
            .write(true)
            .open("/dev/kvm")
            .unwrap_or_else(|error| {
                panic!("this manual test requires /dev/kvm ({error}); use bazel build for a build-only check")
            }),
    );

    let output = Command::new(qemu)
        .env_clear()
        .env("LC_ALL", "C")
        .arg("-L")
        .arg(bios)
        .args([
            "-machine",
            "q35",
            "-accel",
            "kvm",
            "-cpu",
            "host",
            "-m",
            "64M",
            "-nodefaults",
            "-nic",
            "none",
            "-display",
            "none",
            "-monitor",
            "none",
            "-serial",
            "stdio",
            "-no-reboot",
            "-device",
            "isa-debug-exit,iobase=0xf4,iosize=4",
            "-kernel",
        ])
        .arg(kernel)
        .output()
        .expect("failed to execute the toolchain's QEMU");
    assert_eq!(
        output.status.code(),
        Some(85),
        "QEMU did not exit via isa-debug-exit: {}; stdout={:?}; stderr={:?}",
        output.status,
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr),
    );
    assert_eq!(output.stdout, b"hello from x86_64\n");
    println!("COM1: {}QEMU exit status: 85", String::from_utf8_lossy(&output.stdout));
}
