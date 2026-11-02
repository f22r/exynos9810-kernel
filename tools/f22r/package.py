"""Package and reconstruct both universal variants; fail on any mismatch."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import re
import struct
from datetime import datetime
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

root = Path(os.environ.get('F22R_KERNEL_ROOT') or Path(__file__).resolve().parents[2])
captures = Path(os.environ.get('F22R_CAPTURE_ROOT') or root / '.f22r/captures')
out = Path(os.environ.get('F22R_OUTPUT') or root / '.f22r/releases')
out.mkdir(parents=True, exist_ok=True)
models = ('G960F', 'G965F', 'N960F', 'G960N', 'G965N', 'N960N')
# Read the build date from the kernel itself, including when packaging a prior build.
base_image = (captures / 'regular/G960F.Image').read_bytes()
dates = set(re.findall(rb'4\.9\.337-DS-ACK-V1\.12-G960F-(\d{2}\.\d{2}\.\d{4})-F22R-v3\.4\.2', base_image))
if len(dates) != 1:
    raise ValueError("missing or ambiguous build date in G960F.Image")
date = dates.pop().decode('ascii')
datetime.strptime(date, '%d.%m.%Y')
if os.environ.get('F22R_BUILD_DATE', date) != date:
    raise ValueError("requested build date differs from captured kernel")
del base_image

def sha(data): return hashlib.sha256(data).hexdigest()

def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def package_variant(variant, staging):
    suffix = '-OneUI7' if variant == 'OneUI7' else ''
    name = f'DS-ACK-V1.13-F22R-{date}-Enforcing-KernelSU{suffix}'
    original_name = f'DS-ACK-V1.12-08.05.2026-Enforcing-KernelSU{suffix}.zip'
    source_zip = Path(os.environ.get('F22R_REFERENCE_ZIPS') or '/mnt/e/Android/reference-v112') / original_name
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
        label = 'OneUI7 / Android 15-16' if variant == 'OneUI7' else 'Regular / Android 11-14'
        text = text.replace('    ui_print "Detecting device..."',
            f'    ui_print "{label}; KernelSU-Next v3.4.2 (legacy)"\n    ui_print "Detecting device..."')
        installer.write_text(text)
        records = {}
        for model in models:
            image = (image_folder / (model + '.Image')).read_bytes()
            dtb = (image_folder / (model + '.dtb')).read_bytes()
            if dtb[:4] != b'DTBH' or struct.unpack_from('<II', dtb, 4) != (2, 1):
                raise ValueError(f'{model}: unsupported DTBH header')
            offset, size = struct.unpack_from('<II', dtb, 32)
            if offset + size > len(dtb) or dtb[offset:offset + 4] != bytes.fromhex('d00dfeed'):
                raise ValueError(f'{model}: invalid DTBH entry')
            with tempfile.NamedTemporaryFile(dir=tmp) as tree:
                tree.write(dtb[offset:offset + size])
                tree.flush()
                for partition in ('system', 'vendor', 'odm'):
                    node = '/firmware/android/fstab/' + partition
                    fs = subprocess.check_output(['fdtget', tree.name, node, 'type'], text=True).strip()
                    if fs != 'ext4':
                        raise ValueError(f'{variant}/{model}: {partition} uses {fs}, expected ext4')
            config = (image_folder / (model + '.config')).read_text()
            symbols = (image_folder / (model + '.System.map')).read_text()
            version = f'4.9.337-DS-ACK-V1.12-{model}-{date}-F22R-v3.4.2{suffix}'
            require(version.encode() + b'\0' in image, (variant, model, 'uname'))
            require(len(version) <= 64, 'uname too long')
            require(image[56:60] == b'ARM\x64', (variant, model, 'arm64 header'))
            for flag in ('CONFIG_KSU=y', 'CONFIG_KSU_MANUAL_HOOK=y', 'CONFIG_SECURITY_SELINUX=y'):
                require(flag in config.splitlines(), (variant, model, flag))
            require('CONFIG_ALWAYS_PERMISSIVE=y' not in config, 'permissive kernel')
            enabled = 'CONFIG_ONEUI7_WORKAROUND=y' in config.splitlines()
            require(enabled == (variant == 'OneUI7'), 'OneUI7 configuration')
            require((' get_fixed_brightness\n' in symbols) == enabled, 'brightness symbol')
            require(b'v3.4.2' in image, 'driver version string')
            command_file = image_folder / (model + '.ksu-command.txt')
            command = command_file.read_text()
            require(re.search(r'-DKSU_VERSION=33355(?![0-9])', command), 'driver version code')
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
        archive = staging / (name + '.zip')
        with ZipFile(archive, 'w', ZIP_DEFLATED) as package:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    rel = path.relative_to(stage).as_posix()
                    entry = ZipInfo(rel)
                    entry.external_attr = 0o100755 << 16
                    package.writestr(entry, path.read_bytes(), compress_type=ZIP_DEFLATED)
        with ZipFile(archive) as package, ZipFile(source_zip) as original:
            require(package.testzip() is None, 'ZIP CRC')
            for tool in ('busybox', 'magiskboot', 'bsdiff'):
                rel = 'floyd/tools/' + tool
                require(package.read(rel) == original.read(rel), ('original tool changed', tool))
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
                    require(sha(data) == expected, (variant, model, ext, 'delta reconstruction'))
                    # Neither variant changes device trees from its exact upstream ZIP.
                    original_data = original.read(f'floyd/{model}-{ext}')
                    if ext == 'dtb':
                        if model != 'G960F':
                            (stage / 'original-base').write_bytes(original.read('floyd/G960F-dtb'))
                            (stage / 'original-patch').write_bytes(original_data)
                            subprocess.run(['bspatch', str(stage / 'original-base'), str(stage / 'original-dtb'),
                                            str(stage / 'original-patch')], check=True)
                            original_data = (stage / 'original-dtb').read_bytes()
                        require(original_data == data, (variant, model, 'DTB differs from upstream'))
            require('Unofficial F22R' in package.read(paths[2]).decode(), 'installer attribution')
        record = {'file': archive.name, 'sha256': sha(archive.read_bytes()),
                            'bytes': archive.stat().st_size, 'models': records}
        print('VERIFIED', variant, archive.name, record['sha256'], flush=True)
        return record

with tempfile.TemporaryDirectory(prefix='.verify-', dir=out) as tmp:
    staging = Path(tmp)
    reports = {variant: package_variant(variant, staging) for variant in ('regular', 'OneUI7')}
    for model in models:
        require(reports['regular']['models'][model]['Image_sha256'] !=
                reports['OneUI7']['models'][model]['Image_sha256'], (model, 'identical variant images'))
    (staging / 'verification.json').write_text(json.dumps(reports, indent=2))
    for name in [reports['regular']['file'], reports['OneUI7']['file'], 'verification.json']:
        (staging / name).replace(out / name)
print('PASS: 12 kernels, 12 DTBs, Enforcing, legacy KSU, OneUI7 separation and original tools verified.')
