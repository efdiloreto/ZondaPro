import glob
import os
from pathlib import Path

from cx_Freeze import setup as cx_setup, Executable

from zondapro.__acercade__ import __version__, __descripcion__, __compania__

aca = os.path.dirname(os.path.realpath(__file__))


archivos_excluir = [
    "./zondapro/main.pyc",
    "./zondapro/sistema.pyc",
    "./zondapro/widgets/modulos.pyc",
    "./zondapro/widgets/zonda.pyc",
    "./zondapro/widgets/entrada.pyc",
    "./zondapro/widgets/dialogos.pyc",
    "./zondapro/cirsoc/factores.pyc",
    "./zondapro/cirsoc/cp/aisladas.pyc",
    "./zondapro/cirsoc/cp/cartel.pyc",
    "./zondapro/cirsoc/cp/edificio.pyc",
]

build_options = {
    "packages": ["pyqt5", "zondapro", "cryptography", "wmi"],
    "excludes": archivos_excluir + ["tkinter", "black"],
    "optimize": 1,
    "include_msvcr": True,
    "no_compress": True
}

executables = [
    Executable(
        os.path.join(aca, "zondapro", "iniciar.py"),
        base="Win32GUI",
        targetName="Zonda",
        icon=os.path.join(aca, "zondapro", "recursos", "iconos", "zonda.ico"),
        copyright=__compania__,
        trademarks=__compania__
    )
]

cx_setup(
    name="Zonda",
    version=__version__,
    description=__descripcion__,
    options={"build_exe": build_options},
    executables=executables,
)
