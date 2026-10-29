"""
build_exe.py — Standalone Executable Builder (harErp.exe) via PyInstaller
=========================================================================
Usage:
    pip install pyinstaller
    python build_exe.py
"""

import subprocess
import sys


def build_executable():
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "harErp",
        "main.py",
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("\n✔ Executable built successfully in dist/harErp!")


gerar_executavel = build_executable


if __name__ == "__main__":
    build_executable()
