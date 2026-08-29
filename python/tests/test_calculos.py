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
from zonda.cirsoc.factores import Rafaga, Topografia
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
    """Valores de referencia bajo constantes de exposición CIRSOC 102-2025.

    Si numpy o el propio cálculo cambian de resultado, este test lo detecta.
    """
    esperado = [
        526.61431225,
        552.85043681,
        576.04993811,
        596.93171488,
        615.97817698,
        633.53020199,
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


def test_rafaga_factor_simplificado():
    rafaga = Rafaga(
        ancho=20,
        longitud=30,
        altura=10,
        altura_rafaga=6,
        velocidad=45,
        frecuencia=1.0,
        beta=0.02,
        flexibilidad=enums.Flexibilidad.RIGIDA,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
    )
    assert rafaga.factor == 0.85


def test_rafaga_edificio_rigido_exposicion_b():
    """Caso 1: Edificio Rígido Exp. B (B=20m, L=30m, h=10m, V=45m/s)."""
    rafaga = Rafaga(
        ancho=20.0,
        longitud=30.0,
        altura=10.0,
        altura_rafaga=6.0,  # 0.6 * 10 = 6.0 m < z_min=9.2 m -> z_bar = 9.2 m
        velocidad=45.0,
        frecuencia=1.0,
        beta=0.02,
        flexibilidad=enums.Flexibilidad.RIGIDA,
        factor_g_simplificado=False,
        categoria_exp=enums.CategoriaExposicion.B,
    )
    assert rafaga.parametros.z == pytest.approx(9.2, abs=0.01)
    assert rafaga.parametros.iz == pytest.approx(0.304, abs=0.005)
    assert rafaga.parametros.lz == pytest.approx(95.31, abs=0.05)
    assert rafaga.factor_q == pytest.approx(0.876, abs=0.005)
    assert rafaga.factor == pytest.approx(0.852, abs=0.005)


def test_rafaga_edificio_rigido_exposicion_c():
    """Caso 2: Edificio Rígido Exp. C (B=15m, L=15m, h=25m, V=45m/s)."""
    rafaga = Rafaga(
        ancho=15.0,
        longitud=15.0,
        altura=25.0,
        altura_rafaga=15.0,  # 0.6 * 25 = 15.0 m > z_min=4.6 m -> z_bar = 15.0 m
        velocidad=45.0,
        frecuencia=1.2,
        beta=0.02,
        flexibilidad=enums.Flexibilidad.RIGIDA,
        factor_g_simplificado=False,
        categoria_exp=enums.CategoriaExposicion.C,
    )
    assert rafaga.parametros.z == pytest.approx(15.0, abs=0.01)
    assert rafaga.parametros.iz == pytest.approx(0.187, abs=0.005)
    assert rafaga.parametros.lz == pytest.approx(164.84, abs=0.05)
    assert rafaga.factor_q == pytest.approx(0.892, abs=0.005)
    assert rafaga.factor == pytest.approx(0.873, abs=0.005)


def test_rafaga_estructura_flexible_dinamica():
    """Caso 3: Estructura Flexible Exp. B (B=10m, L=1m, h=40m, n1=0.4Hz, V=45m/s)."""
    rafaga = Rafaga(
        ancho=10.0,
        longitud=1.0,
        altura=40.0,
        altura_rafaga=24.0,  # 0.6 * 40 = 24.0 m > z_min=9.2 m
        velocidad=45.0,
        frecuencia=0.4,
        beta=0.02,
        flexibilidad=enums.Flexibilidad.FLEXIBLE,
        factor_g_simplificado=False,
        categoria_exp=enums.CategoriaExposicion.B,
    )
    assert rafaga.parametros.z == pytest.approx(24.0, abs=0.01)
    assert rafaga.parametros.iz == pytest.approx(0.259, abs=0.005)
    assert rafaga.parametros.lz == pytest.approx(131.21, abs=0.05)
    assert rafaga.factor_q == pytest.approx(0.863, abs=0.005)
    assert rafaga.parametros.gr == pytest.approx(3.97, abs=0.01)
    assert rafaga.parametros.r == pytest.approx(0.88, abs=0.01)
    assert rafaga.factor == pytest.approx(1.11, abs=0.01)


def test_rafaga_ejemplo_guia_edificio_rigido():
    """Ejemplo reglamentario: Edificio Rígido Exp. B (B=30m, L=30m, h=183m, V=51m/s)."""
    rafaga = Rafaga(
        ancho=30.0,
        longitud=30.0,
        altura=183.0,
        altura_rafaga=109.8,  # z_bar = 0.6 * h = 109.8 m
        velocidad=51.0,
        frecuencia=1.0,
        beta=0.01,
        flexibilidad=enums.Flexibilidad.RIGIDA,
        factor_g_simplificado=False,
        categoria_exp=enums.CategoriaExposicion.B,
    )
    assert rafaga.parametros.z == pytest.approx(109.8, abs=0.01)
    assert rafaga.parametros.iz == pytest.approx(0.201, abs=0.005)
    assert rafaga.parametros.lz == pytest.approx(217.8, abs=0.1)
    assert rafaga.factor_q**2 == pytest.approx(0.616, abs=0.005)
    assert rafaga.factor_q == pytest.approx(0.785, abs=0.005)
    assert rafaga.factor == pytest.approx(0.818, abs=0.005)


def test_rafaga_ejemplo_guia_edificio_flexible():
    """Ejemplo reglamentario: Edificio Flexible Exp. B (B=30m, L=30m, h=183m, n1=0.2Hz, beta=0.01, V=51m/s)."""
    rafaga = Rafaga(
        ancho=30.0,
        longitud=30.0,
        altura=183.0,
        altura_rafaga=109.8,  # z_bar = 0.6 * h = 109.8 m
        velocidad=51.0,
        frecuencia=0.2,
        beta=0.01,
        flexibilidad=enums.Flexibilidad.FLEXIBLE,
        factor_g_simplificado=False,
        categoria_exp=enums.CategoriaExposicion.B,
    )
    assert rafaga.parametros.z == pytest.approx(109.8, abs=0.01)
    assert rafaga.parametros.iz == pytest.approx(0.201, abs=0.005)
    assert rafaga.parametros.lz == pytest.approx(217.8, abs=0.1)
    assert rafaga.factor_q**2 == pytest.approx(0.616, abs=0.005)
    assert rafaga.parametros.gr == pytest.approx(3.787, abs=0.005)
    assert rafaga.parametros.r**2 == pytest.approx(1.25, abs=0.02)
    assert rafaga.parametros.r == pytest.approx(1.12, abs=0.01)
    assert rafaga.factor == pytest.approx(1.16, abs=0.01)


def test_rafaga_factor_rigido_usa_ancho_mas_altura():
    rafaga_1 = Rafaga(
        ancho=15,
        longitud=30,
        altura=10,
        altura_rafaga=6,
        velocidad=45,
        frecuencia=1.0,
        beta=0.02,
        flexibilidad=enums.Flexibilidad.RIGIDA,
        factor_g_simplificado=False,
        categoria_exp=enums.CategoriaExposicion.B,
    )
    rafaga_2 = Rafaga(
        ancho=30,
        longitud=15,
        altura=10,
        altura_rafaga=6,
        velocidad=45,
        frecuencia=1.0,
        beta=0.02,
        flexibilidad=enums.Flexibilidad.RIGIDA,
        factor_g_simplificado=False,
        categoria_exp=enums.CategoriaExposicion.B,
    )
    # Q depende de (ancho + altura) / Lz: a mayor ancho normal al viento, menor Q
    assert rafaga_1.factor_q > rafaga_2.factor_q
    assert rafaga_1.factor > 0


def test_topografia_umbrales_consideracion():
    # Exposición B: H >= 20 m y H/Lh >= 0.2
    topo_b_valida = Topografia(
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno=20,
        distancia_cresta=50,
        distancia_barlovento_sotavento=0,
        direccion=enums.DireccionTopografia.BARLOVENTO,
        alturas=10,
    )
    assert topo_b_valida.topografia_considerada() is True

    topo_b_baja = Topografia(
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno=19.9,
        distancia_cresta=50,
        distancia_barlovento_sotavento=0,
        direccion=enums.DireccionTopografia.BARLOVENTO,
        alturas=10,
    )
    assert topo_b_baja.topografia_considerada() is False
    assert topo_b_baja.factor == (1.0,)

    # Exposición C: H >= 5 m
    topo_c_valida = Topografia(
        categoria_exp=enums.CategoriaExposicion.C,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno=5.0,
        distancia_cresta=20,
        distancia_barlovento_sotavento=0,
        direccion=enums.DireccionTopografia.BARLOVENTO,
        alturas=5,
    )
    assert topo_c_valida.topografia_considerada() is True


def test_topografia_loma_2d_caso_1():
    """Caso 1: Loma 2D, Barlovento, Exp. B (H=30m, Lh=100m, x=0m, z=10m)."""
    topo = Topografia(
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno=30.0,
        distancia_cresta=100.0,
        distancia_barlovento_sotavento=0.0,
        direccion=enums.DireccionTopografia.BARLOVENTO,
        alturas=10.0,
    )
    params = topo.parametros
    assert params.lh == pytest.approx(100.0, abs=0.01)
    assert params.k1 == pytest.approx(0.39, abs=0.005)
    assert params.k2 == pytest.approx(1.0, abs=0.005)
    assert params.k3[0] == pytest.approx(0.741, abs=0.005)
    assert topo.factor[0] == pytest.approx(1.66, abs=0.01)


def test_topografia_pendiente_fuerte_caso_2():
    """Caso 2: Loma 2D, Pendiente Fuerte H/Lh > 0.5, Exp. C (H=30m, Lh=40m, x=20m, z=12m)."""
    topo = Topografia(
        categoria_exp=enums.CategoriaExposicion.C,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno=30.0,
        distancia_cresta=40.0,
        distancia_barlovento_sotavento=20.0,
        direccion=enums.DireccionTopografia.BARLOVENTO,
        alturas=12.0,
    )
    params = topo.parametros
    assert params.lh == pytest.approx(60.0, abs=0.01)  # 2*H
    assert params.k1 == pytest.approx(0.725, abs=0.005)
    assert params.k2 == pytest.approx(0.778, abs=0.005)
    assert params.k3[0] == pytest.approx(0.549, abs=0.005)
    assert topo.factor[0] == pytest.approx(1.71, abs=0.01)


def test_topografia_escarpa_sotavento_caso_3():
    """Caso 3: Escarpa 2D, Sotavento mu=4.0, Exp. B (H=25m, Lh=60m, x=100m, z=8m)."""
    topo = Topografia(
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.ESCARPA_BIDIMENSIONAL,
        altura_terreno=25.0,
        distancia_cresta=60.0,
        distancia_barlovento_sotavento=100.0,
        direccion=enums.DireccionTopografia.SOTAVENTO,
        alturas=8.0,
    )
    params = topo.parametros
    assert params.mu == pytest.approx(4.0, abs=0.01)
    assert params.lh == pytest.approx(60.0, abs=0.01)
    assert params.k1 == pytest.approx(0.312, abs=0.005)
    assert params.k2 == pytest.approx(0.583, abs=0.005)
    assert params.k3[0] == pytest.approx(0.717, abs=0.005)
    assert topo.factor[0] == pytest.approx(1.28, abs=0.01)


def test_topografia_fuera_de_influencia_caso_4():
    """Caso 4: Colina 3D, x > mu*Lh, Exp. B (H=20m, Lh=50m, x=120m, z=10m)."""
    topo = Topografia(
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=True,
        tipo_terreno=enums.TipoTerrenoTopografia.COLINA_TRIDIMENSIONAL,
        altura_terreno=20.0,
        distancia_cresta=50.0,
        distancia_barlovento_sotavento=120.0,
        direccion=enums.DireccionTopografia.BARLOVENTO,
        alturas=10.0,
    )
    params = topo.parametros
    assert params.lh == pytest.approx(50.0, abs=0.01)
    assert params.k1 == pytest.approx(0.38, abs=0.005)
    assert params.k2 == pytest.approx(0.0, abs=0.005)
    assert params.k3[0] == pytest.approx(0.449, abs=0.005)
    assert topo.factor[0] == pytest.approx(1.0, abs=0.005)


def test_factor_reduccion_gcpi_gran_volumen():
    """Verifica el factor de reducción Ri y GCpi reducido según Art. 1.11.1 (CIRSOC 102-2005).

    Caso Calcpad:
    Vi = 10000 m3
    Aog = 15 m2 (aberturas totales)
    GCpi nominal = 0.55 (parcialmente cerrado)
    Ri = min(1.0, 0.5 * (1 + 1 / sqrt(1 + Vi / (6950 * Aog)))) = 0.978253...
    GCpi_red = 0.55 * Ri = 0.538039...
    """
    edificio = Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=8,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.PARCIALMENTE_CERRADO,
        categoria=enums.CategoriaEstructura.II,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        reducir_gcpi=True,
        aberturas=(5.0, 5.0, 5.0, 0.0, 0.0),
        volumen_interno=10000.0,
    )
    presiones_cubierta = edificio.presiones.cubierta.sprfv
    assert presiones_cubierta.factor_reduccion_gcpi == pytest.approx(0.978, abs=0.001)
    assert presiones_cubierta.gcpi == pytest.approx(0.538, abs=0.001)


