#!/usr/bin/env python3
"""
CamView Standalone Executable Builder.

Automates building standalone executable bundles for Linux, Windows, and macOS
using PyInstaller.

Usage:
    python build.py [--onefile | --onedir] [--debug] [--clean] [--name NAME]
"""

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent


def clean_build_artifacts(root: Path):
    """Remove previous build and dist directories."""
    print("🧹 Cleaning previous build artifacts...")
    for folder_name in ["build", "dist"]:
        folder = root / folder_name
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            print(f"   Removed {folder}")


def build_executable(
    onefile: bool = True,
    debug: bool = False,
    app_name: str = "CamView",
    clean: bool = True,
) -> int:
    """Execute PyInstaller build process with cross-platform configuration."""
    root = get_project_root()
    system = platform.system().lower()

    if clean:
        clean_build_artifacts(root)

    print(f"🚀 Building {app_name} for {platform.system()} ({platform.machine()})...")
    print(f"   Mode: {'Single File (--onefile)' if onefile else 'Directory (--onedir)'}")
    print(f"   Console: {'Enabled (Debug)' if debug else 'Disabled (GUI Mode)'}")

    # Verify PyInstaller is installed
    try:
        import PyInstaller.__main__
    except ImportError:
        print("\n❌ Error: PyInstaller is not installed!")
        print("   Please install it with:")
        print("       uv sync --all-extras")
        print("   or:")
        print("       uv pip install pyinstaller")
        return 1

    # Base arguments
    args = [
        str(root / "main.py"),
        f"--name={app_name}",
        "--noconfirm",
    ]

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    if debug:
        args.append("--console")
    else:
        args.append("--noconsole")

    # Add assets data folder
    assets_src = root / "src" / "assets"
    if assets_src.exists():
        separator = ";" if system == "windows" else ":"
        args.append(f"--add-data={assets_src}{separator}src/assets")

    # Add platform specific icon if present
    if system == "windows":
        ico = assets_src / "icon.ico"
        if ico.exists():
            args.append(f"--icon={ico}")
    elif system == "darwin":
        icns = assets_src / "icon.icns"
        if icns.exists():
            args.append(f"--icon={icns}")

    # Hidden imports required by dynamic PySide6 and OpenCV DNN features
    hidden_imports = [
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "cv2",
        "numpy",
        "sqlite3",
        "urllib.request",
        "json",
        "dataclasses",
        "threading",
        "queue",
        "src.core.connection",
        "src.core.stream_worker",
        "src.core.ai_detector",
        "src.core.event_db",
        "src.core.config_store",
        "src.core.resource_path",
        "src.styles.theme",
        "src.views.login_window",
        "src.views.viewer_window",
        "src.views.settings_dialog",
        "src.views.events_window",
    ]
    for imp in hidden_imports:
        args.append(f"--hidden-import={imp}")

    # Exclude unused heavy packages
    excludes = [
        "tkinter",
        "matplotlib",
        "scipy",
        "torch",
        "torchvision",
        "IPython",
        "unittest",
        "pytest",
    ]
    for exc in excludes:
        args.append(f"--exclude-module={exc}")

    # Execute PyInstaller
    print("\n📦 Running PyInstaller...")
    try:
        PyInstaller.__main__.run(args)
    except Exception as e:
        print(f"\n❌ Build failed with exception: {e}")
        return 1

    # Post-build summary
    dist_dir = root / "dist"
    print("\n" + "=" * 60)
    print("🎉 BUILD SUCCESSFUL!")
    print("=" * 60)

    if system == "windows":
        out_target = dist_dir / (f"{app_name}.exe" if onefile else app_name)
    elif system == "darwin":
        out_target = dist_dir / (f"{app_name}.app" if not onefile else app_name)
    else:
        out_target = dist_dir / app_name

    print(f"\n📁 Executable location:\n   {out_target}")

    if out_target.exists():
        if out_target.is_file():
            size_mb = out_target.stat().st_size / (1024 * 1024)
            print(f"   File size: {size_mb:.2f} MB")
            # Ensure executable permission on Unix
            if system != "windows":
                out_target.chmod(0o755)

        print("\n🚀 To run the executable:")
        if system == "windows":
            print(f"   .\\dist\\{app_name}.exe")
        elif system == "darwin":
            print(f"   open dist/{app_name}.app  # or ./dist/{app_name}")
        else:
            print(f"   ./dist/{app_name}")

    print("=" * 60 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="CamView Standalone Executable Builder")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--onefile",
        action="store_true",
        default=True,
        help="Create a single-file standalone executable (default)",
    )
    group.add_argument(
        "--onedir",
        action="store_true",
        help="Create a standalone distribution folder containing executable and libraries",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Keep terminal console attached for logging and debugging",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not clean build/ and dist/ folders before building",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="CamView",
        help="Name of the resulting executable (default: CamView)",
    )

    args = parser.parse_args()
    onefile_mode = not args.onedir

    sys.exit(
        build_executable(
            onefile=onefile_mode,
            debug=args.debug,
            app_name=args.name,
            clean=not args.no_clean,
        )
    )


if __name__ == "__main__":
    main()
