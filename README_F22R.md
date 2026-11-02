# DS-ACK V1.12 F22R — KernelSU-Next 3.4.2 legacy

Unofficial update of DS-ACK by [duhansysl](https://github.com/duhansysl/exynos9810-kernel).
Original credits, license and recovery installer lineage are retained.

## Two variants

- Regular Enforcing KernelSU: original Android 11–14 variant.
- Enforcing KernelSU **OneUI7**: original Android 15–16 variant. The exact original
  ExtremeROM brightness/boot-mode framework is present, and
  `CONFIG_ONEUI7_WORKAROUND=y` is enabled only in this variant.

Each ZIP covers G960F, G965F, N960F, G960N, G965N and N960N with the original
bootloader-based model selection, per-model kernel/DTB deltas, and preservation
of the installed boot ramdisk. Android version ranges follow the original
developer's release notes; they are not a claim of new physical-device testing.

## KernelSU source

This is a **built-in non-GKI legacy integration**. It uses official legacy commit
`b933b1f728116a456fbebf27b6a8772a640cdf23`, including the upstream 3.4.2 feature
backports in `c81cdf51` and the subsequent SELinux rwlock allocation fix.
It does not substitute the GKI/LKM driver from tag v3.4.2 into a 4.9 kernel.

The checked-in integration patch preserves Samsung 4.9 read/write compatibility,
execve hook pointer arguments, manager discovery, and the old zero-length
SELinux ioctl payload used by existing Zygisk/Vector helpers. Upstream manager
scan serialization and authenticated-manager FD renewal replace the obsolete
versions of those local patches. The working host SELinux/atomic-allocation and
daemon-domain fixes from the prior F22R build are retained.

`KSU_VERSION_TAG_OVERRIDE=v3.4.2` and the upstream-supported
`KSU_VERSION_OVERRIDE=33355` explicitly pin the integration's reported version
to the official v3.4.2 Manager release code. Unmodified legacy commit-count
calculation is 33318; both values and the exact source commit are documented
here to avoid implying that the commit histories match.

Use the official **Main v3.4.2 Manager**, not an unrelated APK with an incompatible
signing certificate. Manager and ksud updates are separate from flashing the ZIP.

## Build

Local environment: Ubuntu-KernelBuild WSL, Clang 18, original Apollo configs.
The build driver reuses Apollo's compiler/config/model functions and captures
Image, DTB, .config, System.map, compiler command and selected disassembly for
every model before packaging.

Build and packaging default to their own checkout and use .f22r for local outputs;
source and verification scripts are included in `tools/f22r/` with instructions.
Kernel version strings retain DS-ACK, original model and build date, add F22R
and v3.4.2, and contain no `-KSU` suffix. OneUI7 adds the `-OneUI7` marker.

## Verification limits

Compiler success and package reconstruction are separate from boot/runtime
verification. This update has not yet been physically tested for boot, module
installation/removal, Zygisk injection, Vector/LSPosed, or OneUI7 brightness.
The previous S9+ test applies to the earlier build only.
