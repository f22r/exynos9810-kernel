# Kernel optimization verification — 2026-11-04

All work continues in the existing local branch f22r-susfs230, source /root/f22r-susfs230 in Ubuntu-KernelBuild. No new branch was created for this optimization. Existing SUSFS 2.3 adaptation, camera deferred-free and RNG suspend-drain changes remain.

## Changes

1. CPU schedutil slack timer: get_next_event_time_ms previously converted sleep duration to microseconds while comparing it with expired_time in milliseconds. It now uses ktime_to_ms, matching msecs_to_jiffies at timer scheduling. This avoids scheduling the timer for short predicted idle intervals that are below its intended threshold.
2. GPU DVFS: clear timer_active under the callback spinlock before cancel_delayed_work_sync. Reuse this cancellation for runtime stop and workqueue teardown, so a running callback cannot requeue after cancellation. Clock tables, thermal controls and polling intervals are unchanged.
3. MAX77705: routine monitor diagnostics are opt-in via root-only monitor_debug module parameter (factory builds default on). Disabling them skips 19 register-dump reads plus two diagnostic status reads per monitor request. Charge regulation, health checks, IRQ handling and fault-triggered dumps are unchanged.
4. Input booster: repetitive set/release logging uses the existing debug_level gate.
5. KernelSU: five routine setuid/unmount log sites use the existing ksu_dbg facility. Failure logs and functionality remain. The tracked adaptation patch was regenerated.

## Device snapshot and decisions

ADB root read-only inspection of the connected S9+ succeeded. Running kernel remains the 02.11.2026 build; no new kernel was flashed.
- schedutil both clusters; rate limits 5000/5000 microseconds.
- Battery saver active; big CPU capped at 1924000 kHz. This cap was not overridden.
- Input booster enable_event=0, debug_level=0. Timing changes would not benefit this snapshot.
- Active GPU: Bifrost r38p1 with exynos frontend; DT minimum 338000, runtime PM delay 50 ms, polling 30 ms. Old tHEx drivers were not modified.
- zRAM 6 GiB logical capacity, LZ4; page-cluster=0, swappiness=130. Approximately 2.8 GB original pages occupied 842 MB physical zRAM memory. MemAvailable approximately 1.7 GiB and current memory PSI avg10=0.00. No forced zRAM resize, swapoff, swappiness rewrite or compressor change was made.
- Prior suspend/RNG and camera fixes retained; no new claim that their runtime behavior is validated.

## Verification scope

python3 tools/f22r/test-optimization.py: extracted production C functions with ASan/UBSan and stubbed kernel interfaces. Cases: 0/1/69/70/71/1000 ms idle threshold, boost/min-util exclusions, diagnostic off/on/fault read counts, and GPU requeue-disable/cancel/destroy ordering. These are host tests, not a proof of actual concurrent hardware behavior.

Also rerun existing SUSFS and KernelSU regression suites after changes. Build uses tools/f22r/build.sh regular with F22R_MODELS=2. Final build status, checksums and copied artifacts are recorded in the artifact verification report.

Pending: boot/module/SUSFS smoke tests, real CPU/GPU suspend transitions, charging and thermal checks, camera use, screen-off battery A/B and frame-time measurement. No battery percentage improvement, first-boot improvement, all-ROM compatibility or real-device stability is claimed. Previously diagnosed ART/odsign/framework ROM issues are outside these kernel changes.