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
from zonda.cirsoc.cp.edificio import (
    CubiertaComponentes,
    ParedesComponentes,
    cp_positivo_paredes,
    distancia_a,
)
from zonda.cirsoc.factores import Rafaga, Topografia, factor_altitud
from zonda.cirsoc.presiones.edificio import presion_minima
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


def test_factor_altitud():
    assert factor_altitud(0) == 1.0
    assert factor_altitud(-10) == 1.0
    assert factor_altitud(600) == pytest.approx(0.931, abs=0.01)
    assert factor_altitud(1500) == pytest.approx(0.836, abs=0.01)


def test_edificio_factor_altitud(edificio: Edificio):
    edificio_altitud = Edificio(
        ancho=edificio.ancho,
        longitud=edificio.longitud,
        elevacion=edificio.elevacion,
        altura_alero=edificio.altura_alero,
        altura_cumbrera=edificio.altura_cumbrera,
        tipo_cubierta=edificio.tipo_cubierta,
        cerramiento=edificio.cerramiento,
        categoria=edificio.categoria,
        velocidad=edificio.velocidad,
        factor_g_simplificado=edificio.factor_g_simplificado,
        categoria_exp=edificio.categoria_exp,
        considerar_topografia=edificio.considerar_topografia,
        altitud=1000,
    )
    ke = factor_altitud(1000)
    assert edificio_altitud.factor_altitud == pytest.approx(ke)
    assert edificio_altitud.resultados[0].q.ke == pytest.approx(ke)
    assert edificio_altitud.resultados[0].q.valor == pytest.approx(
        edificio.resultados[0].q.valor * ke
    )


def test_presion_dinamica_benchmark_calcpad():
    """Valida los valores calculados de Kz y qz contra el script de Calcpad.

    Parámetros de entrada:
    - V = 55.1 m/s, Kd = 0.85, Altitud ze = 600 m (Ke = 0.931084...)
    - Exposición B (alfa = 7.5, zg = 1000 m), Kzt = 1.0
    """
    edificio = Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=20,
        altura_cumbrera=20,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        cerramiento=enums.Cerramiento.CERRADO,
        categoria=enums.CategoriaEstructura.II,
        velocidad=55.1,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        altitud=600,
        alturas_personalizadas=[0, 5, 8, 10, 15, 20],
    )
    # Valores esperados según Calcpad
    # Altura z: (Kz, qz)
    referencias = {
        0.0: (0.587, 864.14),
        5.0: (0.587, 864.14),
        8.0: (0.665, 979.52),
        10.0: (0.706, 1039.58),
        15.0: (0.787, 1158.28),
        20.0: (0.849, 1250.64),
    }
    ke_esperado = 0.931084
    assert edificio.factor_altitud == pytest.approx(ke_esperado, abs=1e-4)

    presiones = edificio.presiones.paredes.sprfv.presiones_velocidad
    for p in presiones:
        if p.altura in referencias:
            kz_esp, qz_esp = referencias[p.altura]
            assert p.kz == pytest.approx(kz_esp, abs=0.001)
            assert p.valor == pytest.approx(qz_esp, abs=0.1)


def test_cartel_calcula(cartel: Cartel):
    assert cartel.presiones is not None
    assert cartel.presiones.fuerza_total > 0


