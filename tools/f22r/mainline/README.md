# Linux 7.1 bring-up for the Galaxy S9+ SM-G965F

This branch builds an ARM64 kernel and device tree for the international Exynos S9+ (`star2lte`). The first milestone is an Android-oriented configuration with Binder IPC and binderfs, 32-bit app support, SELinux, seccomp, ext4, compressed EROFS, pstore and the Exynos 9810 UFS host. The DT uses the board port's memory map and enables its UFS supply and controller.

## Build

Use Linux with Git, make, LLVM/Clang, flex, bison, libelf development headers, bc, Python 3 and fdtget. Run these commands from this repository's root with a fresh workspace on a Linux filesystem.

```sh
mkdir -p ../star2lte-lab
git clone --depth 1 --branch v7.1 https://github.com/torvalds/linux ../star2lte-lab/linux
git clone https://github.com/SheroAbi/galaxy-s9plus-mainline-linux ../star2lte-lab/board
git -C ../star2lte-lab/board checkout --detach bcee6014fc2e44a4c4f1c34bca0a880d4b543ec3
bash tools/f22r/mainline/build.sh ../star2lte-lab/linux ../star2lte-lab/board ../star2lte-lab/output
```

The builder checks both source revisions, applies the board driver's patch set in a scratch checkout, and validates the selected options in the generated configuration. It checks the ARM64 Image header, board identity, hardware revision and UFS status in the compiled DTB. Paths and hashes are recorded in `output/SHA256SUMS`.

## First build (2 November 2026)

The build produced `7.1.0-f22r-star2lte-lab-dirty`. The suffix comes from applying the board patches to the pinned Linux checkout. The generated DTB reports `Samsung Galaxy S9+ (SM-G965F)` and enables `/soc@0/ufs@11120000`. The ARM64 header, requested config values and hashes passed the local checks.

| File | SHA-256 |
| --- | --- |
| Image | `2c6dc679500f58e4efb5e0d7a541c1e448899b8f0bda5546fca34d6ef969a683` |
| DTB | `0f651df06556517e82c07b110b2ce63caa792f177c331403a80f06885a8b1da3` |
| .config | `6530cc0c7121e62abefa1e57917c2818e5b1db6854c5b96e248e70f7f63c1df3` |

## Hardware and Android testing

The outputs are a raw Image and DTB for development. The next hardware milestone requires a bootloader shim, a diagnostic ramdisk and a tested recovery path. Android first-stage init, encrypted userdata, Samsung vendor HALs, modem, camera, suspend and KernelSU integration still require separate work and on-device tests.

Linux is pinned to [v7.1](https://github.com/torvalds/linux/commit/8cd9520d35a6c38db6567e97dd93b1f11f185dc6). Board support comes from [SheroAbi's SM-G965F Linux port](https://github.com/SheroAbi/galaxy-s9plus-mainline-linux/tree/bcee6014fc2e44a4c4f1c34bca0a880d4b543ec3), which documents its uniLoader requirements and Ubuntu hardware results. DS-ACK and the 4.9 release remain credited in [README_F22R.md](../../../README_F22R.md).
