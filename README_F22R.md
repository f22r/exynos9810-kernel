# DS-ACK F22R V1.14 — KernelSU-Next 3.4.2 legacy

Unofficial update of DS-ACK by [duhansysl](https://github.com/duhansysl/exynos9810-kernel).
F22R V1.14 is based on DS-ACK V1.12. The kernel release string retains the upstream base and the F22R build date.
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

Use the included **Manager v3.4.2-100-ga6c81fa4 (33455-6)**. This APK was
verified with the legacy driver (33355-6); these version codes need not be equal.
Manager and ksud updates are separate from flashing the ZIP.

## SUSFS and maintenance changes

SUSFS 2.3.0 is integrated with the limited feature profile documented in
[tools/f22r/SUSFS.md](tools/f22r/SUSFS.md). The release includes the unmodified
official SUSFS module R28, tested with its universal ARM64 utility.

Retained camera allocation/deferred-free and RNG suspend-drain fixes are joined
by a schedutil timer-unit correction, GPU DVFS timer shutdown synchronization,
and reduced routine input/charger/KernelSU logging. Battery gains are not yet measured.

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

On 2026-11-04, the regular G965F image was tested on a Galaxy S9+ running Noble
Android 14: boot/unlock, root, SELinux Enforcing, Manager, SUSFS installation and
reboot, SUSFS version/features and rejection of non-root queries, both Zygisk
architectures, and rear/front camera preview switching. No kernel panic/Oops
signature appeared in the collected post-test dmesg. Camera preview frames were
confirmed; photo/video capture and every third-party module were not tested.

Other models and OneUI7 receive build/package verification only. OneUI7/UN1CA
runtime compatibility, long-term stability, battery improvement, module removal,
and exhaustive mount isolation remain unverified. The upstream per-variant DTBs
and their ext4 fstab declarations are preserved; this release does not claim
compatibility with ROM layouts requiring different fstab/filesystem settings.
