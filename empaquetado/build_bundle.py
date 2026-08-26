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

"""Script central para armar la estructura de distribución (bundle) de Zonda.

Copia el código fuente de la aplicación, compila el lanzador nativo,
prepara el runtime de Python y organiza la carpeta 'dist/' para que los
empaquetadores (WiX para MSI, make_dmg para DMG, AppImage para Linux)
puedan generar el instalador final.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PYTHON_DIR = RAIZ / "python"
LAUNCHER_DIR = RAIZ / "launcher"
DIST_DIR = RAIZ / "dist" / "bundle"
CACHE_DIR = RAIZ / "dist" / "cache"

# Zonda exporta los reportes con pandoc, que no es una dependencia de Python: es
# un ejecutable aparte. Si no viaja adentro del instalador, el usuario tiene que
# instalarlo a mano o la exportación falla, así que se descarga acá y el
# lanzador lo pone en el PATH desde tools/pandoc.
PANDOC_VERSION = "3.10.2"
PANDOC_BASE_URL = f"https://github.com/jgm/pandoc/releases/download/{PANDOC_VERSION}"
# Sólo el .zip de Windows trae el COPYRIGHT adentro; para las otras plataformas
# se baja del repositorio, porque distribuir el binario obliga a acompañarlo.
PANDOC_COPYRIGHT_URL = (
    f"https://raw.githubusercontent.com/jgm/pandoc/{PANDOC_VERSION}/COPYRIGHT"
)


def compilar_lanzador(target_os: str) -> Path:
    """Invoca launcher/build.py para asegurar que el binario del lanzador esté compilado."""
    print("=== [1/4] Compilando el lanzador nativo ===")
    cmd = [sys.executable, str(LAUNCHER_DIR / "build.py"), "--target", target_os]
    subprocess.run(cmd, check=True, cwd=str(RAIZ))

    if target_os == "windows":
        binario = LAUNCHER_DIR / "bin" / "Zonda.exe"
    else:
        binario = LAUNCHER_DIR / "bin" / "zonda"

    if not binario.exists():
        raise FileNotFoundError(f"No se encontró el binario compilado en {binario}")

    return binario


def copiar_codigo_fuente(destino_app: Path) -> None:
    """Copia el paquete zonda/ a la carpeta de distribución."""
    print(f"=== [2/4] Copiando código de Zonda a {destino_app} ===")
    origen_zonda = PYTHON_DIR / "zonda"
    destino_zonda = destino_app / "zonda"

    if destino_zonda.exists():
        shutil.rmtree(destino_zonda)

    shutil.copytree(
        origen_zonda,
        destino_zonda,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
    )


def preparar_runtime_python(destino_python: Path, target_os: str) -> None:
    """Prepara el entorno de Python dentro de la distribución."""
    print(f"=== [3/4] Preparando entorno de Python en {destino_python} ===")
    sistema_actual = "macos" if platform.system().lower() == "darwin" else ("windows" if platform.system().lower() == "windows" else "linux")

    if target_os == sistema_actual:
        # Crear un venv completo en destino_python usando uv
        print(f"Creando entorno Python 3.13 en {destino_python}...")
        if destino_python.exists():
            shutil.rmtree(destino_python)
        
        subprocess.run(["uv", "venv", str(destino_python), "--python", "3.13"], check=True)
        
        py_exe = destino_python / "Scripts" / "python.exe" if target_os == "windows" else destino_python / "bin" / "python3"
        print(f"Instalando dependencias de Zonda en {py_exe}...")
        subprocess.run(["uv", "pip", "install", str(PYTHON_DIR), "--python", str(py_exe)], check=True)
    else:
        print(
            "Nota: Compilando para un OS diferente al actual.\n"
            "Instalando dependencias usando uv target..."
        )
        destino_python.mkdir(parents=True, exist_ok=True)
        target_dir = destino_python / "Lib" / "site-packages" if target_os == "windows" else destino_python / "lib"
        subprocess.run(["uv", "pip", "install", "--target", str(target_dir), str(PYTHON_DIR)], check=True)


def _arquitectura_pandoc(target_os: str) -> str:
    """Devuelve la arquitectura con la que pandoc nombra sus archivos.

    Args:
        target_os: El sistema operativo destino.

    Returns: El nombre de la arquitectura tal como aparece en el release.
    """
    if target_os == "windows":
        # pandoc sólo publica x86_64 para Windows.
        return "x86_64"

    maquina = platform.machine().lower()
    es_arm = maquina in ("arm64", "aarch64")
    if target_os == "macos":
        return "arm64" if es_arm else "x86_64"
    return "arm64" if es_arm else "amd64"


def _archivo_pandoc(target_os: str) -> tuple[str, str]:
    """Arma el nombre del archivo publicado y el del ejecutable adentro.

    Args:
        target_os: El sistema operativo destino.

    Returns: El nombre del archivo a descargar y el del binario de pandoc.
    """
    arq = _arquitectura_pandoc(target_os)
    if target_os == "windows":
        return f"pandoc-{PANDOC_VERSION}-windows-{arq}.zip", "pandoc.exe"
    if target_os == "macos":
        return f"pandoc-{PANDOC_VERSION}-{arq}-macOS.zip", "pandoc"
    return f"pandoc-{PANDOC_VERSION}-linux-{arq}.tar.gz", "pandoc"


def _descargar(url: str, destino: Path) -> Path:
    """Descarga un archivo si no está ya en la cache.

    Args:
        url: La dirección de donde se descarga.
        destino: El archivo donde se guarda.

    Returns: El archivo descargado.
    """
    if destino.exists():
        print(f"Usando la copia en cache: {destino}")
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando {url}")
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    with urllib.request.urlopen(url) as respuesta, open(parcial, "wb") as archivo:
        shutil.copyfileobj(respuesta, archivo)
    parcial.replace(destino)
    return destino


def _extraer_pandoc(comprimido: Path, nombre_binario: str, destino: Path) -> None:
    """Saca del archivo comprimido el binario de pandoc y su licencia.

    Args:
        comprimido: El .zip o .tar.gz descargado.
        nombre_binario: El nombre del ejecutable de pandoc.
        destino: La carpeta tools/pandoc del bundle.
    """
    # Del release sólo interesan dos archivos: el ejecutable y el COPYRIGHT,
    # que la GPL obliga a distribuir junto con el binario.
    def es_binario(nombre: str) -> bool:
        return Path(nombre).name == nombre_binario

    def es_copyright(nombre: str) -> bool:
        return Path(nombre).name.upper().startswith("COPYRIGHT")

    if comprimido.suffix == ".zip":
        with zipfile.ZipFile(comprimido) as zf:
            miembros = zf.namelist()
            for nombre in miembros:
                if es_binario(nombre) or es_copyright(nombre):
                    with zf.open(nombre) as origen:
                        (destino / Path(nombre).name).write_bytes(origen.read())
    else:
        with tarfile.open(comprimido) as tf:
            for miembro in tf.getmembers():
                if not miembro.isfile():
                    continue
                if es_binario(miembro.name) or es_copyright(miembro.name):
                    extraido = tf.extractfile(miembro)
                    if extraido is not None:
                        (destino / Path(miembro.name).name).write_bytes(extraido.read())

    binario = destino / nombre_binario
    if not binario.exists():
        raise FileNotFoundError(
            f"No se encontró {nombre_binario} dentro de {comprimido.name}"
        )
    if nombre_binario != "pandoc.exe":
        os.chmod(binario, 0o755)


def preparar_pandoc(tools_dir: Path, target_os: str) -> None:
    """Deja el ejecutable de pandoc dentro del bundle.

    Args:
        tools_dir: La carpeta tools/pandoc del bundle.
        target_os: El sistema operativo destino.
    """
    print(f"=== Preparando pandoc {PANDOC_VERSION} en {tools_dir} ===")
    nombre_archivo, nombre_binario = _archivo_pandoc(target_os)

    if (tools_dir / nombre_binario).exists():
        print("pandoc ya estaba en el bundle.")
        return

    comprimido = _descargar(
        f"{PANDOC_BASE_URL}/{nombre_archivo}", CACHE_DIR / nombre_archivo
    )
    _extraer_pandoc(comprimido, nombre_binario, tools_dir)

    copyright_destino = tools_dir / "COPYRIGHT.txt"
    if not copyright_destino.exists():
        _descargar(PANDOC_COPYRIGHT_URL, CACHE_DIR / "pandoc-COPYRIGHT.txt")
        shutil.copy2(CACHE_DIR / "pandoc-COPYRIGHT.txt", copyright_destino)

    tamaño = (tools_dir / nombre_binario).stat().st_size / 1024 / 1024
    print(f"✓ pandoc listo: {tools_dir / nombre_binario} ({tamaño:.0f} MB)")


def armar_bundle(target_os: str, con_pandoc: bool = True) -> Path:
    """Ensambla todos los componentes en dist/bundle/."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Compilar lanzador
    binario_lanzador = compilar_lanzador(target_os)

    # 2. Limpiar y recrear estructura de carpetas
    app_dir = DIST_DIR / "app"
    python_dir = DIST_DIR / "python"
    tools_dir = DIST_DIR / "tools" / "pandoc"

    app_dir.mkdir(parents=True, exist_ok=True)
    python_dir.mkdir(parents=True, exist_ok=True)
    tools_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copiar lanzador al directorio raíz del bundle
    dest_lanzador = DIST_DIR / binario_lanzador.name
    shutil.copy2(binario_lanzador, dest_lanzador)
    if target_os != "windows":
        os.chmod(dest_lanzador, 0o755)

    # 4. Copiar código de la app
    copiar_codigo_fuente(app_dir)

    # 5. Preparar entorno Python
    preparar_runtime_python(python_dir, target_os)

    # 6. Bajar pandoc, que es lo que exporta los reportes
    if con_pandoc:
        preparar_pandoc(tools_dir, target_os)
    else:
        print(
            "Aviso: se saltea pandoc. El instalador no va a poder exportar\n"
            "reportes salvo que el usuario lo tenga instalado en el sistema.",
            file=sys.stderr,
        )

    # 7. Copiar icono de Zonda
    shutil.copy2(LAUNCHER_DIR / "src" / "zonda.ico", DIST_DIR / "zonda.ico")

    print("\n=== [4/4] ¡Bundle generado exitosamente! ===")
    print(f"Ubicación: {DIST_DIR}")
    return DIST_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Armar el bundle de distribución de Zonda.")
    parser.add_argument(
        "--target",
        choices=["auto", "windows", "macos", "linux"],
        default="auto",
        help="Sistema operativo destino (default: auto)",
    )
    parser.add_argument(
        "--sin-pandoc",
        action="store_true",
        help="No incluir pandoc en el bundle (los reportes no se van a poder exportar)",
    )
    args = parser.parse_args()

    sistema_actual = platform.system().lower()
    target = args.target
    if target == "auto":
        target = "macos" if sistema_actual == "darwin" else ("windows" if sistema_actual == "windows" else "linux")

    armar_bundle(target, con_pandoc=not args.sin_pandoc)


if __name__ == "__main__":
    main()
