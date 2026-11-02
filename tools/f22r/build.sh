#!/usr/bin/env bash
set -euo pipefail
variant=${1:?regular or OneUI7}
case "$variant" in regular) export CR_ONEUI7=n;; OneUI7) export CR_ONEUI7=y;; *) exit 2;; esac
repo=${F22R_KERNEL_ROOT:-$(cd -- "$(dirname -- "$0")/../.." && pwd)}
cd "$repo"
export CROSS_COMPILE_ARM32=arm-linux-gnueabihf-
export CR_JOBS_LIMIT=10
export KBUILD_BUILD_USER=F22R
export KBUILD_BUILD_HOST=local-wsl
# Reuse original Apollo configuration, compiler and model selection functions.
source <(sed '/^# Main Menu/,$d' apollo.sh)
set -euo pipefail
CR_MKZIP=y
CR_CLEAN=n
CR_KSU=y
CR_SELINUX=2
CR_COMPILER=8
capture="${F22R_CAPTURE_ROOT:-$repo/.f22r/captures}/$variant"
mkdir -p "$capture" "$CR_PRODUCT"
PACK_KERNEL_ZIP() {
  test -s "$CR_KERNEL"
  test -s "$CR_DTB"
  test -s System.map
  grep -q '^CONFIG_KSU=y$' .config
  grep -q '^CONFIG_KSU_MANUAL_HOOK=y$' .config
  grep -q '^CONFIG_SECURITY_SELINUX=y$' .config
  if grep -qx 'CONFIG_ALWAYS_PERMISSIVE=y' .config; then
    echo 'Refusing permissive configuration' >&2
    return 1
  fi
  if [[ "$variant" == OneUI7 ]]; then
    grep -q '^CONFIG_ONEUI7_WORKAROUND=y$' .config
    grep -q ' get_fixed_brightness$' System.map
  else
    if grep -qx 'CONFIG_ONEUI7_WORKAROUND=y' .config || grep -q ' get_fixed_brightness$' System.map; then
      echo 'OneUI7 workaround in regular build' >&2
      return 1
    fi
  fi
  cp "$CR_KERNEL" "$capture/$CR_VARIANT.Image"
  cp "$CR_DTB" "$capture/$CR_VARIANT.dtb"
  cp .config "$capture/$CR_VARIANT.config"
  cp System.map "$capture/$CR_VARIANT.System.map"
  cp drivers/kernelsu/core/.init.o.cmd "$capture/$CR_VARIANT.ksu-command.txt"
  "$OBJDUMP" -d --disassemble-symbols=handle_sepolicy,apply_kernelsu_rules,ksu_handle_execveat_ksud,panel_set_brightness,get_fixed_brightness \
    vmlinux > "$capture/$CR_VARIANT.audit.asm"
  echo "F22R_CAPTURE_OK $variant $CR_VARIANT $(sha256sum "$CR_KERNEL" | cut -d' ' -f1)"
}
for CR_TARGET in ${F22R_MODELS:-2 1 3 4 5 6}; do
  echo "F22R_BUILD_START $variant target=$CR_TARGET $(date -Is)"
  BUILD
  export -n CONFIG_MACH_EXYNOS9810_STARLTE_EUR_OPEN CONFIG_MACH_EXYNOS9810_STAR2LTE_EUR_OPEN \
    CONFIG_MACH_EXYNOS9810_CROWNLTE_EUR_OPEN CONFIG_MACH_EXYNOS9810_STARLTE_KOR \
    CONFIG_MACH_EXYNOS9810_STAR2LTE_KOR CONFIG_MACH_EXYNOS9810_CROWNLTE_KOR
done
echo "F22R_BUILD_DONE $variant $(date -Is)"
