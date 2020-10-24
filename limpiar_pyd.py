import glob
from pathlib import Path

archivos_pyd = [Path(path) for path in glob.iglob("./zondapro/**/*.pyd", recursive=True)]


for archivo in archivos_pyd:
    print(archivo)
    archivo.unlink()