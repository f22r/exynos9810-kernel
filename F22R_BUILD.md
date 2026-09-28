# F22R KernelSU-Next build

This is an unofficial F22R modification of [duhansysl's DS-ACK Exynos 9810 kernel V1.12](https://github.com/duhansysl/exynos9810-kernel/releases/tag/V1.12). The DS-ACK name identifies the upstream kernel; F22R identifies this modification. It is not an upstream DS-ACK release.

The target package is the regular `DS-ACK-V1.12-08.05.2026-Enforcing-KernelSU.zip` for Android 11–14. This branch does not build the separately labeled OneUI7 or Q release variants.

The kernel base remains Linux 4.9.337 from DS-ACK V1.12. This branch pins [KernelSU-Next's `legacy` branch](https://github.com/KernelSU-Next/KernelSU-Next/tree/legacy) at `5e2f85327336185a8330429422ad04b84c6e6d38`, which contains the v3.4.0 legacy updates for older kernels. The `patches/kernelsu-next-legacy-4.9.patch` file adapts allowlist writes to the Linux 4.9 API. Small compatibility headers and the arm32 VDSO linker adjustment allow the upstream build script to use Ubuntu's Clang 18.

The build script retains the original six device targets: Galaxy S9 and S9+, Galaxy Note9, and their Korean variants. Select target `7` to produce the original combined flashable ZIP. Select a single target to build an individual boot image. The image filename includes `KernelSU-Next-v3.4.0` to distinguish its contents. The displayed kernel version uses the original `DS-ACK-V1.12-<model>-<build date>` structure and appends `F22R-v3.4.0`, without a `KSU` label. The build date uses Asia/Jakarta time.

Build on a Linux filesystem with the repository and submodule fully checked out. The script's custom compiler option (`8`) expects Clang 18 in `../compiler/clang-custom/bin`. Select Enforcing (`2`) and KernelSU (`y`) for the variant based on the upstream Enforcing KernelSU ZIP.

SUSFS is not included. The separate `susfs4ksu-module` requires a SUSFS-patched kernel; do not install it as if this build provided that feature.
