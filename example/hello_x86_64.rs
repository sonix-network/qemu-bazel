#![no_std]
#![no_main]

use core::{
    arch::{asm, global_asm},
    panic::PanicInfo,
};

// QEMU's PVH loader enters protected mode with flat 32-bit segments.
// Enable PAE and long mode, identity-map the first 2 MiB, then enter Rust.
global_asm!(
    r#"
    .section .note.Xen,"a",@note
    .balign 4
    .long 4, 8, 18             # XEN_ELFNOTE_PHYS32_ENTRY (ELF64 descriptor)
    .asciz "Xen"
    .quad pvh_entry

    .section .text.boot,"ax",@progbits
    .code32
    .global pvh_entry
pvh_entry:
    cli
    cld
    lgdt [gdt_pointer]
    mov eax, cr4
    or eax, 1 << 5              # PAE
    mov cr4, eax
    mov eax, offset pml4
    mov cr3, eax
    mov ecx, 0xc0000080        # EFER
    rdmsr
    or eax, 1 << 8             # LME
    wrmsr
    mov eax, cr0
    or eax, 1 << 31            # PG
    mov cr0, eax
    .byte 0xea                 # far jump, ptr16:32 (offset, selector)
    .long long_mode
    .word 0x08

    .code64
long_mode:
    mov ax, 0x10
    mov ss, ax
    mov ds, ax
    mov es, ax
    lea rsp, [rip + __stack_top]
    xor ebp, ebp
    call rust_main
    ud2

    .balign 8
gdt:
    .quad 0
    .quad 0x00af9a000000ffff    # 64-bit code
    .quad 0x00cf92000000ffff    # data
gdt_pointer:
    .word gdt_pointer - gdt - 1
    .long gdt

    .section .rodata.boot,"a",@progbits
    .balign 4096
pml4:
    .quad pdpt + 3
    .zero 4088
pdpt:
    .quad pd + 3
    .zero 4088
pd:
    .quad 0x83                 # present, writable, 2 MiB page at address zero
    .zero 4088
"#,
);

const COM1: u16 = 0x3f8;

fn outb(port: u16, value: u8) {
    unsafe { asm!("out dx, al", in("dx") port, in("al") value, options(nomem, nostack, preserves_flags)) }
}

fn inb(port: u16) -> u8 {
    let value: u8;
    unsafe { asm!("in al, dx", in("dx") port, lateout("al") value, options(nomem, nostack, preserves_flags)) }
    value
}

#[no_mangle]
extern "C" fn rust_main() -> ! {
    outb(COM1 + 1, 0); // Disable UART interrupts.
    outb(COM1 + 3, 0x80); // Expose divisor latch.
    outb(COM1, 1); // Divisor 1 (115200 baud).
    outb(COM1 + 1, 0);
    outb(COM1 + 3, 3); // 8N1.
    outb(COM1 + 2, 7); // Enable and clear FIFOs.
    outb(COM1 + 4, 3); // DTR, RTS.

    for &byte in b"hello from x86_64\n" {
        while inb(COM1 + 5) & 0x20 == 0 {}
        outb(COM1, byte);
    }
    while inb(COM1 + 5) & 0x40 == 0 {}

    // isa-debug-exit maps guest value n to QEMU exit status (n << 1) | 1.
    unsafe { asm!("out dx, eax", in("dx") 0xf4u16, in("eax") 0x2au32, options(nomem, nostack, preserves_flags)) }
    halt()
}

#[panic_handler]
fn panic(_info: &PanicInfo<'_>) -> ! {
    halt()
}

fn halt() -> ! {
    loop {
        unsafe { asm!("hlt", options(nomem, nostack)) }
    }
}
