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

"""Script para compilar el lanzador nativo de Zonda en cualquier plataforma."""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC_DIR = RAIZ / "launcher" / "src"
DIST_DIR = RAIZ / "launcher" / "bin"

sys.path.insert(0, str(RAIZ))
from empaquetado.version import obtener_version  # noqa: E402

PLANTILLA_RC = SRC_DIR / "recursos.rc.in"
# El .rc generado va al lado de la plantilla y no a bin/ porque adentro
# referencia a zonda.ico con una ruta relativa, y los compiladores de recursos
# se invocan con cwd=SRC_DIR.
RC_GENERADO = SRC_DIR / "recursos.generado.rc"


def generar_rc() -> Path | None:
    """Completa la plantilla de recursos con la version del proyecto.

    Los cuatro campos de version del ejecutable de Windows llevan cuatro
    numeros, mientras que la version de Zonda tiene tres, asi que se completa
    con un cero. Dos de esos campos se escriben con comas y dos con puntos.

    Returns: El .rc listo para compilar, o ``None`` si no hay plantilla.
    """
    if not PLANTILLA_RC.exists():
        return None

    partes = (obtener_version().split(".") + ["0", "0", "0", "0"])[:4]
    contenido = PLANTILLA_RC.read_text(encoding="utf-8")
    contenido = contenido.replace("@VERSION_COMA@", ",".join(partes))
    contenido = contenido.replace("@VERSION_PUNTO@", ".".join(partes))

    RC_GENERADO.write_text(contenido, encoding="utf-8")
    return RC_GENERADO


def compilar_macos(salida: Path) -> None:
    clang = shutil.which("clang") or shutil.which("gcc")
    if not clang:
        print("Error: No se encontró clang ni gcc en el sistema.", file=sys.stderr)
        sys.exit(1)

    cmd = [
        clang,
        "-O2",
        "-Wall",
        "-Wextra",
        "-o",
        str(salida),
        str(SRC_DIR / "main.c"),
    ]
    print(f"Compilando en macOS: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def compilar_linux(salida: Path) -> None:
    gcc = shutil.which("gcc") or shutil.which("clang")
    if not gcc:
        print("Error: No se encontró gcc ni clang en el sistema.", file=sys.stderr)
        sys.exit(1)

    cmd = [
        gcc,
        "-O2",
        "-Wall",
        "-Wextra",
        "-o",
        str(salida),
        str(SRC_DIR / "main.c"),
    ]
    print(f"Compilando en Linux: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def compilar_windows_mingw(salida: Path, cross: bool = False) -> None:
    windres = shutil.which("x86_64-w64-mingw32-windres") if cross else shutil.which("windres")
    gcc = shutil.which("x86_64-w64-mingw32-gcc") if cross else shutil.which("gcc")

    if not gcc:
        print(
            "Error: No se encontró el compilador MinGW-w64 (gcc).",
            file=sys.stderr,
        )
        sys.exit(1)

    res_obj = SRC_DIR / "recursos.o"
    archivo_rc = generar_rc()
    if windres and archivo_rc is not None:
        cmd_rc = [
            windres,
            str(archivo_rc),
            "-O",
            "coff",
            "-o",
            str(res_obj),
        ]
        print(f"Compilando recursos Windows: {' '.join(cmd_rc)}")
        subprocess.run(cmd_rc, check=True, cwd=str(SRC_DIR))

    cmd = [
        gcc,
        "-O2",
        "-municode",
        "-mwindows",
        "-o",
        str(salida),
        str(SRC_DIR / "main.c"),
    ]
    if res_obj.exists():
        cmd.append(str(res_obj))
    cmd.extend(["-lshlwapi", "-lshell32", "-luser32"])

    print(f"Compilando en Windows (MinGW): {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    if res_obj.exists():
        res_obj.unlink()
    if RC_GENERADO.exists():
        RC_GENERADO.unlink()


def compilar_windows_msvc(salida: Path) -> None:
    cl = shutil.which("cl")
    rc = shutil.which("rc")
    if not cl:
        print("Error: No se encontró el compilador de MSVC (cl.exe).", file=sys.stderr)
        sys.exit(1)

    res_file = SRC_DIR / "recursos.res"
    archivo_rc = generar_rc()
    if rc and archivo_rc is not None:
        subprocess.run([rc, "/fo", str(res_file), str(archivo_rc)], check=True, cwd=str(SRC_DIR))

    cmd = [
        cl,
        "/O2",
        "/W3",
        "/D_UNICODE",
        "/DUNICODE",
        f"/Fe:{salida}",
        # Sin /Fo, cl.exe deja el .obj en el directorio de trabajo, que es la
        # raiz del repositorio. Va junto al ejecutable, que ya esta ignorado.
        f"/Fo:{DIST_DIR}" + chr(92),
        str(SRC_DIR / "main.c"),
    ]
    if res_file.exists():
        cmd.append(str(res_file))
    cmd.extend(["/link", "/SUBSYSTEM:WINDOWS", "shlwapi.lib", "shell32.lib", "user32.lib"])

    print(f"Compilando en Windows (MSVC): {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    if res_file.exists():
        res_file.unlink()
    if RC_GENERADO.exists():
        RC_GENERADO.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compilar el lanzador nativo de Zonda.")
    parser.add_argument(
        "--target",
        choices=["auto", "windows", "macos", "linux"],
        default="auto",
        help="Plataforma objetivo a compilar (default: auto)",
    )
    args = parser.parse_args()

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    target = args.target
    sistema_actual = platform.system().lower()

    if target == "auto":
        target = "macos" if sistema_actual == "darwin" else ("windows" if sistema_actual == "windows" else "linux")

    if target == "windows":
        salida = DIST_DIR / "Zonda.exe"
        if sistema_actual == "windows":
            if shutil.which("cl"):
                compilar_windows_msvc(salida)
            else:
                compilar_windows_mingw(salida, cross=False)
        else:
            compilar_windows_mingw(salida, cross=True)
    elif target == "macos":
        salida = DIST_DIR / "zonda"
        compilar_macos(salida)
    elif target == "linux":
        salida = DIST_DIR / "zonda"
        compilar_linux(salida)

    print(f"\n✓ Lanzador compilado exitosamente en: {salida}")


if __name__ == "__main__":
    main()
