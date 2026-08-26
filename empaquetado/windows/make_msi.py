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

"""Generador del instalador Zonda.msi usando WiX Toolset para Windows."""

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))
from empaquetado.version import obtener_version

VERSION = obtener_version()
PACKAGING_DIR = RAIZ / "empaquetado"
DIST_DIR = RAIZ / "dist"
MSI_OUTPUT = DIST_DIR / f"Zonda-{VERSION}.msi"
WXS_TEMPLATE = PACKAGING_DIR / "windows" / "zonda.wxs"


def construir_msi() -> Path:
    """Genera el instalador .msi utilizando WiX (wix.exe o candle + light)."""
    print(f"=== Generando instalador Windows {MSI_OUTPUT.name} ===")

    # 1. Asegurar bundle base
    cmd_bundle = [sys.executable, str(PACKAGING_DIR / "build_bundle.py"), "--target", "windows"]
    subprocess.run(cmd_bundle, check=True)

    bundle_dir = DIST_DIR / "bundle"

    # 2. Buscar herramientas de WiX Toolset
    wix_exe = shutil.which("wix")
    candle_exe = shutil.which("candle")
    light_exe = shutil.which("light")

    if wix_exe:
        # WiX v4 / v5
        cmd = [
            wix_exe,
            "build",
            str(WXS_TEMPLATE),
            "-d",
            f"SourceDir={bundle_dir}",
            "-d",
            f"Version={VERSION}",
            "-o",
            str(MSI_OUTPUT),
        ]
        print(f"Compilando MSI con WiX v4/v5: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    elif candle_exe and light_exe:
        # WiX v3 clásico
        wixobj = DIST_DIR / "zonda.wixobj"
        cmd_candle = [
            candle_exe,
            str(WXS_TEMPLATE),
            f"-dSourceDir={bundle_dir}",
            f"-dVersion={VERSION}",
            "-o",
            str(wixobj),
        ]
        cmd_light = [
            light_exe,
            str(wixobj),
            "-ext",
            "WixUIExtension",
            "-o",
            str(MSI_OUTPUT),
        ]
        subprocess.run(cmd_candle, check=True)
        subprocess.run(cmd_light, check=True)
        if wixobj.exists():
            wixobj.unlink()
    else:
        print(
            "Aviso: No se encontró WiX Toolset (wix.exe o candle/light) en PATH.\n"
            "El archivo .wxs y el bundle están listos en dist/bundle para ser compilados en Windows/CI.",
            file=sys.stderr,
        )
        return MSI_OUTPUT

    print(f"\n✓ ¡Instalador Windows generado exitosamente en: {MSI_OUTPUT}!")
    return MSI_OUTPUT


def main() -> None:
    construir_msi()


if __name__ == "__main__":
    main()
