# Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>
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

"""Generador del bundle Zonda.app y del archivo instalador Zonda.dmg para macOS."""

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
PACKAGING_DIR = RAIZ / "empaquetado"
DIST_DIR = RAIZ / "dist"
APP_BUNDLE = DIST_DIR / "Zonda.app"

sys.path.insert(0, str(RAIZ))
from empaquetado.version import obtener_version

VERSION = obtener_version()
DMG_FILE = DIST_DIR / f"Zonda-{VERSION}.dmg"


def generar_icns(destino_icns: Path) -> None:
    """Genera el archivo zonda.icns a partir del isotipo en zonda.ico usando sips e iconutil."""
    ico_path = RAIZ / "python" / "zonda" / "recursos" / "iconos" / "zonda.ico"
    if not ico_path.exists():
        print(f"Aviso: No se encontró {ico_path}, omitiendo generación de .icns")
        return

    iconset_dir = DIST_DIR / "zonda.iconset"
    iconset_dir.mkdir(parents=True, exist_ok=True)

    # Extraer imagen base PNG desde zonda.ico
    base_png = DIST_DIR / "zonda_base.png"
    subprocess.run(
        ["sips", "-s", "format", "png", str(ico_path), "--out", str(base_png)],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    tamanos = [16, 32, 64, 128, 256, 512]
    for t in tamanos:
        subprocess.run(
            [
                "sips",
                "-z",
                str(t),
                str(t),
                str(base_png),
                "--out",
                str(iconset_dir / f"icon_{t}x{t}.png"),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "sips",
                "-z",
                str(t * 2),
                str(t * 2),
                str(base_png),
                "--out",
                str(iconset_dir / f"icon_{t}x{t}@2x.png"),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    subprocess.run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(destino_icns)], check=True)
    shutil.rmtree(iconset_dir)
    if base_png.exists():
        base_png.unlink()
    print(f"✓ Ícono generado desde isotipo: {destino_icns}")


def escribir_info_plist(destino: Path) -> None:
    """Copia el Info.plist completando los campos de version.

    Se hace acá y no a mano en la plantilla para que la version que muestra
    macOS en el Finder y en "Acerca de" no pueda quedar vieja: sale siempre de
    ``__version__``, igual que el nombre del .dmg.

    Args:
        destino: El Info.plist a escribir dentro del bundle.
    """
    plantilla = PACKAGING_DIR / "macos" / "Info.plist"
    with open(plantilla, "rb") as archivo:
        datos = plistlib.load(archivo)

    datos["CFBundleShortVersionString"] = VERSION
    datos["CFBundleVersion"] = VERSION

    with open(destino, "wb") as archivo:
        plistlib.dump(datos, archivo)


def construir_app_bundle() -> Path:
    """Construye la estructura estándar Zonda.app/Contents/..."""
    print("=== Construyendo Zonda.app ===")

    # 1. Asegurar que el bundle base exista
    cmd_bundle = [sys.executable, str(PACKAGING_DIR / "build_bundle.py"), "--target", "macos"]
    subprocess.run(cmd_bundle, check=True)

    bundle_src = DIST_DIR / "bundle"

    if APP_BUNDLE.exists():
        shutil.rmtree(APP_BUNDLE)

    contents_dir = APP_BUNDLE / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"

    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copiar Info.plist con la version del proyecto ya escrita
    escribir_info_plist(contents_dir / "Info.plist")

    # 3. Copiar lanzador binario a Contents/MacOS/zonda
    lanzador_src = bundle_src / "zonda"
    lanzador_dest = macos_dir / "zonda"
    shutil.copy2(lanzador_src, lanzador_dest)
    os.chmod(lanzador_dest, 0o755)

    # 4. Copiar Python, App y Tools a Contents/Resources/
    shutil.copytree(bundle_src / "app", resources_dir / "app", dirs_exist_ok=True)
    shutil.copytree(bundle_src / "python", resources_dir / "python", dirs_exist_ok=True, symlinks=True)
    if (bundle_src / "tools").exists():
        shutil.copytree(bundle_src / "tools", resources_dir / "tools", dirs_exist_ok=True)

    # 5. Generar y copiar icono .icns
    generar_icns(resources_dir / "zonda.icns")

    print(f"✓ Zonda.app construido en: {APP_BUNDLE}")
    return APP_BUNDLE


def crear_dmg(app_bundle: Path) -> Path:
    """Genera la imagen .dmg usando hdiutil de macOS con enlace a /Applications."""
    print("=== Creando imagen de disco Zonda.dmg ===")

    dmg_temp_dir = DIST_DIR / "dmg_root"
    if dmg_temp_dir.exists():
        shutil.rmtree(dmg_temp_dir)
    dmg_temp_dir.mkdir(parents=True, exist_ok=True)

    # Copiar Zonda.app a la raíz del DMG
    shutil.copytree(app_bundle, dmg_temp_dir / "Zonda.app", symlinks=True)

    # Crear symlink a /Applications
    applications_symlink = dmg_temp_dir / "Applications"
    os.symlink("/Applications", str(applications_symlink))

    if DMG_FILE.exists():
        DMG_FILE.unlink()

    cmd = [
        "hdiutil",
        "create",
        "-volname",
        "Zonda",
        "-srcfolder",
        str(dmg_temp_dir),
        "-ov",
        "-format",
        "UDZO",
        str(DMG_FILE),
    ]
    subprocess.run(cmd, check=True)

    shutil.rmtree(dmg_temp_dir)
    print(f"\n✓ ¡Instalador macOS generado exitosamente en: {DMG_FILE}!")
    return DMG_FILE


def main() -> None:
    if sys.platform != "darwin":
        print("Este script debe ejecutarse en macOS.", file=sys.stderr)
        sys.exit(1)

    app = construir_app_bundle()
    crear_dmg(app)


if __name__ == "__main__":
    main()
