#!/usr/bin/env bash
# Compile-only bring-up for SM-G965F. Use dedicated source checkouts.
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
linux=$(realpath "${1:?path to clean torvalds/linux v7.1 checkout}")
board=$(realpath "${2:?path to SheroAbi board support checkout}")
out=$(realpath -m "${3:?path to separate output directory}")
test "$(git -C "$linux" rev-parse HEAD)" = 8cd9520d35a6c38db6567e97dd93b1f11f185dc6
test "$(git -C "$board" rev-parse HEAD)" = bcee6014fc2e44a4c4f1c34bca0a880d4b543ec3
for source in "$linux" "$board"; do
    if [[ -n $(git -C "$source" status --porcelain) ]]; then
        echo "Expected a pristine source checkout: $source" >&2
        exit 1
    fi
    case "$out/" in "$source/"*) echo "Output must be outside the inputs" >&2; exit 1;; esac
done
mkdir -p "$out"
# Keep imported drivers and generated files out of the two pinned inputs.
scratch=$(mktemp -d "$out/src.XXXXXXXX")
git clone --quiet --local --no-hardlinks "$linux" "$scratch"
git -C "$scratch" checkout -q --detach 8cd9520d35a6c38db6567e97dd93b1f11f185dc6
bash "$board/scripts/build/apply_drivers.sh" "$scratch"
dts=arch/arm64/boot/dts/exynos/exynos9810-star2lte.dts
sed 's|status = "disabled"; /\* UFS-STATUS \*/|status = "okay"; /* UFS-STATUS */|' \
    "$board/src/mainline-dts/exynos9810-star2lte.dts" > "$scratch/$dts"
printf '\ndtb-$(CONFIG_ARCH_EXYNOS) += exynos9810-star2lte.dtb\n' >> "$scratch/arch/arm64/boot/dts/exynos/Makefile"
kbuild=(make -C "$scratch" O="$out/obj" ARCH=arm64 LLVM=1)
KCONFIG_ALLCONFIG="$here/star2lte.config" "${kbuild[@]}" allnoconfig
# Kconfig silently drops requested settings with unmet dependencies.
while IFS= read -r setting; do
    [[ $setting == CONFIG_*=* ]] || continue
    if ! grep -Fxq "$setting" "$out/obj/.config"; then
        echo "Configuration rejected: $setting" >&2
        exit 1
    fi
done < "$here/star2lte.config"
"${kbuild[@]}" -j"${JOBS:-4}" Image exynos/exynos9810-star2lte.dtb
dtb="$out/obj/arch/arm64/boot/dts/exynos/exynos9810-star2lte.dtb"
image="$out/obj/arch/arm64/boot/Image"
test "$(fdtget "$dtb" / compatible)" = "samsung,star2lte samsung,exynos9810"
test "$(fdtget -t x "$dtb" / model_info-hw_rev)" = 1a
ufs=/soc@0/ufs@11120000
test "$(fdtget "$dtb" "$ufs" status)" = okay
test "$(fdtget "$dtb" "$ufs" compatible)" = samsung,exynos9810-ufs
python3 -c 'import sys; f=open(sys.argv[1],"rb"); f.seek(56); sys.exit(f.read(4)!=b"ARM\x64")' "$image"
(cd "$out/obj" && sha256sum arch/arm64/boot/Image arch/arm64/boot/dts/exynos/exynos9810-star2lte.dtb .config > "$out/SHA256SUMS")
echo "Verified SM-G965F Image, DTB and config: $out/SHA256SUMS"