def test_cartel_valores_de_referencia(cartel: Cartel):
    """Valores de referencia bajo constantes de exposición CIRSOC 102-2025.

    Si numpy o el propio cálculo cambian de resultado, este test lo detecta.
    """
    esperado = [
        631.41318036,
        662.87042424,
        690.68688402,
        715.72370777,
        738.56089877,
        759.60586408,
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


def _edificio_angulo_pequeno(
    tipo_cubierta=enums.TipoCubierta.DOS_AGUAS, alero: float = 0
) -> Edificio:
    """Crea un edificio con ángulo de cubierta menor que 10°.

    Args:
        tipo_cubierta: El tipo de cubierta.
        alero: La dimensión del alero.

    Returns:
        Un edificio con cubierta de pequeña pendiente (≈ 5.7°).
    """
    altura_cumbrera = 7 if tipo_cubierta != enums.TipoCubierta.PLANA else 6
    return Edificio(
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
        alero=alero,
    )


@pytest.mark.parametrize("tipo_cubierta", list(enums.TipoCubierta))
def test_cubierta_barlovento_angulo_menor_diez_tiene_caso_positivo(tipo_cubierta):
    """Con viento normal, las cubiertas de ángulo < 10° suman el caso positivo.

    El nuevo Reglamento agrega un caso de presión positiva de -0.18 en todas
    las zonas de la cubierta a barlovento con viento normal a la cumbrera.
    """
    edificio = _edificio_angulo_pequeno(tipo_cubierta)
    cubierta_normal = edificio.resultados_sprfv.filtrar(
        zona=enums.ZonaEdificio.CUBIERTA,
        direccion=enums.DireccionVientoMetodoDireccionalSprfv.NORMAL,
    )
    positivas = cubierta_normal.filtrar(
        caso=enums.TipoPresionCubiertaBarloventoSprfv.POSITIVA
    )
    negativas = cubierta_normal.filtrar(caso=None)
    assert positivas
    assert len(positivas) == len(negativas)
    for fila in positivas:
        assert fila.cp == pytest.approx(-0.18)
        assert fila.rango is not None
        assert fila.posicion is None
    assert all(fila.cp < 0 for fila in negativas)


@pytest.mark.parametrize("tipo_cubierta", list(enums.TipoCubierta))
def test_cubierta_barlovento_angulo_menor_diez_presiones_de_los_casos(tipo_cubierta):
    """Los dos casos conviven y tienen presiones coherentes.

    El caso positivo es más bajo (en valor absoluto) que el negativo por zona,
    así que su presión es menor.
    """
    edificio = _edificio_angulo_pequeno(tipo_cubierta)
    cubierta_normal = edificio.resultados_sprfv.filtrar(
        zona=enums.ZonaEdificio.CUBIERTA,
        direccion=enums.DireccionVientoMetodoDireccionalSprfv.NORMAL,
    )
    positivas = cubierta_normal.filtrar(
        caso=enums.TipoPresionCubiertaBarloventoSprfv.POSITIVA
    )
    negativas = cubierta_normal.filtrar(caso=None)
    for positiva, negativa in zip(positivas, negativas, strict=True):
        assert abs(positiva.pos) < abs(negativa.pos)
        assert abs(positiva.neg) < abs(negativa.neg)


def test_cubierta_barlovento_angulo_menor_diez_alero():
    """El alero repite el caso positivo de la cubierta de pequeña pendiente.

    A barlovento el coeficiente es -0.18 - 0.8 y a sotavento se mantiene.
    """
    edificio = _edificio_angulo_pequeno(alero=1)
    alero = edificio.resultados_sprfv.filtrar(
        zona=enums.ZonaEdificio.ALERO,
        direccion=enums.DireccionVientoMetodoDireccionalSprfv.NORMAL,
    )
    barlovento = alero.filtrar(
        posicion=enums.PosicionCubiertaAleroSprfv.BARLOVENTO,
        caso=enums.TipoPresionCubiertaBarloventoSprfv.POSITIVA,
    ).unica()
    sotavento = alero.filtrar(
        posicion=enums.PosicionCubiertaAleroSprfv.SOTAVENTO,
        caso=enums.TipoPresionCubiertaBarloventoSprfv.POSITIVA,
    ).unica()
    assert barlovento.cp == pytest.approx(-0.98)
    assert sotavento.cp == pytest.approx(-0.18)


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


def _paredes_componentes(
    area: float,
    *,
    ancho: float = 20,
    longitud: float = 30,
    altura_media: float = 8,
    angulo: float = 5,
) -> object:
    """Instancia ParedesComponentes con un solo componente del área dada.

    Args:
        area: El área tributaria del componente.
        ancho: El ancho del edificio.
        longitud: La longitud del edificio.
        altura_media: La altura media de cubierta.
        angulo: El ángulo de cubierta.

    Returns:
        La instancia, para leer ``referencia``, ``distancia_a`` y ``entradas``.
    """
    return ParedesComponentes(
        ancho=ancho,
        longitud=longitud,
        altura_media=altura_media,
        angulo_cubierta=angulo,
        componentes={"comp": area},
    )


def test_paredes_componentes_referencia_nueva_tabla():
    """La rama baja usa Tabla C 5.3-1; un edificio alto la Figura 5.4-1."""
    bajo = _paredes_componentes(3)
    assert bajo.referencia == "Tabla C 5.3-1"
    alto = _paredes_componentes(3, altura_media=25)
    assert alto.referencia == "Figura 5.4-1"


def test_paredes_componentes_valores_tabla_c531():
    """Valores GCp extremos y de rampa log, por zona y por tramo de área.

    Con ángulo ≤ 10° hay descuento 0.9 sobre todos los GCp (como dice hoy el
    código; la nota al pie permite reducir solo los positivos). Los valores
    del tramo log son interpolación logarítmica entre los extremos de la
    tabla —-1.1→−0.8, −1.4→−0.8 y 1.0→0.7 para A∈[1, 50].
    """
    log10 = np.log10
    factor = 0.9  # ángulo=5 → descuento 0.9 por pendiente ≤ 10°

    def esperado(cps: tuple[float, float], area: float) -> float:
        primer_cp, ultimo_cp = cps
        primer_area, ultima_area = 1.0, 50.0
        if area <= primer_area:
            return primer_cp * factor
        if area >= ultima_area:
            return ultimo_cp * factor
        g = (ultimo_cp - primer_cp) / log10(ultima_area / primer_area)
        return (primer_cp + g * log10(area / primer_area)) * factor

    casos = (
        (0.5, (1.0, 0.7), (-1.1, -0.8), (-1.4, -0.8)),
        (3.0, (1.0, 0.7), (-1.1, -0.8), (-1.4, -0.8)),
        (60.0, (1.0, 0.7), (-1.1, -0.8), (-1.4, -0.8)),
    )
    for area, pos, n4, n5 in casos:
        paredes = _paredes_componentes(area, angulo=5)
        valores_cp = {
            entrada.zona_componente: entrada.valor for entrada in paredes.entradas
        }
        assert len(valores_cp) == 3
        assert valores_cp[enums.ZonaComponenteParedEdificio.TODAS] == pytest.approx(
            esperado(pos, area)
        )
        assert valores_cp[enums.ZonaComponenteParedEdificio.CUATRO] == pytest.approx(
            esperado(n4, area)
        )
        assert valores_cp[enums.ZonaComponenteParedEdificio.CINCO] == pytest.approx(
            esperado(n5, area)
        )


def test_paredes_componentes_benchmark_calcpad():
    """Valida los valores de GCp contra el script de Calcpad para Tabla C 5.3-1.

    Parámetros de entrada:
    - θ = 5° (aplica r = 0.9)
    - Casos de área A ∈ {0.5, 3.0, 10.0, 60.0} m²
    """
    # area: (pos_todas, neg_zona4, neg_zona5)
    referencias_calcpad = {
        0.5: (0.9, -0.99, -1.26),
        3.0: (0.8242, -0.9142, -1.1084),
        10.0: (0.7411, -0.8311, -0.9421),
        60.0: (0.63, -0.72, -0.72),
    }
    for area, (pos_esp, n4_esp, n5_esp) in referencias_calcpad.items():
        paredes = _paredes_componentes(area, angulo=5)
        valores_cp = {
            entrada.zona_componente: entrada.valor for entrada in paredes.entradas
        }
        assert valores_cp[enums.ZonaComponenteParedEdificio.TODAS] == pytest.approx(
            pos_esp, abs=0.001
        )
        assert valores_cp[enums.ZonaComponenteParedEdificio.CUATRO] == pytest.approx(
            n4_esp, abs=0.001
        )
        assert valores_cp[enums.ZonaComponenteParedEdificio.CINCO] == pytest.approx(
            n5_esp, abs=0.001
        )


def test_paredes_componentes_excepcion_distancia_a():
    """La excepción limita "a" a 0.8·h para θ ∈ [0°, 7°] y dimensión mínima > 90 m."""
    # Edificio plano, ancho < 90: la excepción no debe aplicar aunque θ ∈ [0, 7]
    a_normal = distancia_a(60, 80, 10)
    edificio_normal = _paredes_componentes(
        2, ancho=60, longitud=80, altura_media=10, angulo=5
    )
    assert edificio_normal.distancia_a == a_normal

    # Edificio plano, dimensión mínima > 90: se limita a 0.8h
    a_total = distancia_a(95, 120, 10)
    edificio = _paredes_componentes(
        2, ancho=95, longitud=120, altura_media=10, angulo=5
    )
    assert edificio.distancia_a == min(a_total, 0.8 * 10)

    # θ = 8° (fuera de rango): no se aplica la excepción
    a_sin_excepcion = distancia_a(95, 120, 10)
    edificio_8 = _paredes_componentes(
        2, ancho=95, longitud=120, altura_media=10, angulo=8
    )
    assert edificio_8.distancia_a == a_sin_excepcion


def test_paredes_componentes_valores_figura_5_4_1():
    """Valores GCp de la Figura 5.4-1 (h > 20 m), extremos y rampa log.

    El positivo viaja en la zona "todas" con la rampa (0.9 → 0.6) para
    A ∈ [2, 50] y sin el descuento 0.9 de la rama baja; los negativos de las
    Zonas 4 y 5, (-0.9 → -0.7) y (-1.8 → -1.0), con el mismo rango de áreas.
    Referencia reglamentaria fija.
    """
    log10 = np.log10

    def esperado(cps: tuple[float, float], area: float) -> float:
        primer_cp, ultimo_cp = cps
        primer_area, ultima_area = 2.0, 50.0
        if area <= primer_area:
            return primer_cp
        if area >= ultima_area:
            return ultimo_cp
        g = (ultimo_cp - primer_cp) / log10(ultima_area / primer_area)
        return primer_cp + g * log10(area / primer_area)

    casos = (
        (0.5, (0.9, 0.6), (-0.9, -0.7), (-1.8, -1.0)),
        (3.0, (0.9, 0.6), (-0.9, -0.7), (-1.8, -1.0)),
        (60.0, (0.9, 0.6), (-0.9, -0.7), (-1.8, -1.0)),
    )
    for area, pos, n4, n5 in casos:
        paredes = _paredes_componentes(area, altura_media=25, angulo=5)
        valores_cp = {
            entrada.zona_componente: entrada.valor for entrada in paredes.entradas
        }
        assert len(valores_cp) == 3
        assert valores_cp[enums.ZonaComponenteParedEdificio.TODAS] == pytest.approx(
            esperado(pos, area)
        )
        assert valores_cp[enums.ZonaComponenteParedEdificio.CUATRO] == pytest.approx(
            esperado(n4, area)
        )
        assert valores_cp[enums.ZonaComponenteParedEdificio.CINCO] == pytest.approx(
            esperado(n5, area)
        )


def test_paredes_componentes_gran_altura_no_aplica_excepcion_distancia_a():
    """La excepción de "a" a 0,8·h es de la Tabla C 5.3-1, no de la 5.4-1."""
    a_sin_excepcion = distancia_a(95, 120, 25)
    alto = _paredes_componentes(2, ancho=95, longitud=120, altura_media=25, angulo=5)
    assert alto.distancia_a == a_sin_excepcion


def _cubierta_componentes(
    area: float,
    *,
    ancho: float = 30,
    longitud: float = 40,
    altura_media: float = 8,
    angulo: float = 4,
    tipo_cubierta: enums.TipoCubierta = enums.TipoCubierta.DOS_AGUAS,
    parapeto: float = 0,
    es_alero: bool = False,
) -> CubiertaComponentes:
    """Instancia CubiertaComponentes con un solo componente del área dada.

    Args:
        area: El área tributaria del componente.
        ancho: El ancho del edificio.
        longitud: La longitud del edificio.
        altura_media: La altura media de cubierta.
        angulo: El ángulo de cubierta.
        tipo_cubierta: El tipo de cubierta.
        parapeto: La dimensión del parapeto.
        es_alero: Indica si los valores son los del alero.

    Returns:
        La instancia, para leer ``referencia``, ``distancias_zonas`` y
        ``entradas``.
    """
    return CubiertaComponentes(
        ancho=ancho,
        longitud=longitud,
        altura_media=altura_media,
        angulo=angulo,
        tipo_cubierta=tipo_cubierta,
        parapeto=parapeto,
        es_alero=es_alero,
        componentes={"comp": area},
    )


def _valores_por_zona(cubierta: CubiertaComponentes) -> dict:
    """Los valores de GCp indexados por zona.

    Args:
        cubierta: La instancia de la que se leen las entradas.

    Returns:
        El valor de cada zona.
    """
    return {entrada.zona_componente: entrada.valor for entrada in cubierta.entradas}


def test_cubierta_componentes_referencia_tabla_c532():
    """La cubierta a dos aguas con θ ≤ 7° y h ≤ 20 m usa la Tabla C 5.3-2."""
    assert _cubierta_componentes(3).referencia == "Tabla C 5.3-2"
    assert _cubierta_componentes(3, es_alero=True).referencia == "Tabla C 5.3-2"


def test_cubierta_componentes_referencia_tabla_c533():
    """La cubierta a dos aguas con 7° < θ ≤ 20° y h ≤ 20 m usa la Tabla C 5.3-3."""
    assert _cubierta_componentes(3, angulo=8).referencia == "Tabla C 5.3-3"
    assert _cubierta_componentes(3, angulo=20).referencia == "Tabla C 5.3-3"
    assert (
        _cubierta_componentes(3, angulo=8, es_alero=True).referencia == "Tabla C 5.3-3"
    )
    # Límite: θ = 7° sigue en la 5.3-2.
    assert _cubierta_componentes(3, angulo=7).referencia == "Tabla C 5.3-2"
    # Fuera del alcance 2025: sin lineamientos.
    with pytest.raises(ErrorLineamientos):
        _ = _cubierta_componentes(3, angulo=46).referencia
    with pytest.raises(ErrorLineamientos):
        _ = _cubierta_componentes(3, altura_media=21, angulo=8).referencia


def test_cubierta_componentes_referencia_tabla_c534():
    """La cubierta a dos aguas con 20° < θ ≤ 27° y h ≤ 20 m usa la Tabla C 5.3-4."""
    assert _cubierta_componentes(3, angulo=21).referencia == "Tabla C 5.3-4"
    assert _cubierta_componentes(3, angulo=27).referencia == "Tabla C 5.3-4"
    assert (
        _cubierta_componentes(3, angulo=25, es_alero=True).referencia == "Tabla C 5.3-4"
    )
    # Límite: θ = 20° sigue en la 5.3-3.
    assert _cubierta_componentes(3, angulo=20).referencia == "Tabla C 5.3-3"
    # Las zonas se miden con la distancia "a", no con h como en la 5.3-2.
    assert _cubierta_componentes(3, angulo=25).distancias_zonas is None


def test_cubierta_componentes_referencia_tabla_c535():
    """La cubierta a dos aguas con 27° < θ ≤ 45° y h ≤ 20 m usa la Tabla C 5.3-5."""
    assert _cubierta_componentes(3, angulo=28).referencia == "Tabla C 5.3-5"
    assert _cubierta_componentes(3, angulo=45).referencia == "Tabla C 5.3-5"
    assert (
        _cubierta_componentes(3, angulo=36, es_alero=True).referencia == "Tabla C 5.3-5"
    )
    # Límite: θ = 27° sigue en la 5.3-4.
    assert _cubierta_componentes(3, angulo=27).referencia == "Tabla C 5.3-4"
    # Las zonas se miden con la distancia "a", no con h como en la 5.3-2.
    assert _cubierta_componentes(3, angulo=36).distancias_zonas is None


def test_cubierta_componentes_referencia_figura_5_3_5a():
    """La cubierta a un agua con 3° < θ ≤ 10° y h ≤ 20 m usa la Figura 5.3-5A."""
    un_agua = enums.TipoCubierta.UN_AGUA
    assert _cubierta_componentes(3, tipo_cubierta=un_agua).referencia == "Figura 5.3-5A"
    assert (
        _cubierta_componentes(3, angulo=10, tipo_cubierta=un_agua).referencia
        == "Figura 5.3-5A"
    )
    assert (
        _cubierta_componentes(
            3, angulo=4, tipo_cubierta=un_agua, es_alero=True
        ).referencia
        == "Figura 5.3-5A"
    )
    # Límite: θ = 3° sigue en la 5.3-2 (Nota 5 de la Figura 5.3-5A).
    assert (
        _cubierta_componentes(3, angulo=3, tipo_cubierta=un_agua).referencia
        == "Tabla C 5.3-2"
    )
    # Las zonas se miden con la distancia "a", no con h como en la 5.3-2.
    assert (
        _cubierta_componentes(3, angulo=4, tipo_cubierta=un_agua).distancias_zonas
        is None
    )
    with pytest.raises(ErrorLineamientos):
        _ = _cubierta_componentes(
            3, altura_media=21, angulo=8, tipo_cubierta=un_agua
        ).referencia


def test_cubierta_componentes_referencia_figura_5_4_1():
    """La cubierta con h > 20 m y θ ≤ 7° usa la Figura 5.4-1 (Nota 6)."""
    assert _cubierta_componentes(3, altura_media=21).referencia == "Figura 5.4-1"
    assert (
        _cubierta_componentes(
            3, altura_media=25, tipo_cubierta=enums.TipoCubierta.UN_AGUA
        ).referencia
        == "Figura 5.4-1"
    )
    # Los ángulos mayores a 7° y los aleros de gran altura quedan sin
    # lineamientos 2025.
    with pytest.raises(ErrorLineamientos):
        _ = _cubierta_componentes(3, altura_media=21, angulo=8).referencia
    with pytest.raises(ErrorLineamientos):
        _ = _cubierta_componentes(3, altura_media=21, es_alero=True).referencia
    with pytest.raises(ErrorLineamientos):
        _ = _cubierta_componentes(
            3, altura_media=21, angulo=8, tipo_cubierta=enums.TipoCubierta.UN_AGUA
        ).referencia
    # Las zonas se miden con la distancia "a", no con h como en la 5.3-2.
    assert _cubierta_componentes(3, altura_media=21).distancias_zonas is None


def test_cubierta_componentes_valores_figura_5_4_1():
    """Valores GCp de cubierta de la Figura 5.4-1 (h > 20 m).

    Las Zonas 1, 2 y 3 con sus rampas log (-1.4 → -0.9, -2.3 → -1.6 y
    -3.2 → -2.3) para A ∈ [1, 50] y sin valor positivo. Con parapeto de 1 m
    o más y θ ≤ 10° la Zona 3 negativa iguala a la Zona 2 (Nota 7).
    """
    log10 = np.log10

    def esperado(cps: tuple[float, float], area: float) -> float:
        primer_cp, ultimo_cp = cps
        if area <= 1:
            return primer_cp
        if area >= 50:
            return ultimo_cp
        g = (ultimo_cp - primer_cp) / log10(50)
        return primer_cp + g * log10(area)

    zonas = enums.ZonaComponenteCubiertaEdificio
    casos = (
        (0.5, (-1.4, -0.9), (-2.3, -1.6), (-3.2, -2.3)),
        (3.0, (-1.4, -0.9), (-2.3, -1.6), (-3.2, -2.3)),
        (60.0, (-1.4, -0.9), (-2.3, -1.6), (-3.2, -2.3)),
    )
    for area, n1, n2, n3 in casos:
        valores = _valores_por_zona(_cubierta_componentes(area, altura_media=21))
        assert dict(valores) == {
            zonas.UNO: pytest.approx(esperado(n1, area)),
            zonas.DOS: pytest.approx(esperado(n2, area)),
            zonas.TRES: pytest.approx(esperado(n3, area)),
        }

    # Nota 7: parapeto ≥ 1 m (y θ ≤ 10°, que acá siempre se cumple) → la
    # Zona 3 negativa iguala a la Zona 2.
    con_parapeto = _valores_por_zona(
        _cubierta_componentes(3, altura_media=21, parapeto=1)
    )
    assert con_parapeto[zonas.TRES] == pytest.approx(con_parapeto[zonas.DOS])
    # Sin parapeto la Zona 3 mantiene su propia curva.
    sin_parapeto = _valores_por_zona(_cubierta_componentes(3, altura_media=21))
    assert sin_parapeto[zonas.TRES] != pytest.approx(sin_parapeto[zonas.DOS])


def test_cubierta_componentes_referencia_figura_5_3_5b():
    """La cubierta a un agua con 10° < θ ≤ 30° y h ≤ 20 m usa la Figura 5.3-5B."""
    un_agua = enums.TipoCubierta.UN_AGUA
    assert (
        _cubierta_componentes(3, angulo=11, tipo_cubierta=un_agua).referencia
        == "Figura 5.3-5B"
    )
    assert (
        _cubierta_componentes(3, angulo=30, tipo_cubierta=un_agua).referencia
        == "Figura 5.3-5B"
    )
    assert (
        _cubierta_componentes(
            3, angulo=20, tipo_cubierta=un_agua, es_alero=True
        ).referencia
        == "Figura 5.3-5B"
    )
    # Límite: θ = 10° sigue en la 5.3-5A.
    assert (
        _cubierta_componentes(3, angulo=10, tipo_cubierta=un_agua).referencia
        == "Figura 5.3-5A"
    )
    # Las zonas se miden con la distancia "a", no con h como en la 5.3-2.
    assert (
        _cubierta_componentes(3, angulo=20, tipo_cubierta=un_agua).distancias_zonas
        is None
    )
    with pytest.raises(ErrorLineamientos):
        _ = _cubierta_componentes(3, angulo=31, tipo_cubierta=un_agua).referencia


def test_cubierta_componentes_referencia_tabla_c532_planas():
    """La cubierta plana trata su ángulo 0 como la tabla de pendiente mínima."""
    assert (
        _cubierta_componentes(3, tipo_cubierta=enums.TipoCubierta.PLANA).referencia
        == "Tabla C 5.3-2"
    )


def test_cubierta_componentes_distancias_zonas():
    """Las zonas de la Figura 5.3-2A se miden con h, no con la distancia "a"."""
    cubierta = _cubierta_componentes(3, altura_media=8)
    assert cubierta.distancias_zonas == pytest.approx((1.6, 4.8, 9.6))
    assert _cubierta_componentes(3, angulo=8).distancias_zonas is None


def test_cubierta_componentes_valores_tabla_c533():
    """Los GCp de la Tabla C 5.3-3 (Figura 5.3-2B).

    Los esperados salen de las fórmulas de la tabla, que son otra forma de
    escribir la interpolación logarítmica entre los extremos de cada zona.
    """
    log10 = np.log10

    def esperado(area: float) -> dict:
        # zona: (área tramo constante, extremo, cst, pendiente, área tope, tope)
        pendientes = {
            enums.ZonaComponenteCubiertaEdificio.UNO: (
                2,
                -2.0,
                -2.3839,
                1.2754,
                30,
                -0.5,
            ),
            enums.ZonaComponenteCubiertaEdificio.DOS: (1, -2.7, -2.7, 1.3067, 20, -1.0),
            enums.ZonaComponenteCubiertaEdificio.TRES: (1, -3.6, -3.6, 1.8, 10, -1.8),
        }
        negativos = {}
        for zona, (area_a, extremo, cst, pendiente, area_b, tope) in pendientes.items():
            if area <= area_a:
                negativos[zona] = extremo
            elif area <= area_b:
                negativos[zona] = cst + pendiente * log10(area)
            else:
                negativos[zona] = tope
        if area <= 1:
            positivo = 0.6
        elif area <= 20:
            positivo = 0.6 - 0.2306 * log10(area)
        else:
            positivo = 0.3
        negativos[enums.ZonaComponenteCubiertaEdificio.TODAS] = positivo
        return negativos

    for area in (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0):
        valores_cp = _valores_por_zona(_cubierta_componentes(area, angulo=12))
        assert valores_cp == pytest.approx(esperado(area), abs=0.001)


def test_cubierta_componentes_alero_tabla_c533():
    """El alero de la Tabla C 5.3-3 usa la superficie superior de la cubierta.

    La Nota 5 de la Figura 5.3-2B envía los voladizos al Art. 5.7 (pendiente,
    ver issue): por ahora el alero toma los valores de la cubierta, sin el
    positivo de la zona "todas".
    """
    cubierta = _cubierta_componentes(5, angulo=12)
    alero = _cubierta_componentes(5, angulo=12, es_alero=True)
    zonas = enums.ZonaComponenteCubiertaEdificio
    valores_cubierta = _valores_por_zona(cubierta)
    valores_alero = _valores_por_zona(alero)
    assert zonas.TODAS not in valores_alero
    for zona in (zonas.UNO, zonas.DOS, zonas.TRES):
        assert valores_alero[zona] == pytest.approx(valores_cubierta[zona])


def test_cubierta_componentes_valores_tabla_c534():
    """Los GCp de la Tabla C 5.3-4 (Figura 5.3-2C).

    Los esperados salen de las fórmulas de la tabla, que son otra forma de
    escribir la interpolación logarítmica entre los extremos de cada zona.
    """
    log10 = np.log10

    def esperado(area: float) -> dict:
        # zona: (área tramo constante, extremo, cst, pendiente, área tope, tope)
        pendientes = {
            enums.ZonaComponenteCubiertaEdificio.UNO: (
                1,
                -1.5,
                -1.5,
                0.5380,
                20,
                -0.8,
            ),
            enums.ZonaComponenteCubiertaEdificio.DOS: (1, -2.5, -2.5, 1.300, 10, -1.2),
            enums.ZonaComponenteCubiertaEdificio.TRES: (1, -3.0, -3.0, 1.600, 10, -1.4),
        }
        negativos = {}
        for zona, (area_a, extremo, cst, pendiente, area_b, tope) in pendientes.items():
            if area <= area_a:
                negativos[zona] = extremo
            elif area <= area_b:
                negativos[zona] = cst + pendiente * log10(area)
            else:
                negativos[zona] = tope
        if area <= 1:
            positivo = 0.6
        elif area <= 20:
            positivo = 0.6 - 0.2306 * log10(area)
        else:
            positivo = 0.3
        negativos[enums.ZonaComponenteCubiertaEdificio.TODAS] = positivo
        return negativos

    for area in (0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 60.0):
        valores_cp = _valores_por_zona(_cubierta_componentes(area, angulo=25))
        assert valores_cp == pytest.approx(esperado(area), abs=0.001)


def test_cubierta_componentes_alero_tabla_c534():
    """El alero de la Tabla C 5.3-4 usa la superficie superior de la cubierta.

    Igual que en la Tabla C 5.3-3, la Nota de la Figura 5.3-2C envía los
    voladizos al Art. 5.7 (pendiente, ver issue): el alero toma los valores de
    la cubierta sin el positivo de la zona "todas".
    """
    cubierta = _cubierta_componentes(5, angulo=25)
    alero = _cubierta_componentes(5, angulo=25, es_alero=True)
    zonas = enums.ZonaComponenteCubiertaEdificio
    valores_cubierta = _valores_por_zona(cubierta)
    valores_alero = _valores_por_zona(alero)
    assert zonas.TODAS not in valores_alero
    for zona in (zonas.UNO, zonas.DOS, zonas.TRES):
        assert valores_alero[zona] == pytest.approx(valores_cubierta[zona])


def test_cubierta_componentes_valores_tabla_c535():
    """Los GCp de la Tabla C 5.3-5 (Figura 5.3-2D).

    Los esperados salen de las fórmulas de la tabla, que son otra forma de
    escribir la interpolación logarítmica entre los extremos de cada zona.
    """
    log10 = np.log10

    def esperado(area: float) -> dict:
        # zona: (área tramo constante, extremo, cst, pendiente, área tope, tope)
        pendientes = {
            enums.ZonaComponenteCubiertaEdificio.UNO: (1, -1.8, -1.8, 1.000, 10, -0.8),
            enums.ZonaComponenteCubiertaEdificio.DOS: (1, -2.0, -2.0, 0.7686, 20, -1.0),
            enums.ZonaComponenteCubiertaEdificio.TRES: (
                1,
                -2.5,
                -2.5,
                1.1529,
                20,
                -1.0,
            ),
        }
        negativos = {}
        for zona, (area_a, extremo, cst, pendiente, area_b, tope) in pendientes.items():
            if area <= area_a:
                negativos[zona] = extremo
            elif area <= area_b:
                negativos[zona] = cst + pendiente * log10(area)
            else:
                negativos[zona] = tope
        if area <= 1:
            positivo = 0.9
        elif area <= 20:
            positivo = 0.9 - 0.3074 * log10(area)
        else:
            positivo = 0.5
        negativos[enums.ZonaComponenteCubiertaEdificio.TODAS] = positivo
        return negativos

    for area in (0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 60.0):
        valores_cp = _valores_por_zona(_cubierta_componentes(area, angulo=36))
        assert valores_cp == pytest.approx(esperado(area), abs=0.001)


def test_cubierta_componentes_alero_tabla_c535():
    """El alero de la Tabla C 5.3-5 usa la superficie superior de la cubierta.

    Igual que en las Tablas C 5.3-3 y 5.3-4, la Nota de la Figura 5.3-2D envía
    los voladizos al Art. 5.7 (pendiente, ver issue): el alero toma los valores
    de la cubierta sin el positivo de la zona "todas".
    """
    cubierta = _cubierta_componentes(5, angulo=36)
    alero = _cubierta_componentes(5, angulo=36, es_alero=True)
    zonas = enums.ZonaComponenteCubiertaEdificio
    valores_cubierta = _valores_por_zona(cubierta)
    valores_alero = _valores_por_zona(alero)
    assert zonas.TODAS not in valores_alero
    for zona in (zonas.UNO, zonas.DOS, zonas.TRES):
        assert valores_alero[zona] == pytest.approx(valores_cubierta[zona])


def test_cubierta_componentes_valores_figura_5_3_5a():
    """Los GCp de la Figura 5.3-5A.

    Los esperados salen de las fórmulas de la figura, que son otra forma de
    escribir la interpolación logarítmica entre los extremos de cada zona. La
    Zona 1 es constante en -1,1 para todo el rango de áreas (0,1 a 100 m²); el
    resto interpola entre 1 y 10 m².
    """
    log10 = np.log10

    def esperado(area: float) -> dict:
        negativos = {enums.ZonaComponenteCubiertaEdificio.UNO: -1.1}
        # zona: (extremo, cst, pendiente, tope). Todas interpolan entre 1 y
        # 10 m², así que la pendiente es el recorrido en un orden de magnitud.
        pendientes = {
            enums.ZonaComponenteCubiertaEdificio.DOS: (-1.3, -1.3, 0.1, -1.2),
            enums.ZonaComponenteCubiertaEdificio.DOS_PRIMA: (-1.6, -1.6, 0.1, -1.5),
            enums.ZonaComponenteCubiertaEdificio.TRES: (-1.8, -1.8, 0.6, -1.2),
            enums.ZonaComponenteCubiertaEdificio.TRES_PRIMA: (-2.6, -2.6, 1.0, -1.6),
        }
        for zona, (extremo, cst, pendiente, tope) in pendientes.items():
            if area <= 1:
                negativos[zona] = extremo
            elif area <= 10:
                negativos[zona] = cst + pendiente * log10(area)
            else:
                negativos[zona] = tope
        if area <= 1:
            positivo = 0.3
        elif area <= 10:
            positivo = 0.3 - 0.1 * log10(area)
        else:
            positivo = 0.2
        negativos[enums.ZonaComponenteCubiertaEdificio.TODAS] = positivo
        return negativos

    for area in (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 100.0):
        valores_cp = _valores_por_zona(
            _cubierta_componentes(
                area, angulo=8, tipo_cubierta=enums.TipoCubierta.UN_AGUA
            )
        )
        assert valores_cp == pytest.approx(esperado(area), abs=0.001)


def test_cubierta_componentes_alero_figura_5_3_5a():
    """El alero de la Figura 5.3-5A usa la superficie superior de la cubierta.

    La Figura no menciona el voladizo; por el Art. 5.7 (pendiente, ver issue)
    el alero toma los valores de la cubierta sin el positivo de la zona
    "todas", igual que en las Tablas C 5.3-3, 5.3-4 y 5.3-5.
    """
    cubierta = _cubierta_componentes(
        5, angulo=8, tipo_cubierta=enums.TipoCubierta.UN_AGUA
    )
    alero = _cubierta_componentes(
        5, angulo=8, tipo_cubierta=enums.TipoCubierta.UN_AGUA, es_alero=True
    )
    zonas = enums.ZonaComponenteCubiertaEdificio
    valores_cubierta = _valores_por_zona(cubierta)
    valores_alero = _valores_por_zona(alero)
    assert zonas.TODAS not in valores_alero
    for zona in (
        zonas.UNO,
        zonas.DOS,
        zonas.DOS_PRIMA,
        zonas.TRES,
        zonas.TRES_PRIMA,
    ):
        assert valores_alero[zona] == pytest.approx(valores_cubierta[zona])


def test_cubierta_componentes_valores_figura_5_3_5b():
    """Los GCp de la Figura 5.3-5B.

    Los esperados salen de las fórmulas de la figura, que son otra forma de
    escribir la interpolación logarítmica entre los extremos de cada zona.
    Todas interpolan entre 1 y 10 m², así que la pendiente es el recorrido en
    un orden de magnitud.
    """
    log10 = np.log10

    def esperado(area: float) -> dict:
        # zona: (extremo, cst, pendiente, tope).
        pendientes = {
            enums.ZonaComponenteCubiertaEdificio.UNO: (-1.3, -1.3, 0.2, -1.1),
            enums.ZonaComponenteCubiertaEdificio.DOS: (-1.6, -1.6, 0.4, -1.2),
            enums.ZonaComponenteCubiertaEdificio.TRES: (-2.9, -2.9, 0.9, -2.0),
        }
        negativos = {}
        for zona, (extremo, cst, pendiente, tope) in pendientes.items():
            if area <= 1:
                negativos[zona] = extremo
            elif area <= 10:
                negativos[zona] = cst + pendiente * log10(area)
            else:
                negativos[zona] = tope
        if area <= 1:
            positivo = 0.4
        elif area <= 10:
            positivo = 0.4 - 0.1 * log10(area)
        else:
            positivo = 0.3
        negativos[enums.ZonaComponenteCubiertaEdificio.TODAS] = positivo
        return negativos

    for area in (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0):
        valores_cp = _valores_por_zona(
            _cubierta_componentes(
                area, angulo=20, tipo_cubierta=enums.TipoCubierta.UN_AGUA
            )
        )
        assert valores_cp == pytest.approx(esperado(area), abs=0.001)


def test_cubierta_componentes_alero_figura_5_3_5b():
    """El alero de la Figura 5.3-5B usa la superficie superior de la cubierta.

    Igual que en la Figura 5.3-5A: por el Art. 5.7 (pendiente, ver issue) el
    alero toma los valores de la cubierta sin el positivo de la zona "todas".
    """
    cubierta = _cubierta_componentes(
        5, angulo=20, tipo_cubierta=enums.TipoCubierta.UN_AGUA
    )
    alero = _cubierta_componentes(
        5, angulo=20, tipo_cubierta=enums.TipoCubierta.UN_AGUA, es_alero=True
    )
    zonas = enums.ZonaComponenteCubiertaEdificio
    valores_cubierta = _valores_por_zona(cubierta)
    valores_alero = _valores_por_zona(alero)
    assert zonas.TODAS not in valores_alero
    for zona in (zonas.UNO, zonas.DOS, zonas.TRES):
        assert valores_alero[zona] == pytest.approx(valores_cubierta[zona])


def test_cubierta_componentes_valores_tabla_c532():
    """Los GCp de la Tabla C 5.3-2, cubierta sin voladizo.

    Los esperados salen de las fórmulas de la tabla, que son otra forma de
    escribir la interpolación logarítmica entre los extremos de cada zona.
    """
    log10 = np.log10

    def esperado(area: float) -> dict:
        if area <= 10:
            uno_prima = -0.9
        elif area <= 100:
            uno_prima = -1.4 + 0.5 * log10(area)
        else:
            uno_prima = -0.4
        negativos = {enums.ZonaComponenteCubiertaEdificio.UNO_PRIMA: uno_prima}
        pendientes = {
            enums.ZonaComponenteCubiertaEdificio.UNO: (-1.7, 0.4120, -1.0),
            enums.ZonaComponenteCubiertaEdificio.DOS: (-2.3, 0.5297, -1.4),
            enums.ZonaComponenteCubiertaEdificio.TRES: (-3.2, 1.0595, -1.4),
        }
        for zona, (cp_minimo, pendiente, cp_maximo) in pendientes.items():
            if area <= 1:
                negativos[zona] = cp_minimo
            elif area <= 50:
                negativos[zona] = cp_minimo + pendiente * log10(area)
            else:
                negativos[zona] = cp_maximo
        if area <= 1:
            positivo = 0.3
        elif area <= 10:
            positivo = 0.3 - 0.1 * log10(area)
        else:
            positivo = 0.2
        negativos[enums.ZonaComponenteCubiertaEdificio.TODAS] = positivo
        return negativos

    for area in (0.5, 1.0, 5.0, 10.0, 30.0, 50.0, 120.0):
        valores_cp = _valores_por_zona(_cubierta_componentes(area))
        assert valores_cp == pytest.approx(esperado(area), abs=0.001)


def test_cubierta_componentes_alero_tabla_c532():
    """Los GCp de la Tabla C 5.3-2, bloque "Negativo con voladizo".

    Las Zonas 1 y 1' comparten curva y tienen dos tramos log. El alero no
    lleva valores positivos: la Figura 5.3-2A no los grafica.
    """
    log10 = np.log10

    def esperado(area: float) -> dict:
        if area <= 1:
            uno = -1.7
        elif area <= 10:
            uno = -1.7 + 0.1 * log10(area)
        elif area <= 50:
            uno = -2.4584 + 0.8584 * log10(area)
        else:
            uno = -1.0
        valores = {
            enums.ZonaComponenteCubiertaEdificio.UNO: uno,
            enums.ZonaComponenteCubiertaEdificio.UNO_PRIMA: uno,
        }
        pendientes = {
            enums.ZonaComponenteCubiertaEdificio.DOS: (-2.3, 0.7063, -1.1),
            enums.ZonaComponenteCubiertaEdificio.TRES: (-3.2, 1.2360, -1.1),
        }
        for zona, (cp_minimo, pendiente, cp_maximo) in pendientes.items():
            if area <= 1:
                valores[zona] = cp_minimo
            elif area <= 50:
                valores[zona] = cp_minimo + pendiente * log10(area)
            else:
                valores[zona] = cp_maximo
        return valores

    for area in (0.5, 1.0, 5.0, 10.0, 30.0, 50.0, 80.0):
        valores_cp = _valores_por_zona(_cubierta_componentes(area, es_alero=True))
        assert enums.ZonaComponenteCubiertaEdificio.TODAS not in valores_cp
        assert valores_cp == pytest.approx(esperado(area), abs=0.001)


def _valores_por_zona_y_signo(cubierta: CubiertaComponentes) -> dict:
    """Los valores de GCp indexados por zona y signo del coeficiente externo.

    Args:
        cubierta: La instancia de la que se leen las entradas.

    Returns:
        El valor de cada zona para cada signo.
    """
    return {
        (entrada.zona_componente, entrada.tipo_presion): entrada.valor
        for entrada in cubierta.entradas
    }


def test_cubierta_componentes_nota_parapeto_tabla_c532():
    """Nota 5: con parapeto de 1 m o más la Zona 3 negativa iguala a la Zona 2."""
    zonas = enums.ZonaComponenteCubiertaEdificio
    negativa = enums.TipoPresionComponentesParedesCubierta.NEGATIVA

    sin_parapeto = _valores_por_zona_y_signo(_cubierta_componentes(5))
    assert sin_parapeto[(zonas.TRES, negativa)] != pytest.approx(
        sin_parapeto[(zonas.DOS, negativa)]
    )

    con_parapeto = _valores_por_zona_y_signo(_cubierta_componentes(5, parapeto=1))
    assert con_parapeto[(zonas.TRES, negativa)] == pytest.approx(
        con_parapeto[(zonas.DOS, negativa)]
    )


def test_cubierta_componentes_nota_parapeto_positivos_tabla_c532():
    """Nota 5: con parapeto, el positivo de las Zonas 2 y 3 es el de pared.

    La Nota iguala los valores positivos de las Zonas 2 y 3 a los de las Zonas
    de pared 4 y 5 de la Figura 5.3-1, que la Tabla C 5.3-1 no distingue entre
    sí. Las Zonas 1' y 1 se quedan con el positivo único de la zona "todas".
    """
    zonas = enums.ZonaComponenteCubiertaEdificio
    positiva = enums.TipoPresionComponentesParedesCubierta.POSITIVA
    area = 5.0

    sin_parapeto = _valores_por_zona_y_signo(_cubierta_componentes(area))
    assert (zonas.DOS, positiva) not in sin_parapeto
    assert (zonas.TRES, positiva) not in sin_parapeto

    con_parapeto = _valores_por_zona_y_signo(_cubierta_componentes(area, parapeto=1))
    esperado = cp_positivo_paredes(area, angulo_cubierta=4)
    assert con_parapeto[(zonas.DOS, positiva)] == pytest.approx(esperado)
    assert con_parapeto[(zonas.TRES, positiva)] == pytest.approx(esperado)
    # El positivo único sigue estando, para las Zonas 1' y 1.
    assert con_parapeto[(zonas.TODAS, positiva)] == pytest.approx(
        sin_parapeto[(zonas.TODAS, positiva)]
    )
    # Y coincide con el positivo que da la propia clase de paredes.
    paredes = _paredes_componentes(area, angulo=4)
    valores_paredes = {
        entrada.zona_componente: entrada.valor for entrada in paredes.entradas
    }
    assert esperado == pytest.approx(
        valores_paredes[enums.ZonaComponenteParedEdificio.TODAS]
    )


def test_cubierta_componentes_alero_sin_positivos_con_parapeto():
    """La Nota 5 es de la cubierta: el alero no gana valores positivos."""
    entradas = _cubierta_componentes(5, parapeto=1, es_alero=True).entradas
    assert all(
        entrada.tipo_presion is enums.TipoPresionComponentesParedesCubierta.NEGATIVA
        for entrada in entradas
    )


def test_cubierta_componentes_benchmark_calcpad():
    """Valida los valores de GCp contra el script de Calcpad para la Tabla C 5.3-2.

    Parámetros de entrada:
    - Cubierta a dos aguas, θ = 4°, h = 8 m, sin parapeto
    - Áreas que barren los tres tramos de cada zona y todos los quiebres de la
      tabla: los de las Zonas 1, 2 y 3 y del alero (1 y 50 m²), el del positivo
      (10 m²), los de la Zona 1\' (10 y 100 m²) y el del segundo tramo del
      alero (10 m²)
    """
    zonas = enums.ZonaComponenteCubiertaEdificio
    # area: (positivo, zona 1', zona 1, zona 2, zona 3)
    referencias_cubierta = {
        0.5: (0.3, -0.9, -1.7, -2.3, -3.2),
        1.0: (0.3, -0.9, -1.7, -2.3, -3.2),
        5.0: (0.2301, -0.9, -1.412, -1.9298, -2.4594),
        10.0: (0.2, -0.9, -1.288, -1.7703, -2.1405),
        20.0: (0.2, -0.74949, -1.164, -1.6108, -1.8216),
        50.0: (0.2, -0.55051, -1.0, -1.4, -1.4),
        80.0: (0.2, -0.44846, -1.0, -1.4, -1.4),
        100.0: (0.2, -0.4, -1.0, -1.4, -1.4),
        150.0: (0.2, -0.4, -1.0, -1.4, -1.4),
    }
    # area: (zonas 1 y 1', zona 2, zona 3). El alero no lleva positivo.
    referencias_alero = {
        0.5: (-1.7, -2.3, -3.2),
        1.0: (-1.7, -2.3, -3.2),
        5.0: (-1.6301, -1.8063, -2.3361),
        10.0: (-1.6, -1.5937, -1.964),
        20.0: (-1.3416, -1.3811, -1.5919),
        50.0: (-1.0, -1.1, -1.1),
        80.0: (-1.0, -1.1, -1.1),
        100.0: (-1.0, -1.1, -1.1),
        150.0: (-1.0, -1.1, -1.1),
    }
    casos = (
        (
            referencias_cubierta,
            False,
            (zonas.TODAS, zonas.UNO_PRIMA, zonas.UNO, zonas.DOS, zonas.TRES),
        ),
        (
            referencias_alero,
            True,
            (zonas.UNO_PRIMA, zonas.DOS, zonas.TRES),
        ),
    )
    for referencias, es_alero, claves in casos:
        for area, valores_calcpad in referencias.items():
            esperados = dict(zip(claves, valores_calcpad, strict=True))
            if es_alero:
                esperados[zonas.UNO] = esperados[zonas.UNO_PRIMA]
            obtenidos = _valores_por_zona(
                _cubierta_componentes(area, es_alero=es_alero)
            )
            assert obtenidos == pytest.approx(esperados, abs=0.001)


def test_presion_minima_componentes():
    """Art. 5.2.2: la presión neta de C&R no baja de 0,80 kN/m² en ningún signo.

    El valor del CIRSOC 102-2025 reemplaza a los 500 N/m² del Art. 1.4.2 del
    reglamento 2005.
    """
    assert presion_minima(120) == pytest.approx(800)
    assert presion_minima(-120) == pytest.approx(-800)
    # Por encima del mínimo el valor no se toca, y el signo se conserva.
    assert presion_minima(1500) == pytest.approx(1500)
    assert presion_minima(-1500) == pytest.approx(-1500)

    # Borde conocido: el signo sale de la propia presión, así que una neta
    # exactamente nula se queda en cero en vez de subir a ±800. Es inalcanzable
    # en la práctica -pide que el coeficiente externo iguale al interno- y la
    # decisión de qué signo darle está en el issue #10.
    assert presion_minima(0) == 0


def test_presion_minima_se_aplica_a_los_componentes(edificio: Edificio):
    """Ninguna fila de componentes queda por debajo del mínimo, y el SPRFV no lo usa."""
    filas_componentes = edificio.resultados_componentes
    assert filas_componentes
    for fila in filas_componentes:
        for presion in fila.presiones:
            assert abs(presion) >= 800 - 1e-9

    # El mínimo es de componentes: el SPRFV tiene el suyo, y es sólo una nota.
    assert any(
        abs(presion) < 800
        for fila in edificio.resultados_sprfv
        for presion in fila.presiones
    )


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
