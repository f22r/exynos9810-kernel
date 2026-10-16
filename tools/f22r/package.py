"""Package and reconstruct both universal variants; fail on any mismatch."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

root = Path(os.environ.get('F22R_KERNEL_ROOT', '/root/exynos9810-f22r-3.4.2'))
captures = Path(os.environ.get('F22R_CAPTURE_ROOT', '/root/f22r-v342-images'))
out = Path(os.environ.get('F22R_OUTPUT', '/mnt/e/Android/artifacts/v3.4.2'))
out.mkdir(parents=True, exist_ok=True)
models = ('G960F', 'G965F', 'N960F', 'G960N', 'G965N', 'N960N')
date = os.environ.get('F22R_BUILD_DATE', '16.10.2026')

def sha(data): return hashlib.sha256(data).hexdigest()

reports = {}
for variant in ('regular', 'OneUI7'):
    suffix = '-OneUI7' if variant == 'OneUI7' else ''
    name = f'DS-ACK-V1.12-F22R-{date}-Enforcing-KernelSU{suffix}'
    original_name = f'DS-ACK-V1.12-08.05.2026-Enforcing-KernelSU{suffix}.zip'
    source_zip = Path(os.environ.get('F22R_REFERENCE_ZIPS', '/mnt/e/Android/reference-v112')) / original_name
    image_folder = captures / variant
    with tempfile.TemporaryDirectory(prefix='f22r-package-') as tmp:
        stage = Path(tmp)
        template = root / 'Apollo/kernelzip'
        paths = ('LICENSE', 'META-INF/com/google/android/updater-script',
                 'META-INF/com/google/android/update-binary', 'floyd/tools/busybox',
                 'floyd/tools/magiskboot', 'floyd/tools/bsdiff')
        for rel in paths:
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template / rel, target)
        installer = stage / paths[2]
        text = installer.read_text().replace('fkv', name)
        # Retain the upstream ramdisk-preserving flow; stop on failed operations.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(('mv G', 'mv N', './tools/bsdiff ', 'dd if=',
                                    './imgtool ', 'cp new-boot.img')):
                text = text.replace(line, line + ' || exit 1')
        text = text.replace('    boot=$($bb find /dev/block/platform -iname boot)',
            '    boot=$($bb find /dev/block/platform -iname boot)\n    [ -b "$boot" ] || exit 1')
        label = 'OneUI7 / Android 15-16' if variant == 'OneUI7' else 'Regular / Android 11-14'
        text = text.replace('    ui_print "Detecting device..."',
            f'    ui_print "{label}; KernelSU-Next v3.4.2 (legacy)"\n    ui_print "Detecting device..."')
        installer.write_text(text)
        records = {}
        for model in models:
            image = (image_folder / (model + '.Image')).read_bytes()
            dtb = (image_folder / (model + '.dtb')).read_bytes()
            config = (image_folder / (model + '.config')).read_text()
            symbols = (image_folder / (model + '.System.map')).read_text()
            version = f'4.9.337-DS-ACK-V1.12-{model}-{date}-F22R-v3.4.2{suffix}'
            assert version.encode() in image, (variant, model, 'uname')
            assert len(version) <= 64
            assert image[56:60] == b'ARM\x64', (variant, model, 'arm64 header')
            for flag in ('CONFIG_KSU=y', 'CONFIG_KSU_MANUAL_HOOK=y', 'CONFIG_SECURITY_SELINUX=y'):
                assert flag in config.splitlines(), (variant, model, flag)
            assert 'CONFIG_ALWAYS_PERMISSIVE=y' not in config
            enabled = 'CONFIG_ONEUI7_WORKAROUND=y' in config.splitlines()
            assert enabled == (variant == 'OneUI7')
            assert (' get_fixed_brightness\n' in symbols) == enabled
            assert b'v3.4.2' in image
            command_file = image_folder / (model + '.ksu-command.txt')
            command = command_file.read_text()
            assert '-DKSU_VERSION=33355' in command
            for ext, data in (('kernel', image), ('dtb', dtb)):
                dest = stage / f'floyd/{model}-{ext}'
                if model == 'G960F':
                    dest.write_bytes(data)
                else:
                    base = image_folder / ('G960F.Image' if ext == 'kernel' else 'G960F.dtb')
                    source = image_folder / (model + ('.Image' if ext == 'kernel' else '.dtb'))
                    subprocess.run(['bsdiff', str(base), str(source), str(dest)], check=True)
            records[model] = {'uname': version, 'Image_sha256': sha(image), 'DTB_sha256': sha(dtb),
                              'OneUI7': enabled, 'driver_version': 33355}
        archive = out / (name + '.zip')
        with ZipFile(archive, 'w', ZIP_DEFLATED) as package:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    rel = path.relative_to(stage).as_posix()
                    entry = ZipInfo(rel)
                    entry.external_attr = 0o100755 << 16
                    package.writestr(entry, path.read_bytes(), compress_type=ZIP_DEFLATED)
        with ZipFile(archive) as package, ZipFile(source_zip) as original:
            assert package.testzip() is None
            for tool in ('busybox', 'magiskboot', 'bsdiff'):
                rel = 'floyd/tools/' + tool
                assert package.read(rel) == original.read(rel), ('original tool changed', tool)
            for model in models:
                for ext in ('kernel', 'dtb'):
                    data = package.read(f'floyd/{model}-{ext}')
                    if model != 'G960F':
                        patch = stage / 'verify.patch'
                        patch.write_bytes(data)
                        rebuilt = stage / 'verify.output'
                        subprocess.run(['bspatch', str(stage / f'floyd/G960F-{ext}'),
                                        str(rebuilt), str(patch)], check=True)
                        data = rebuilt.read_bytes()
                    expected = records[model]['Image_sha256' if ext == 'kernel' else 'DTB_sha256']
                    assert sha(data) == expected, (variant, model, ext, 'delta reconstruction')
                    # Neither variant changes device trees from its exact upstream ZIP.
                    original_data = original.read(f'floyd/{model}-{ext}')
                    if ext == 'dtb':
                        if model != 'G960F':
                            (stage / 'original-base').write_bytes(original.read('floyd/G960F-dtb'))
                            (stage / 'original-patch').write_bytes(original_data)
                            subprocess.run(['bspatch', str(stage / 'original-base'), str(stage / 'original-dtb'),
                                            str(stage / 'original-patch')], check=True)
                            original_data = (stage / 'original-dtb').read_bytes()
                        assert original_data == data, (variant, model, 'DTB differs from upstream')
            assert 'Unofficial F22R' in package.read(paths[2]).decode()
        reports[variant] = {'file': archive.name, 'sha256': sha(archive.read_bytes()),
                            'bytes': archive.stat().st_size, 'models': records}
        print('VERIFIED', variant, archive.name, reports[variant]['sha256'], flush=True)

for model in models:
    assert reports['regular']['models'][model]['Image_sha256'] != reports['OneUI7']['models'][model]['Image_sha256']
(out / 'verification.json').write_text(json.dumps(reports, indent=2))
print('PASS: 12 kernels, 12 DTBs, Enforcing, legacy KSU, OneUI7 separation and original tools verified.')
