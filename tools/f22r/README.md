# Build and verify the F22R release

Requirements: Linux, Clang/LLVM 18 tools in ../compiler/clang-custom/bin,
ARM32 cross tools, kernel build dependencies, bsdiff/bspatch, Python 3.

Clone the source branch recursively, then use:

```bash
export F22R_KERNEL_ROOT="$PWD"
export F22R_CAPTURE_ROOT="$PWD/../captures-v342"
export F22R_REFERENCE_ZIPS="$PWD/../reference-v112"
export F22R_OUTPUT="$PWD/../release-v342"
export F22R_BUILD_DATE=16.10.2026
bash tools/f22r/build.sh regular
bash tools/f22r/build.sh OneUI7
python3 tools/f22r/package.py
python3 tools/f22r/test-legacy-policy.py KernelSU-Next
```

Place both original V1.12 Enforcing KernelSU ZIPs (regular and OneUI7) in
F22R_REFERENCE_ZIPS. Packaging verifies original DTBs/tools and reconstructs
every bsdiff delta. `F22R_MODELS=2` limits a diagnostic build to S9+ G965F;
complete packaging requires all six models for both variants.

Apollo applies patches/kernelsu-next-v3.4.2-exynos9810.patch idempotently to the
pinned upstream legacy submodule. Its dirty state after applying this tracked
patch is expected; the submodule commit itself remains upstream b933b1f7.
No GitHub Actions or phone connection is required to compile or package.