def test_cerramiento_condiciones_edificio():
    """Verifica las condiciones de cerramiento según Tabla 1.11-1 CIRSOC 102-2005."""
    from zonda.cirsoc import geometria

    # Edificio cerrado estándar (sin aberturas)
    geom_cerrado = geometria.Edificio(
        ancho=10,
        longitud=20,
        elevacion=0,
        altura_alero=5,
        altura_cumbrera=5,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        aberturas=(0.0, 0.0, 0.0, 0.0, 0.0),
    )
    assert not any(geom_cerrado.cerramiento_condicion_1)
    assert not any(geom_cerrado.cerramiento_condicion_2)
    assert not any(geom_cerrado.cerramiento_condicion_3)
    assert all(geom_cerrado.cerramiento_condicion_4)

    # Edificio parcialmente cerrado (gran abertura en pared 1)
    # Pared 1: Area = 50 m2, Abertura = 20 m2
    # Paredes 2, 3, 4: Aberturas = 1 m2 cada una -> A0i = 3 m2
    # 20 > 1.10 * 3 = 3.3 (condicion 2 cumple)
    # 20 > min(0.4, 0.5) = 0.4 (condicion 3 cumple)
    # A0i / Agi = 3 / (100 + 50 + 100 + 200) = 3 / 450 = 0.0067 <= 0.20 (condicion 4 cumple)
    geom_parc_cerrado = geometria.Edificio(
        ancho=10,
        longitud=20,
        elevacion=0,
        altura_alero=5,
        altura_cumbrera=5,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        aberturas=(20.0, 1.0, 1.0, 1.0, 0.0),
    )
    assert not any(geom_parc_cerrado.cerramiento_condicion_1)
    assert geom_parc_cerrado.cerramiento_condicion_2[0] is True
    assert geom_parc_cerrado.cerramiento_condicion_3[0] is True
    assert geom_parc_cerrado.cerramiento_condicion_4[0] is True

    # Edificio abierto (todas las paredes con >= 80% de aberturas)
    geom_abierto = geometria.Edificio(
        ancho=10,
        longitud=20,
        elevacion=0,
        altura_alero=5,
        altura_cumbrera=5,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        aberturas=(45.0, 90.0, 45.0, 90.0, 0.0),
    )
    assert all(geom_abierto.cerramiento_condicion_1)
