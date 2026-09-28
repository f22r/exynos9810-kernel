#!/usr/bin/env python3
"""Check R2 fails and R3 passes Linux 4.9 API type checks after a kernel build."""
import argparse
import io
import pathlib
import shlex
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("kernel_root", type=pathlib.Path)
parser.add_argument("--compiler", default="clang")
args = parser.parse_args()
root = args.kernel_root.resolve()
sources = ("manager/apk_sign", "manager/throne_tracker",
           "runtime/ksud_integration", "policy/allowlist")
patches = ("kernelsu-next-legacy-4.9.patch",
           "kernelsu-next-legacy-manager-discovery.patch",
           "kernelsu-next-legacy-read-compat.patch",
           "kernelsu-next-legacy-execve-compat.patch")


def check(stage, checkout):
    results = []
    for source in sources:
        name = pathlib.Path(source)
        command_file = root / "KernelSU-Next/kernel" / name.parent / ("." + name.name + ".o.cmd")
        command = shlex.split(command_file.read_text().splitlines()[0].split(" := ", 1)[1])
        command[0] = args.compiler
        output = command.index("-o")
        del command[output:output + 2]
        command.remove("-c")
        command = [arg for arg in command if not arg.startswith("-Wp,-MD,")]
        command[-1] = str(checkout / "kernel" / (source + ".c"))
        command += ["-fsyntax-only", "-Werror=int-conversion"]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        results.append(result)
        print(f"{stage}: {source}: exit {result.returncode}")
        if result.returncode:
            print(result.stderr)
    return results


with tempfile.TemporaryDirectory(prefix="f22r-api-check-") as directory:
    checkout = pathlib.Path(directory)
    archive = subprocess.check_output(["git", "-C", str(root / "KernelSU-Next"),
                                       "archive", "HEAD"])
    with tarfile.open(fileobj=io.BytesIO(archive)) as source_archive:
        source_archive.extractall(checkout, filter="data")
    for index, patch in enumerate(patches):
        subprocess.run(["git", "apply", "--check", str(root / "patches" / patch)],
                       cwd=checkout, check=True)
        subprocess.run(["git", "apply", str(root / "patches" / patch)],
                       cwd=checkout, check=True)
        if index == 1:
            before = check("R2", checkout)
    after = check("R3", checkout)
    # Each R2 reader must fail for the actual kernel_read argument mismatch.
    assert all(result.returncode and "kernel_read" in result.stderr for result in before), \
        "R2 did not reproduce the expected kernel_read incompatibility"
    assert all(result.returncode == 0 for result in after), "R3 API checks failed"
    print("PASS: patches apply to pinned source; R2 fails and R3 passes all four API checks.")
