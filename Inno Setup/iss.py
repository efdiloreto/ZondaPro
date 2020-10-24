import glob
import os
from pathlib import Path

from jinja2 import FileSystemLoader, Environment
from zondapro import __acercade__

aca = os.path.dirname(os.path.realpath(__file__))
carpeta_zonda = Path(aca).parent
zonda_exe = [a for a in glob.iglob("../build/**/Zonda.exe", recursive=True)][0]
instalador_pandoc = glob.glob("*pandoc*")[0]

file_loader = FileSystemLoader(aca)
env = Environment(loader=file_loader)

plantilla = env.get_template("plantilla_setup.iss")

setup_str = plantilla.render(
    nombre_soft="Zonda",
    version=__acercade__.__version__,
    web=__acercade__.__web__,
    compania=__acercade__.__compania__,
    descripcion=__acercade__.__descripcion__,
    contrato_licencia=os.path.join(carpeta_zonda, "CONTRATO DE LICENCIA.txt"),
    carpeta_exe=str(Path(Path(zonda_exe).parent).resolve()),
    instalador_pandoc=instalador_pandoc,
    icono_zonda=os.path.join(carpeta_zonda, "zondapro", "recursos", "iconos", "zonda.ico")
)

with open("setup.iss", "w") as f:
    f.write(setup_str)
