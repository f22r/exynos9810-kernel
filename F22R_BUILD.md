# F22R KernelSU-Next build

## Current focus: R4 for G965F

Development now prioritizes Galaxy S9+ G965F. R3 was reported booting with Manager showing **Working / BUILT-IN (LEGACY)** and driver code 33296. Module entries were visible, but a subsequent Zygisk loading report still needs device logs; this is not proof that every module runs correctly.

R4 sets the upstream-supported `KSU_VERSION_TAG_OVERRIDE=v3.4.0`. The pinned legacy checkout had no describable Git tag, so R3 compiled an empty version label and Manager displayed v0.0.0. The numeric driver version remains derived from the same pinned source.

Select target `2` (the new default), compiler `8`, Enforcing `2`, and KernelSU `y`. A single G965F recovery ZIP is created before the original boot-image packaging step. It contains only the G965F kernel/DTB and adapts the upstream installer to reject other models while retaining the phone's existing boot ramdisk. Other devices will be compiled later. R4 addresses version labeling and packaging; it does not claim a Zygisk fix.

The displayed kernel version ends in `F22R-R4-v3.4.0` without `-KSU`. Previous revision details below are historical.

This is an unofficial F22R modification of [duhansysl's DS-ACK Exynos 9810 kernel V1.12](https://github.com/duhansysl/exynos9810-kernel/releases/tag/V1.12). The DS-ACK name identifies the upstream kernel; F22R identifies this modification. It is not an upstream DS-ACK release.

The target package is the regular `DS-ACK-V1.12-08.05.2026-Enforcing-KernelSU.zip` for Android 11–14. This branch does not build the separately labeled OneUI7 or Q release variants.

The kernel base remains Linux 4.9.337 from DS-ACK V1.12. This branch pins [KernelSU-Next's `legacy` branch](https://github.com/KernelSU-Next/KernelSU-Next/tree/legacy) at `5e2f85327336185a8330429422ad04b84c6e6d38`, which contains the v3.4.0 legacy updates for older kernels. The `patches/kernelsu-next-legacy-4.9.patch` file adapts allowlist writes to the Linux 4.9 API. The `patches/kernelsu-next-legacy-manager-discovery.patch` file retries discovery of a Manager already installed before this kernel is flashed. Small compatibility headers and the arm32 VDSO linker adjustment allow the upstream build script to use Ubuntu's Clang 18.

The build script retains the original six device targets: Galaxy S9 and S9+, Galaxy Note9, and their Korean variants. Select target `7` to produce the original combined flashable ZIP. Select a single target to build an individual boot image. The image filename includes `KernelSU-Next-v3.4.0` to distinguish its contents. The displayed kernel version uses the original `DS-ACK-V1.12-<model>-<build date>` structure and appends `F22R-R3-v3.4.0`, without a `KSU` label. The build date uses Asia/Jakarta time.

R2 corrected the legacy setresuid call and added discovery retries. A subsequent G965F screenshot confirmed R2 was running, but Manager still reported "Unsupported | Not integrated". The earlier seccomp log established that the Manager could not obtain a driver descriptor; it did not establish the root cause.

R3 fixes a confirmed Linux 4.9 API incompatibility in the pinned legacy source. Direct `kernel_read(file, buffer, size, position)` calls were compiled against this kernel's older `kernel_read(file, offset, buffer, size)` signature while `-Wno-int-conversion` hid the mismatch. The new `patches/kernelsu-next-legacy-read-compat.patch` routes APK verification, packages.list, allowlist, and module init.rc reads through the existing `ksu_kernel_read_compat` adapter. `patches/kernelsu-next-legacy-execve-compat.patch` also supplies a valid fd pointer in the legacy execve helpers. Neither patch changes the expected Manager signing certificate.

After a build, run `python3 tools/f22r-check-read-compat.py /path/to/kernel --compiler /path/to/clang`. This applies the patches to a temporary copy of the pinned submodule and checks the four affected translation units using the actual kernel build arguments plus `-Werror=int-conversion`: R2 must fail for the read API mismatch and R3 must pass. This verifies the source defect and repair, not successful root access on a phone. R3 remains a test release until boot, Manager integration, root grants, and modules are verified on-device. Use the official KernelSU-Next v3.4.0 Manager for that test; do not mix the older v3.1.0 Manager result with v3.4.0 results.

Build on a Linux filesystem with the repository and submodule fully checked out. The script's custom compiler option (`8`) expects Clang 18 in `../compiler/clang-custom/bin`. Select Enforcing (`2`) and KernelSU (`y`) for the variant based on the upstream Enforcing KernelSU ZIP.

SUSFS is not included. The separate `susfs4ksu-module` requires a SUSFS-patched kernel; do not install it as if this build provided that feature.
