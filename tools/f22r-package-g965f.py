#!/usr/bin/env python3
"""Package a single G965F kernel using the upstream ramdisk-preserving installer."""
import pathlib
import sys
import zipfile

root = pathlib.Path(sys.argv[1]).resolve()
name = sys.argv[2]
if "-G965F-" not in name or pathlib.Path(name).name != name:
    raise SystemExit("Expected a G965F image name")
template = root / "Apollo/kernelzip"
kernel = root / "arch/arm64/boot/Image"
dtb = root / "arch/arm64/boot/dtb.img"
if not kernel.is_file() or not dtb.is_file():
    raise SystemExit("Compiled kernel or DTB missing")
installer_path = "META-INF/com/google/android/update-binary"
installer = (template / installer_path).read_text()
start = installer.index("    if echo $device | grep 'G960[F]'; then")
end = installer.index("    fi", start) + len("    fi")
installer = installer[:start] + '''    ui_print "- S9+ G965F detected (single-device package)"
    mv G965F-kernel kernel || exit 1
    mv G965F-dtb extra || exit 1''' + installer[end:]
installer = installer.replace("grep '[GN]96[05][FN]'", "grep 'G965[F]'")
installer = installer.replace("fkv", name)
installer = installer.replace('    boot=$($bb find /dev/block/platform -iname boot)',
                              '    boot=$($bb find /dev/block/platform -iname boot)\n    [ -b "$boot" ] || exit 1')
for command in ('dd if=$boot of=/tmp/floydKernel/old-boot.img bs=4096',
                './imgtool unpack old-boot.img', './imgtool repack -n old-boot.img',
                'cp new-boot.img /tmp/floyd/boot.img',
                'dd if=/tmp/floyd/boot.img of=$boot bs=4096'):
    installer = installer.replace(command, command + ' || exit 1')
out = root / "Apollo/Product" / (name + ".zip")
out.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as package:
    for path in ("LICENSE", "META-INF/com/google/android/updater-script",
                 "floyd/tools/magiskboot", "floyd/tools/busybox"):
        package.write(template / path, path)
    entry = zipfile.ZipInfo(installer_path)
    entry.external_attr = 0o100755 << 16
    package.writestr(entry, installer, compress_type=zipfile.ZIP_DEFLATED)
    package.write(kernel, "floyd/G965F-kernel")
    package.write(dtb, "floyd/G965F-dtb")
with zipfile.ZipFile(out) as package:
    if package.testzip() is not None:
        raise SystemExit("ZIP integrity failed")
print(f"G965F recovery ZIP ready: {out}")
