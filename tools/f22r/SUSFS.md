# SUSFS 2.3.0 experimental integration

Target: regular Galaxy S9+ G965F, Linux 4.9.337 DS-ACK. Development branch: `beta`; validated release source is promoted to `main`.

## Sources

- 4.9 port: https://github.com/wxx9248/susfs4ksu, commit 71345ded5af28f55d76ebcdc7a9df9cea56111e1.
- Command-dispatch reference: https://github.com/ReSukiSU/ReSukiSU, commit 516d3e87fbc986ccefdde2c2765f1700612441a9.
- KernelSU-Next remains pinned to b933b1f728116a456fbebf27b6a8772a640cdf23 with the existing Exynos adaptation patch extended to include the SUSFS adapter. No switch to ReSukiSU and no Manager ABI change.

## Adaptation

The upstream port's replacement sucompat/init/reboot/setuid hooks were not applied over the existing Next hooks. The v2 reboot-command ABI uses magic2 0xFAFAFAFA and accepts only UID 0 in the KernelSU SELinux domain. Existing KernelSU ioctl/daemon integration remains.

DS-ACK has a backported statx interface; vfs_getattr_nosec preserves its request/query arguments and result mask. Android's existing bpfloader/netd uname behavior and ROM cmdline fallback remain. Process mount state is marked after the existing Next unmount task work, and cleared when granting privileged credentials.

Corrections to the reference port:
- Supply a real fsnotify mark free callback, release the retained mark, and clear ownership on error cleanup.
- Avoid NULL dereference when allocating the enabled-features reply fails.
- Compare full inode/device keys for kstat hash-bucket lookups.
- Correct statfs spoof-success versus real-filesystem fallback behavior.
- Preserve reference ownership in the mount helper fallback and handle d_path error pointers.
- Supply required self-contained headers and compatible declarations.

The previous camera deferred-free and RNG suspend-drain fixes are retained.

## Feature profile

Enabled: SUS_MOUNT, SUS_KSTAT, SPOOF_UNAME, HIDE_KSU_SUSFS_SYMBOLS, SPOOF_CMDLINE_OR_BOOTCONFIG. Verbose logging is off. Path hiding, open redirect and map hiding are unavailable in this initial profile (Kconfig BROKEN dependency), pending separate integration and validation. This is not a claim of full upstream feature parity.

Use an ARM64 SUSFS v2.3-compatible userspace utility; the v1.5.5 utility is incompatible. The matching command structure was checked against the ReSukiSU reference, and tested on G965F with the official SUSFS module R28 universal utility (SHA256 8a626ce3bae27a7bcaa2e7f5f7b91e786ecc57f8e57d19c7856719a89b54b6fa). No SUSFS module is automatically enabled by this source change.

## Validation

Host regression test: python3 tools/f22r/test-susfs230.py
Uses extracted production C functions with stubbed kernel interfaces and ASan/UBSan to check hash collisions, OOM replies, privileged command dispatch and statfs fallback. These are host tests, not Android/kernel runtime tests.

Existing KernelSU tests: python3 tools/f22r/test-legacy-policy.py KernelSU-Next
Build: F22R_MODELS=2 F22R_BUILD_DATE=04.11.2026 F22R_CAPTURE_ROOT=/root/f22r-susfs230-20261104/captures bash tools/f22r/build.sh regular

On 2026-11-04 the regular G965F image booted on Noble Android 14, retained root
and SELinux Enforcing, answered v2.3.0 and feature queries, and rejected non-root
queries. Official SUSFS R28 installed and survived reboot; WebUI and both Zygisk
architectures were active. Rear and front camera previews produced frames, and
switching between them succeeded. Collected post-test dmesg had no panic/Oops
signature. The matching Manager was 33455-6 with driver 33355-6.

Pending: long-term stability, suspend/battery improvement, exhaustive mount
isolation, module removal, full camera capture modes and other physical models.
OneUI7/UN1CA runtime compatibility is not established.
