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

"""Smoke tests del motor de cálculo (zonda.cirsoc)."""

import numpy as np
import pytest

from zonda import enums
from zonda.cirsoc import Cartel, CubiertaAislada, Edificio
from zonda.excepciones import ErrorLineamientos


def test_edificio_calcula(edificio: Edificio):
    assert edificio.geometria is not None
    assert edificio.presiones is not None
    assert len(edificio.geometria.alturas) > 0


def test_edificio_presiones_por_zona(edificio: Edificio):
    zonas = set(edificio.resultados.valores("zona"))
    assert enums.ZonaEdificio.PAREDES in zonas
    assert enums.ZonaEdificio.CUBIERTA in zonas


def test_edificio_alturas_son_crecientes(edificio: Edificio):
    alturas = np.asarray(edificio.geometria.alturas)
    assert np.all(np.diff(alturas) > 0)
    assert alturas[-1] == pytest.approx(8)


def test_cartel_calcula(cartel: Cartel):
    assert cartel.presiones is not None
    assert cartel.presiones.fuerza_total > 0


def test_cartel_valores_de_referencia(cartel: Cartel):
    """Valores capturados del programa antes de actualizar las dependencias.

    Si numpy o el propio cálculo cambian de resultado, este test lo detecta.
    """
    esperado = [
        634.42926105,
        668.35379502,
        698.44799113,
        725.60990135,
        750.44385665,
        773.37793185,
    ]
    assert np.asarray(cartel.presiones.valores) == pytest.approx(esperado, rel=1e-6)


def test_cartel_presiones_crecen_con_la_altura(cartel: Cartel):
    valores = np.asarray(cartel.presiones.valores)
    assert np.all(np.diff(valores) > 0)


def test_cubierta_aislada_calcula(cubierta_aislada: CubiertaAislada):
    assert cubierta_aislada.presiones is not None
    assert cubierta_aislada.cpn is not None


@pytest.mark.parametrize(
    "tipo_cubierta",
    [
        enums.TipoCubierta.PLANA,
        enums.TipoCubierta.DOS_AGUAS,
        enums.TipoCubierta.UN_AGUA,
    ],
)
def test_edificio_todos_los_tipos_de_cubierta(tipo_cubierta):
    altura_cumbrera = 6 if tipo_cubierta == enums.TipoCubierta.PLANA else 8
    edificio = Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=altura_cumbrera,
        tipo_cubierta=tipo_cubierta,
        cerramiento=enums.Cerramiento.CERRADO,
        categoria=enums.CategoriaEstructura.II,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
    assert edificio.presiones is not None


@pytest.mark.parametrize("categoria_exp", list(enums.CategoriaExposicion))
def test_cartel_todas_las_categorias_de_exposicion(categoria_exp):
    cartel = Cartel(
        profundidad=1,
        ancho=10,
        altura_inferior=5,
        altura_superior=10,
        velocidad=45,
        categoria=enums.CategoriaEstructura.II,
        factor_g_simplificado=True,
        categoria_exp=categoria_exp,
        considerar_topografia=False,
    )
    assert cartel.presiones.fuerza_total > 0


def test_cubierta_aislada_fuera_de_lineamientos_es_rechazada():
    """El CIRSOC no cubre cubiertas aisladas a dos aguas con -5° < ángulo < 5°."""
    with pytest.raises(ErrorLineamientos, match="ángulo"):
        CubiertaAislada(
            ancho=10,
            longitud=20,
            altura_alero=5,
            altura_cumbrera=5.1,
            altura_bloqueo=0,
            posicion_bloqueo=enums.PosicionBloqueoCubierta.ALERO_BAJO,
            tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
            coeficiente_friccion=0.02,
            velocidad=45,
            categoria=enums.CategoriaEstructura.II,
            categoria_exp=enums.CategoriaExposicion.B,
            considerar_topografia=False,
        )


def test_cubierta_aislada_plana_no_tiene_lineamientos():
    """El Reglamento sólo cubre cubiertas aisladas a dos aguas y a un agua."""
    with pytest.raises(ErrorLineamientos):
        CubiertaAislada(
            ancho=10,
            longitud=20,
            altura_alero=5,
            altura_cumbrera=5,
            altura_bloqueo=0,
            posicion_bloqueo=enums.PosicionBloqueoCubierta.ALERO_BAJO,
            tipo_cubierta=enums.TipoCubierta.PLANA,
            coeficiente_friccion=0.02,
            velocidad=45,
            categoria=enums.CategoriaEstructura.II,
            categoria_exp=enums.CategoriaExposicion.B,
            considerar_topografia=False,
        )
