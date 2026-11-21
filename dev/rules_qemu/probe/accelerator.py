"""Probe the host hypervisor interface before starting QEMU."""

import ctypes


def accelerator_available(accelerator):
    if accelerator == "kvm":
        import fcntl

        try:
            with open("/dev/kvm", "rb+", buffering=0) as kvm:
                return fcntl.ioctl(kvm, 0xAE00, 0) == 12
        except OSError:
            return False

    if accelerator != "whpx":
        raise ValueError(f"unexpected accelerator: {accelerator}")
    try:
        platform = ctypes.WinDLL("WinHvPlatform.dll", winmode=0x800)  # LOAD_LIBRARY_SEARCH_SYSTEM32
    except OSError:
        return False
    present = ctypes.c_uint32()
    if platform.WHvGetCapability(0, ctypes.byref(present), ctypes.sizeof(present), None) or not present.value:
        return False
    partition = ctypes.c_void_p()
    if platform.WHvCreatePartition(ctypes.byref(partition)):
        return False
    platform.WHvDeletePartition(partition)
    return True
