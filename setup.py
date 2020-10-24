import glob
from distutils.core import setup
from pathlib import Path

from Cython.Build import cythonize

archivos = (
    "./zondapro/main.py",
    "./zondapro/sistema.py",
    "./zondapro/widgets/modulos.py",
    "./zondapro/widgets/zonda.py",
    "./zondapro/widgets/entrada.py",
    "./zondapro/widgets/dialogos.py",
    "./zondapro/cirsoc/factores.py",
    "./zondapro/cirsoc/cp/aisladas.py",
    "./zondapro/cirsoc/cp/cartel.py",
    "./zondapro/cirsoc/cp/edificio.py",
)

setup(
    ext_modules=cythonize(archivos, language_level=3),
)

archivos_pyd = tuple(Path(path) for path in glob.iglob("./zondapro/**/*.pyd", recursive=True))

for archivo in archivos:
    path = Path(archivo)
    path_c = Path(path.with_suffix(".c"))
    nombre = path.stem
    for archivo_pyd in archivos_pyd:
        if nombre in archivo_pyd.stem and archivo_pyd.parent == path.parent:
            archivo_pyd.rename(path.with_suffix(".pyd"))
    path_c.unlink()