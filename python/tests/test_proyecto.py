# Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>

# This file is part of Zonda.

# Zonda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Zonda is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Zonda.  If not, see <https://www.gnu.org/licenses/>.

"""Verifica el formato de los archivos de proyecto.

El archivo guarda los datos de entrada, no los resultados, así que estos tests
no necesitan Qt: van contra ``zonda.proyecto`` directamente.
"""

import json

import pytest

from zonda import proyecto
from zonda.enums import CategoriaExposicion, Estructura, TipoCubierta
from zonda.excepciones import ErrorArchivo

ESTADO = {
    "panel": {"viento": {"categoria_exp": CategoriaExposicion.C, "velocidad": 50}},
    "estructura": {
        "tipo_cubierta": TipoCubierta.UN_AGUA,
        "geometria": {"ancho": 42.5, "altura_alero": 9.0},
        "alturas_personalizadas": "3, 6, 9",
        "alero": True,
    },
}


def test_ida_y_vuelta(tmp_path):
    archivo = tmp_path / f"proyecto{proyecto.EXTENSION}"
    proyecto.guardar(archivo, Estructura.EDIFICIO, ESTADO)

    estructura, estado = proyecto.abrir(archivo)

    assert estructura is Estructura.EDIFICIO
    assert estado == ESTADO


def test_los_enums_se_guardan_por_nombre(tmp_path):
    """El nombre es estable; el valor es el texto que ve el usuario y puede cambiar."""
    archivo = tmp_path / f"proyecto{proyecto.EXTENSION}"
    proyecto.guardar(archivo, Estructura.EDIFICIO, ESTADO)

    contenido = json.loads(archivo.read_text(encoding="utf-8"))

    assert contenido["estructura"] == {"__enum__": "Estructura", "nombre": "EDIFICIO"}
    assert contenido["estado"]["estructura"]["tipo_cubierta"]["nombre"] == "UN_AGUA"


def test_los_enums_vuelven_como_enums(tmp_path):
    archivo = tmp_path / f"proyecto{proyecto.EXTENSION}"
    proyecto.guardar(archivo, Estructura.CARTEL, ESTADO)

    _, estado = proyecto.abrir(archivo)

    assert estado["estructura"]["tipo_cubierta"] is TipoCubierta.UN_AGUA
    assert estado["panel"]["viento"]["categoria_exp"] is CategoriaExposicion.C


def test_cada_estructura_se_distingue(tmp_path):
    """Es lo que deja abrir el archivo sólo desde el módulo que le corresponde."""
    for estructura in Estructura:
        archivo = tmp_path / f"{estructura.name}{proyecto.EXTENSION}"
        proyecto.guardar(archivo, estructura, ESTADO)
        assert proyecto.abrir(archivo)[0] is estructura


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorArchivo, match="No se pudo leer"):
        proyecto.abrir(tmp_path / f"no-existe{proyecto.EXTENSION}")


@pytest.mark.parametrize(
    ("nombre", "contenido", "mensaje"),
    [
        ("no es json", "esto no es json {", "no es un proyecto de Zonda"),
        ("otro programa", '{"programa": "otro"}', "no es un proyecto de Zonda"),
        (
            "otro formato",
            '{"programa": "zonda", "version_formato": 99}',
            "formato distinto",
        ),
        (
            "sin estado",
            '{"programa": "zonda", "version_formato": 2,'
            ' "estructura": {"__enum__": "Estructura", "nombre": "CARTEL"}}',
            "incompleto o dañado",
        ),
        (
            "enum que no existe",
            '{"programa": "zonda", "version_formato": 2, "estructura":'
            ' {"__enum__": "TipoCubierta", "nombre": "INVENTADA"}, "estado": {}}',
            "valor desconocido",
        ),
        (
            "clase de enum que no existe",
            '{"programa": "zonda", "version_formato": 2, "estructura":'
            ' {"__enum__": "NoExiste", "nombre": "A"}, "estado": {}}',
            "tipo de dato desconocido",
        ),
    ],
)
def test_archivos_invalidos(tmp_path, nombre, contenido, mensaje):
    """Un archivo que no sirve tiene que decir por qué, no romper con un traceback."""
    archivo = tmp_path / f"invalido{proyecto.EXTENSION}"
    archivo.write_text(contenido, encoding="utf-8")

    with pytest.raises(ErrorArchivo, match=mensaje):
        proyecto.abrir(archivo)
