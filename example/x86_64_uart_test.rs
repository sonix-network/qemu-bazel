use runfiles::{rlocation, Runfiles};
use std::{env, fs, process::Command};

#[cfg(target_os = "linux")]
fn accelerator_available(accelerator: &str) -> bool {
    assert_eq!(accelerator, "kvm");
    fs::OpenOptions::new().read(true).write(true).open("/dev/kvm").is_ok()
}

#[cfg(target_os = "windows")]
fn accelerator_available(accelerator: &str) -> bool {
    use std::ffi::{c_char, c_void};
    use std::ptr::null_mut;

    #[link(name = "kernel32")]
    extern "system" {
        fn LoadLibraryExW(name: *const u16, file: *mut c_void, flags: u32) -> *mut c_void;
        fn GetProcAddress(module: *mut c_void, name: *const c_char) -> *mut c_void;
        fn FreeLibrary(module: *mut c_void) -> i32;
    }

    assert_eq!(accelerator, "whpx");
    let name: Vec<u16> = "WinHvPlatform.dll\0".encode_utf16().collect();
    // Use the system DLL and resolve it at runtime so a host without WHPX can skip.
    unsafe {
        let module = LoadLibraryExW(name.as_ptr(), null_mut(), 0x800); // LOAD_LIBRARY_SEARCH_SYSTEM32
        if module.is_null() {
            return false;
        }
        let capability = GetProcAddress(module, c"WHvGetCapability".as_ptr());
        let create = GetProcAddress(module, c"WHvCreatePartition".as_ptr());
        let delete = GetProcAddress(module, c"WHvDeletePartition".as_ptr());
        let available = if capability.is_null() || create.is_null() || delete.is_null() {
            false
        } else {
            let capability: extern "system" fn(u32, *mut u32, u32, *mut u32) -> i32 =
                std::mem::transmute(capability);
            let create: extern "system" fn(*mut *mut c_void) -> i32 = std::mem::transmute(create);
            let delete: extern "system" fn(*mut c_void) -> i32 = std::mem::transmute(delete);
            let mut present = 0;
            let mut partition = null_mut();
            if capability(0, &mut present, 4, null_mut()) == 0 && present != 0
                && create(&mut partition) == 0
            {
                assert_eq!(delete(partition), 0);
                true
            } else {
                false
            }
        };
        FreeLibrary(module);
        available
    }
}

#[test]
fn pvh_uart_and_debug_exit() {
    let runfiles = Runfiles::create().unwrap();
    let config = rlocation!(runfiles, env!("BOOT_INPUTS")).unwrap();
    let contents = fs::read_to_string(config).unwrap();
    let entries: Vec<_> = contents.lines().collect();
    let [accelerator, qemu, firmware, kernel] = entries.as_slice() else {
        panic!("expected the accelerator, QEMU, its data directory, and the guest ELF");
    };
    let qemu = rlocation!(runfiles, qemu).expect("missing QEMU");
    let bios = rlocation!(runfiles, firmware).expect("missing firmware directory");
    let kernel = rlocation!(runfiles, kernel).expect("missing guest ELF");
    for rom in ["bios-256k.bin", "pvh.bin", "kvmvapic.bin"] {
        assert!(bios.join(rom).is_file(), "missing staged firmware: {rom}");
    }
    if !accelerator_available(accelerator) {
        println!("SKIP: {} is unavailable on this host", accelerator.to_uppercase());
        return;
    }
    let serial = std::path::PathBuf::from(env::var_os("TEST_TMPDIR").unwrap()).join("com1.log");
    let mut serial_arg = std::ffi::OsString::from("file:");
    serial_arg.push(&serial);

    let output = Command::new(qemu)
        .env_clear()
        .env("LC_ALL", "C")
        .arg("-L")
        .arg(&bios)
        .args([
            "-machine",
            "q35",
            "-accel",
            accelerator,
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
        ])
        .arg(serial_arg)
        .args([
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
    let serial = fs::read(serial).expect("missing QEMU COM1 capture");
    assert_eq!(serial, b"hello from x86_64\n");
    println!("{} COM1: {}QEMU exit status: 85", accelerator, String::from_utf8_lossy(&serial));
}
