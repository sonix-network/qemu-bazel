ENTRY(pvh_entry)

PHDRS
{
    text PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
    note PT_NOTE FLAGS(4);
}

SECTIONS
{
    . = 0x100000;
    .note.Xen : { KEEP(*(.note.Xen)) } :text :note
    .text : { KEEP(*(.text.boot)) *(.text .text.*) } :text
    .rodata : { *(.rodata .rodata.*) } :text
    .data ALIGN(4096) : { *(.data .data.*) } :data
    .bss (NOLOAD) : {
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(16);
        . += 0x4000;
        __stack_top = .;
    } :data

    /DISCARD/ : { *(.eh_frame .eh_frame_hdr) }

    ASSERT(__stack_top <= 0x200000, "guest image exceeds its identity map")
}
