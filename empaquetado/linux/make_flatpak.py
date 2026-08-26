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

"""Generador del bundle Zonda.flatpak para distribuciones Linux."""

import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))
from empaquetado.version import obtener_version

APP_ID = "io.github.efdiloreto.ZondaPro"
VERSION = obtener_version()

PACKAGING_DIR = RAIZ / "empaquetado"
LINUX_DIR = PACKAGING_DIR / "linux"
DIST_DIR = RAIZ / "dist"

MANIFIESTO = LINUX_DIR / f"{APP_ID}.yml"
METAINFO = LINUX_DIR / f"{APP_ID}.metainfo.xml"
ICONO_ICO = RAIZ / "python" / "zonda" / "recursos" / "iconos" / "zonda.ico"

ICONO_PNG = DIST_DIR / f"{APP_ID}.png"
BUILD_DIR = DIST_DIR / "flatpak-build"
REPO_DIR = DIST_DIR / "flatpak-repo"
FLATPAK_OUTPUT = DIST_DIR / f"Zonda-{VERSION}.flatpak"


def extraer_icono(destino: Path) -> Path:
    """Saca del .ico la imagen mas grande, que ya viene codificada como PNG.

    Un .ico multi-resolucion guarda las entradas chicas como BMP pero la de
    256x256 como PNG, asi que alcanza con copiar esos bytes tal cual y no hace
    falta ninguna libreria de imagenes.

    Args:
        destino: El archivo .png a escribir.

    Returns: El archivo escrito.
    """
    datos = ICONO_ICO.read_bytes()
    _, _, cantidad = struct.unpack("<HHH", datos[:6])

    mejor: tuple[int, int, int] | None = None
    for indice in range(cantidad):
        inicio = 6 + indice * 16
        ancho, _, _, _, _, _, tamanio, posicion = struct.unpack(
            "<BBBBHHII", datos[inicio : inicio + 16]
        )
        # En el formato ICO, 0 significa 256.
        ancho = ancho or 256
        if datos[posicion : posicion + 8] != b"\x89PNG\r\n\x1a\n":
            continue
        if mejor is None or ancho > mejor[0]:
            mejor = (ancho, posicion, tamanio)

    if mejor is None:
        raise ValueError(f"{ICONO_ICO} no tiene ninguna entrada en formato PNG")

    ancho, posicion, tamanio = mejor
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos[posicion : posicion + tamanio])
    print(f"✓ Icono de {ancho}x{ancho} extraido a {destino}")
    return destino


def verificar_metainfo() -> None:
    """Corta si el metainfo no declara una <release> para la version actual.

    Es la unica copia de la version que no se puede derivar sola, porque cada
    entrada lleva un changelog escrito por una persona. Corta en vez de avisar
    a proposito: si no, el Flatpak se publicaria mostrando el changelog de la
    version anterior y nadie se enteraria.
    """
    componente = ET.parse(METAINFO).getroot()
    versiones = [
        release.get("version")
        for release in componente.iterfind("releases/release")
        if release.get("version")
    ]
    if VERSION not in versiones:
        tiene = ", ".join(versiones) or "ninguna"
        print(
            f"Error: {METAINFO.name} no declara ninguna <release> para la "
            f"version {VERSION} (tiene {tiene}).",
            file=sys.stderr,
        )
        print(
            "Agregale la entrada que corresponde, con el changelog de lo que "
            "cambio, antes de empaquetar.",
            file=sys.stderr,
        )
        sys.exit(1)


def _runtime_del_manifiesto() -> tuple[str, str, str]:
    """Lee del manifiesto el runtime, el sdk y la branch que hay que tener.

    Returns: El runtime, el sdk y la version de branch.
    """
    texto = MANIFIESTO.read_text(encoding="utf-8")

    def buscar(clave: str) -> str:
        match = re.search(rf"^{clave}:\s*['\"]?([^'\"\s#]+)", texto, re.MULTILINE)
        if not match:
            raise ValueError(f"No se encontro '{clave}' en {MANIFIESTO}")
        return match.group(1)

    return buscar("runtime"), buscar("sdk"), buscar("runtime-version")


def verificar_runtime() -> None:
    """Corta con un mensaje claro si falta el runtime o el sdk de KDE."""
    runtime, sdk, branch = _runtime_del_manifiesto()
    faltantes = []
    for paquete in (f"{runtime}//{branch}", f"{sdk}//{branch}"):
        resultado = subprocess.run(
            ["flatpak", "info", paquete],
            capture_output=True,
            text=True,
        )
        if resultado.returncode != 0:
            faltantes.append(paquete)

    if faltantes:
        print(
            f"Error: falta instalar {' y '.join(faltantes)}.\n\n"
            f"    flatpak install -y flathub {' '.join(faltantes)}\n\n"
            "Si esa branch ya no existe, mira cuales hay con:\n\n"
            "    flatpak remote-ls flathub --runtime | grep org.kde.Platform\n\n"
            f"y actualiza 'runtime-version' en {MANIFIESTO.name}.",
            file=sys.stderr,
        )
        sys.exit(1)


def construir_flatpak() -> Path:
    """Arma el bundle de un solo archivo Zonda-<version>.flatpak."""
    print(f"=== Generando {FLATPAK_OUTPUT.name} ===")

    for herramienta in ("flatpak", "flatpak-builder"):
        if not shutil.which(herramienta):
            print(
                f"Error: no se encontro '{herramienta}' en el PATH.\n"
                "Instalalo con el gestor de paquetes de tu distribucion.",
                file=sys.stderr,
            )
            sys.exit(1)

    verificar_runtime()
    verificar_metainfo()

    # 1. Asegurar el bundle base. El lanzador nativo no se compila porque
    #    adentro del Flatpak lo reemplaza el wrapper zonda.sh.
    cmd_bundle = [
        sys.executable,
        str(PACKAGING_DIR / "build_bundle.py"),
        "--target",
        "linux",
        "--sin-lanzador",
    ]
    subprocess.run(cmd_bundle, check=True)

    # 2. Extraer el icono que el manifiesto espera en dist/.
    extraer_icono(ICONO_PNG)

    # 3. Compilar dentro de un repositorio OSTree temporal.
    cmd_builder = [
        "flatpak-builder",
        "--force-clean",
        "--disable-rofiles-fuse",
        "--repo",
        str(REPO_DIR),
        str(BUILD_DIR),
        str(MANIFIESTO),
    ]
    print(f"Compilando: {' '.join(cmd_builder)}")
    subprocess.run(cmd_builder, check=True)

    # 4. Exportar el repositorio a un unico archivo instalable.
    if FLATPAK_OUTPUT.exists():
        FLATPAK_OUTPUT.unlink()

    cmd_bundle_out = [
        "flatpak",
        "build-bundle",
        str(REPO_DIR),
        str(FLATPAK_OUTPUT),
        APP_ID,
    ]
    subprocess.run(cmd_bundle_out, check=True)

    print(f"\n✓ ¡Paquete Flatpak generado exitosamente en: {FLATPAK_OUTPUT}!")
    print(f"Se instala con: flatpak install --user {FLATPAK_OUTPUT.name}")
    return FLATPAK_OUTPUT


def main() -> None:
    if sys.platform != "linux":
        print(
            "Este script debe ejecutarse en Linux (o en el CI de Linux).",
            file=sys.stderr,
        )
        sys.exit(1)

    construir_flatpak()


if __name__ == "__main__":
    main()
