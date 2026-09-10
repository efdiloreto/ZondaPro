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
empaquetadores (WiX para MSI, make_dmg para DMG, Flatpak para Linux)
puedan generar el instalador final.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PYTHON_DIR = RAIZ / "python"
LAUNCHER_DIR = RAIZ / "launcher"
DIST_DIR = RAIZ / "dist" / "bundle"
CACHE_DIR = RAIZ / "dist" / "cache"

def compilar_lanzador(target_os: str) -> Path:
    """Invoca launcher/build.py para asegurar que el binario del lanzador esté compilado."""
    print("=== [1/3] Compilando el lanzador nativo ===")
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
    print(f"=== [2/3] Copiando código de Zonda a {destino_app} ===")
    origen_zonda = PYTHON_DIR / "zonda"
    destino_zonda = destino_app / "zonda"

    if destino_zonda.exists():
        shutil.rmtree(destino_zonda)

    shutil.copytree(
        origen_zonda,
        destino_zonda,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
    )


def _python_standalone() -> Path:
    """Consigue una distribución standalone de Python 3.13, relocalizable.

    Returns: La carpeta raíz del intérprete descargado por uv.
    """
    subprocess.run(["uv", "python", "install", "3.13", "--managed-python"], check=True)
    resultado = subprocess.run(
        ["uv", "python", "find", "3.13", "--managed-python"],
        check=True,
        capture_output=True,
        text=True,
    )
    ejecutable = Path(resultado.stdout.strip())
    # En Windows el intérprete está en la raíz de la distribución; en macOS y
    # Linux, adentro de bin/.
    if ejecutable.parent.name == "bin":
        return ejecutable.parent.parent
    return ejecutable.parent


def preparar_runtime_python(destino_python: Path, target_os: str) -> None:
    """Prepara el entorno de Python dentro de la distribución."""
    print(f"=== [3/3] Preparando entorno de Python en {destino_python} ===")
    sistema_actual = "macos" if platform.system().lower() == "darwin" else ("windows" if platform.system().lower() == "windows" else "linux")

    if target_os == sistema_actual:
        # Un venv no sirve para distribuir: no lleva ni el intérprete ni la
        # stdlib, sino que apunta con pyvenv.cfg al Python que lo creó, que en la
        # máquina del usuario no existe. Por eso se copia una distribución
        # standalone completa, que además deja el intérprete en su raíz, que es
        # donde el lanzador (launcher/src/main.c) lo busca.
        origen = _python_standalone()
        print(f"Copiando el runtime standalone desde {origen}...")
        if destino_python.exists():
            shutil.rmtree(destino_python)

        shutil.copytree(
            origen,
            destino_python,
            ignore=shutil.ignore_patterns(
                "BUILD", "include", "libs", "__pycache__", "EXTERNALLY-MANAGED"
            ),
        )

        py_exe = (
            destino_python / "python.exe"
            if target_os == "windows"
            else destino_python / "bin" / "python3"
        )
        print(f"Instalando dependencias de Zonda en {py_exe}...")
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                str(PYTHON_DIR),
                "--python",
                str(py_exe),
                # La distribución viene marcada como gestionada por uv; instalar
                # adentro es justamente lo que se busca acá.
                "--break-system-packages",
            ],
            check=True,
        )
    else:
        print(
            "Nota: Compilando para un OS diferente al actual.\n"
            "Instalando dependencias usando uv target..."
        )
        destino_python.mkdir(parents=True, exist_ok=True)
        target_dir = destino_python / "Lib" / "site-packages" if target_os == "windows" else destino_python / "lib"
        subprocess.run(["uv", "pip", "install", "--target", str(target_dir), str(PYTHON_DIR)], check=True)


def armar_bundle(target_os: str, con_lanzador: bool = True) -> Path:
    """Ensambla todos los componentes en dist/bundle/."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Compilar lanzador
    binario_lanzador = compilar_lanzador(target_os) if con_lanzador else None

    # 2. Limpiar y recrear estructura de carpetas
    app_dir = DIST_DIR / "app"
    python_dir = DIST_DIR / "python"

    app_dir.mkdir(parents=True, exist_ok=True)
    python_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copiar lanzador al directorio raíz del bundle
    if binario_lanzador is not None:
        dest_lanzador = DIST_DIR / binario_lanzador.name
        shutil.copy2(binario_lanzador, dest_lanzador)
        if target_os != "windows":
            os.chmod(dest_lanzador, 0o755)

    # 4. Copiar código de la app
    copiar_codigo_fuente(app_dir)

    # 5. Preparar entorno Python
    preparar_runtime_python(python_dir, target_os)

    # 6. Copiar icono de Zonda
    shutil.copy2(LAUNCHER_DIR / "src" / "zonda.ico", DIST_DIR / "zonda.ico")

    print("\n=== ¡Bundle generado exitosamente! ===")
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
        "--sin-lanzador",
        action="store_true",
        help=(
            "No compilar el lanzador nativo. Lo usa el Flatpak, que lo reemplaza "
            "por un wrapper y asi no necesita un compilador de C"
        ),
    )
    args = parser.parse_args()

    sistema_actual = platform.system().lower()
    target = args.target
    if target == "auto":
        target = "macos" if sistema_actual == "darwin" else ("windows" if sistema_actual == "windows" else "linux")

    armar_bundle(
        target,
        con_lanzador=not args.sin_lanzador,
    )


if __name__ == "__main__":
    main()
