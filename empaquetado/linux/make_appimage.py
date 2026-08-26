# Copyright (c) 2023-2026, Eduardo Di Loreto <efdiloreto@gmail.com>
#
# This file is part of Zonda.
#
# Zonda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Zonda is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Zonda.  If not, see <https://www.gnu.org/licenses/>.

"""Generador del paquete portátil Zonda.AppImage para distribuciones Linux."""

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
PACKAGING_DIR = RAIZ / "empaquetado"
DIST_DIR = RAIZ / "dist"
sys.path.insert(0, str(RAIZ))
from empaquetado.version import obtener_version

VERSION = obtener_version()
APPIMAGE_OUTPUT = DIST_DIR / f"Zonda-{VERSION}-x86_64.AppImage"
APPIMAGETOOL_URL = "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"


def preparar_appdir() -> Path:
    """Construye la estructura estándar de AppDir para AppImage."""
    print("=== Preparando AppDir para Linux ===")

    # 1. Asegurar bundle base
    cmd_bundle = [sys.executable, str(PACKAGING_DIR / "build_bundle.py"), "--target", "linux"]
    subprocess.run(cmd_bundle, check=True)

    bundle_src = DIST_DIR / "bundle"

    if APP_DIR.exists():
        shutil.rmtree(APP_DIR)

    usr_bin = APP_DIR / "usr" / "bin"
    usr_share_icons = APP_DIR / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    usr_share_mime = APP_DIR / "usr" / "share" / "mime" / "packages"

    usr_bin.mkdir(parents=True, exist_ok=True)
    usr_share_icons.mkdir(parents=True, exist_ok=True)
    usr_share_mime.mkdir(parents=True, exist_ok=True)

    # 2. Copiar archivos de escritorio e iconos
    shutil.copy2(PACKAGING_DIR / "linux" / "zonda.desktop", APP_DIR / "zonda.desktop")
    shutil.copy2(PACKAGING_DIR / "linux" / "zonda.xml", usr_share_mime / "zonda.xml")

    ico_path = RAIZ / "python" / "zonda" / "recursos" / "iconos" / "zonda.ico"
    png_salida = APP_DIR / "zonda.png"
    if ico_path.exists():
        try:
            from PIL import Image
            img = Image.open(ico_path)
            img.save(png_salida, format="PNG")
            shutil.copy2(png_salida, usr_share_icons / "zonda.png")
        except Exception:
            logo_png = RAIZ / "python" / "zonda" / "recursos" / "imagenes" / "logo.png"
            if logo_png.exists():
                shutil.copy2(logo_png, png_salida)
                shutil.copy2(logo_png, usr_share_icons / "zonda.png")

    # 3. Copiar lanzador y estructura de Zonda
    shutil.copy2(bundle_src / "zonda", usr_bin / "zonda")
    os.chmod(usr_bin / "zonda", 0o755)

    shutil.copytree(bundle_src / "app", APP_DIR / "usr" / "app", dirs_exist_ok=True)
    shutil.copytree(bundle_src / "python", APP_DIR / "usr" / "python", dirs_exist_ok=True, symlinks=True)
    if (bundle_src / "tools").exists():
        shutil.copytree(bundle_src / "tools", APP_DIR / "usr" / "tools", dirs_exist_ok=True)

    # 4. Script AppRun de inicio del AppImage
    apprun_path = APP_DIR / "AppRun"
    apprun_content = """#!/bin/sh
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${HERE}/usr/tools/pandoc:${PATH}"
export PYTHONPATH="${HERE}/usr/app:${PYTHONPATH}"
exec "${HERE}/usr/bin/zonda" "$@"
"""
    apprun_path.write_text(apprun_content, encoding="utf-8")
    os.chmod(apprun_path, 0o755)

    print(f"✓ AppDir preparado en: {APP_DIR}")
    return APP_DIR


def generar_appimage(appdir: Path) -> Path:
    """Invoca appimagetool para generar el archivo AppImage final."""
    print("=== Generando archivo AppImage ===")
    appimagetool = shutil.which("appimagetool")

    if not appimagetool:
        tool_local = DIST_DIR / "appimagetool"
        if not tool_local.exists():
            print("Descargando appimagetool...")
            urllib.request.urlretrieve(APPIMAGETOOL_URL, str(tool_local))
            os.chmod(tool_local, 0o755)
        appimagetool = str(tool_local)

    cmd = [appimagetool, str(appdir), str(APPIMAGE_OUTPUT)]
    subprocess.run(cmd, check=True, env={**os.environ, "ARCH": "x86_64"})

    print(f"\n✓ ¡Paquete AppImage generado exitosamente en: {APPIMAGE_OUTPUT}!")
    return APPIMAGE_OUTPUT


def main() -> None:
    if sys.platform != "linux":
        print("Este script está pensado para ejecutarse en Linux (o CI de Linux).", file=sys.stderr)

    appdir = preparar_appdir()
    try:
        generar_appimage(appdir)
    except Exception as e:
        print(f"Aviso al compilar AppImage (requiere Linux + FUSE): {e}")


if __name__ == "__main__":
    main()
