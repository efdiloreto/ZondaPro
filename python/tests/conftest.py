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

"""Configuración común de los tests.

Los tests son *smoke tests*: verifican que cada pieza del programa se construye
y corre de punta a punta, no la exactitud de los valores del CIRSOC 102. Las
pocas cifras que se afirman son valores de referencia capturados del propio
programa, y sirven para detectar cambios inadvertidos al actualizar numpy u
otra dependencia de cálculo.

Sobre la plataforma de Qt: se usa la nativa siempre que haya un display, porque
la vista 3D necesita un contexto gráfico real. Sólo se cae a ``offscreen`` en
sistemas sin display (por ejemplo CI en Linux), donde esos tests se saltean.
"""

import os
import sys


def _hay_display() -> bool:
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


if "QT_QPA_PLATFORM" not in os.environ and not _hay_display():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

SIN_OPENGL = os.environ.get("QT_QPA_PLATFORM") == "offscreen"

import pytest
from PyQt6 import QtCore, QtWidgets

# QtWebEngine exige contextos OpenGL compartidos y el atributo debe fijarse
# antes de que exista una QApplication, incluida la que crea pytest-qt.
QtWidgets.QApplication.setAttribute(
    QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts
)

from zonda import enums
from zonda.cirsoc import Cartel, CubiertaAislada, Edificio


@pytest.fixture(scope="session")
def qapp_cls():
    """Los tests usan la QApplication real del programa.

    Es la que sabe recibir los archivos que le manda el sistema (ver
    ``zonda.main.Aplicacion``), así que conviene que sea la misma que corre en
    producción y no una QApplication pelada.
    """
    from zonda.main import Aplicacion

    return Aplicacion


@pytest.fixture(scope="session")
def edificio() -> Edificio:
    return Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=8,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        categoria=enums.CategoriaEstructura.II,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        componentes_paredes={"Viga": 10.0},
        componentes_cubierta={"Correa": 5.0},
    )


@pytest.fixture(scope="session")
def edificio_angulo_pequeno() -> Edificio:
    """Edificio con ángulo de cubierta menor que 10° y alero.

    Altura de alero 6 m y cumbrera a 7 m sobre un ancho de 20 m: el ángulo es
    de unos 5.7°, así el viento normal a la cumbrera genera los casos de
    presión de las cubiertas de pequeña pendiente del nuevo Reglamento.
    """
    return Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=7,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        categoria=enums.CategoriaEstructura.II,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=1,
    )


@pytest.fixture(scope="session")
def edificio_con_parapeto() -> Edificio:
    """Edificio de la Tabla C 5.3-2 con parapeto de 1 m alrededor.

    Con ese parapeto se activa la Nota 5 de la Figura 5.3-2A: la Zona 3
    negativa iguala a la Zona 2 y las Zonas 2 y 3 reciben el valor positivo de
    las Zonas de pared 4 y 5.
    """
    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=8,
        altura_cumbrera=9,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        categoria=enums.CategoriaEstructura.II,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        parapeto=1,
        componentes_cubierta={"Correa": 5.0},
    )


@pytest.fixture(scope="session")
def cartel() -> Cartel:
    return Cartel(
        profundidad=1,
        ancho=10,
        altura_inferior=5,
        altura_superior=10,
        velocidad=45,
        categoria=enums.CategoriaEstructura.II,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )


@pytest.fixture(scope="session")
def cartel_con_topografia() -> Cartel:
    """Cartel con la topografía activada.

    Los parámetros están elegidos para que ``Topografia.topografia_considerada``
    dé ``True`` (H/Lh ≥ 0.2 y H > 20 m para la categoría de exposición B), así
    el reporte entra en la rama que muestra los datos del terreno.
    """
    return Cartel(
        profundidad=1,
        ancho=10,
        altura_inferior=5,
        altura_superior=10,
        velocidad=45,
        categoria=enums.CategoriaEstructura.II,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno=30,
        distancia_cresta=50,
        distancia_barlovento_sotavento=20,
        direccion=enums.DireccionTopografia.BARLOVENTO,
    )


@pytest.fixture(scope="session")
def cubierta_aislada() -> CubiertaAislada:
    return CubiertaAislada(
        ancho=10,
        longitud=20,
        altura_alero=5,
        altura_cumbrera=6,
        altura_bloqueo=0,
        posicion_bloqueo=enums.PosicionBloqueoCubierta.ALERO_BAJO,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        coeficiente_friccion=0.02,
        velocidad=45,
        categoria=enums.CategoriaEstructura.II,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
