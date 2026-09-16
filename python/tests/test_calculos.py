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

from itertools import pairwise

import numpy as np
import pytest

from zonda import enums
from zonda.cirsoc import Cartel, CubiertaAislada, Edificio, cp
from zonda.cirsoc.cp.edificio import (
    CubiertaComponentes,
    ParapetoComponentes,
    ParedesComponentes,
    cp_positivo_paredes,
    distancia_a,
)
from zonda.cirsoc.factores import Rafaga, Topografia, factor_altitud
from zonda.cirsoc.presiones.base import presion_minima
from zonda.cirsoc.presiones.cartel import PRESION_MINIMA_OTRAS_ESTRUCTURAS
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


# --- Cartel: Figura 4.4-1 -------------------------------------------------


def test_cartel_calcula(cartel: Cartel):
    assert cartel.presiones is not None
    assert cartel.presiones.fuerzas_totales[enums.CasoCartel.CASO_A] > 0


def test_cartel_la_presion_de_velocidad_se_evalua_a_la_punta(cartel: Cartel):
    """La Ec. 4.4-1 usa qh evaluada a la altura h que define la Figura 4.4-1."""
    fila = cartel.resultados.filtrar(caso=enums.CasoCartel.CASO_A).unica()
    assert fila.q.altura == pytest.approx(cartel.altura_superior)


def test_cartel_valores_de_referencia(cartel: Cartel):
    """Valores de referencia bajo constantes de exposición CIRSOC 102-2025.

    El cartel tiene s = 5 m, B = 10 m y h = 10 m: s/h = 0.5 y B/s = 2, así que
    el Caso A/B cae en la celda (0.5, 2) de la Figura 4.4-1 y el Caso C en las
    celdas de la columna B/s = 2. Si numpy o el propio cálculo cambian de
    resultado, este test lo detecta.
    """
    fila_a = cartel.resultados.filtrar(caso=enums.CasoCartel.CASO_A).unica()
    assert fila_a.q.kz == pytest.approx(0.7058033400746822)
    assert fila_a.q.valor == pytest.approx(744.7116314504742, rel=1e-6)
    assert fila_a.cf == pytest.approx(1.70)
    assert fila_a.presion == pytest.approx(1076.1083074459352, rel=1e-6)
    assert fila_a.fuerza == pytest.approx(53805.41537229676, rel=1e-6)

    fila_c = cartel.resultados.filtrar(caso=enums.CasoCartel.CASO_C)
    assert [f.cf for f in fila_c] == pytest.approx([2.25, 1.50])
    assert fila_c[0].presion == pytest.approx(1424.260995149032, rel=1e-6)


def test_cartel_presion_minima_articulo_4_8():
    """Art. 4.8: la fuerza de diseño no baja de 0,80 kN/m² por el área A_f.

    Con una velocidad baja varias filas calculadas quedan por debajo del
    mínimo: el recorte deja la presión de cada fila en 800 N/m² y, con ella,
    la fuerza de cada caso sobre el área proyectada. En el Caso C, la suma de
    las fuerzas de las regiones cubre el mínimo del cartel completo.
    """
    cartel = Cartel(
        profundidad=1,
        ancho=10,
        altura_inferior=5,
        altura_superior=10,
        velocidad=25,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
    filas = cartel.resultados
    assert filas
    assert any(
        fila.q.valor * fila.factor_rafaga * fila.cf < PRESION_MINIMA_OTRAS_ESTRUCTURAS
        for fila in filas
    )
    for fila in filas:
        esperado = max(
            fila.q.valor * fila.factor_rafaga * fila.cf,
            PRESION_MINIMA_OTRAS_ESTRUCTURAS,
        )
        assert fila.presion == pytest.approx(esperado)
        assert fila.fuerza == pytest.approx(fila.presion * fila.area)

    area_total = cartel.presiones.area
    for fuerza in cartel.presiones.fuerzas_totales.values():
        assert fuerza >= 800 * area_total - 1e-9


def test_cartel_casos_a_y_b_comparten_coeficiente_y_fuerza(cartel: Cartel):
    """La tabla de la Figura 4.4-1 es común a los Casos A y B: sólo cambia
    dónde actúa la fuerza resultante."""
    fila_a = cartel.resultados.filtrar(caso=enums.CasoCartel.CASO_A).unica()
    fila_b = cartel.resultados.filtrar(caso=enums.CasoCartel.CASO_B).unica()
    assert fila_a.cf == fila_b.cf
    assert fila_a.fuerza == fila_b.fuerza
    assert fila_b.excentricidad == pytest.approx(0.2 * cartel.ancho)
    assert fila_a.excentricidad is None


@pytest.mark.parametrize(
    ("altura_inferior", "altura_neta", "altura_superior", "ancho", "esperado"),
    [
        (0, 5, 5, 5, 1.45),  # s/h = 1, B/s = 1
        (1, 9, 10, 18, 1.50),  # s/h = 0.9, B/s = 2
        (3, 7, 10, 35, 1.55),  # s/h = 0.7, B/s = 5
        (5, 5, 10, 10, 1.70),  # s/h = 0.5, B/s = 2
        (7, 3, 10, 60, 1.85),  # s/h = 0.3, B/s = 20
        (20, 5, 25, 20, 1.80),  # s/h = 0.2, B/s = 4
        (35, 5, 40, 50, 1.85),  # s/h = 0.125 (fila ≤ 0.16), B/s = 10
        (0, 5, 5, 500, 1.30),  # s/h = 1, B/s = 100 (columna ≥ 45)
        (0, 5, 5, 0.1, 1.80),  # s/h = 1, B/s = 0.02 (columna ≤ 0.05)
    ],
)
def test_cartel_cf_casos_ab_valores_de_tabla(
    altura_inferior, altura_neta, altura_superior, ancho, esperado
):
    """Celdas y clamps de la tabla de los Casos A y B (Figura 4.4-1)."""
    cf = cp.Cartel(
        altura_inferior, altura_neta, altura_superior, ancho, profundidad=1
    ).cf_casos_ab
    assert cf == pytest.approx(esperado)


def test_cartel_cf_casos_ab_interpolacion():
    """Interpolación bilineal entre celdas: s/h = 0.625 y B/s = 1.5 da 1.6625."""
    cf = cp.Cartel(0, 5, 8, 7.5, profundidad=1).cf_casos_ab
    assert cf == pytest.approx(1.6625)


def test_cartel_cf_caso_c_no_aplica_con_b_s_menor_a_2():
    cf = cp.Cartel(5, 5, 10, 8, profundidad=1)  # B/s = 1.6
    assert not cf.aplica_caso_c
    assert cf.limites_regiones == {}
    assert cf.cf_por_region == {}


@pytest.mark.parametrize(
    ("ancho", "esperado"),
    [
        (10, [2.25, 1.50]),  # B/s = 2
        (22.5, [3.00, 1.95, 1.375, 1.075]),  # B/s = 4.5, interpolado
        (57.5, [3.875, 2.525, 1.925, 1.225, 1.15, 0.925, 0.55]),  # B/s = 11.5
        (225, [4.30, 2.55, 1.95, 1.85, 1.85, 1.10, 0.55]),  # B/s = 45
        (450, [4.30, 2.55, 1.95, 1.85, 1.85, 1.10, 0.55]),  # B/s ≥ 45
    ],
)
def test_cartel_cf_caso_c_por_region(ancho, esperado):
    """La tabla del Caso C con s/h = 0.5, interpolando en B/s cuando hace falta."""
    cf = cp.Cartel(5, 5, 10, ancho, profundidad=1)
    assert list(cf.cf_por_region.values()) == pytest.approx(esperado)


@pytest.mark.parametrize("b_s", [2, 3.7, 10, 11.5, 30, 100])
def test_cartel_las_regiones_cubren_el_ancho_sin_huecos(b_s):
    """Las regiones del Caso C tapan todo el ancho del cartel, sin solapes."""
    cf = cp.Cartel(5, 5, 10, 5 * b_s, profundidad=1)
    limites = sorted(cf.limites_regiones.values())
    assert limites[0][0] == pytest.approx(0)
    assert limites[-1][1] == pytest.approx(cf.ancho)
    for (_, fin_anterior), (inicio, _) in pairwise(limites):
        assert inicio == pytest.approx(fin_anterior)
    total = sum(fin - inicio for inicio, fin in limites)
    assert total == pytest.approx(cf.ancho)


def test_cartel_cf_caso_c_reduccion_de_s_h_mayor_a_08():
    """Nota 3: con s/h > 0.8 los Cf del Caso C se multiplican por (1.8 - s/h)."""
    cf = cp.Cartel(1, 9, 10, 18, profundidad=1)  # s/h = 0.9, B/s = 2
    assert list(cf.cf_por_region.values()) == pytest.approx([2.25 * 0.9, 1.50 * 0.9])


@pytest.mark.parametrize(
    ("esquina_retorno", "esperado_0_s"),
    [
        (0, 2.64),  # sin esquina de retorno
        (1, 2.64),  # Lr/s = 0.2 < 0.3: sin reducción
        (1.5, 2.376),  # Lr/s = 0.3: factor 0.9
        (5, 1.98),  # Lr/s = 1: factor 0.75
        (7.5, 1.782),  # Lr/s = 1.5: factor 0.675
        (10, 1.584),  # Lr/s = 2: factor 0.6
        (30, 1.584),  # Lr/s ≥ 2: factor 0.6
    ],
)
def test_cartel_cf_caso_c_esquina_de_retorno(esquina_retorno, esperado_0_s):
    """La esquina de retorno reduce los valores con asterisco: la primera
    región cuando B/s ≥ 5."""
    cf = cp.Cartel(0, 5, 5, 30, profundidad=1, esquina_retorno=esquina_retorno)
    assert cf.cf_por_region[enums.RegionCartel.REGION_0_S] == pytest.approx(
        esperado_0_s
    )


def test_cartel_cf_caso_c_esquina_de_retorno_no_aplica_con_b_s_menor_a_5():
    cf = cp.Cartel(5, 5, 10, 10, profundidad=1, esquina_retorno=5)
    assert cf.factor_esquina_retorno == 1.0
    assert cf.cf_por_region[enums.RegionCartel.REGION_0_S] == pytest.approx(2.25)


def test_cartel_factor_de_aberturas():
    """Nota 1: los Cf se multiplican por (1 - (1 - ε)^1.5)."""
    cf = cp.Cartel(5, 5, 10, 10, profundidad=1, epsilon=0.8)
    factor = 1 - (1 - 0.8) ** 1.5
    assert cf.factor_aberturas == pytest.approx(factor)
    assert cf.cf_casos_ab == pytest.approx(1.70 * factor)
    assert cf.cf_por_region[enums.RegionCartel.REGION_0_S] == pytest.approx(
        2.25 * factor
    )


def test_cartel_reducciones_de_doble_cara():
    """Nota 2: Rmin reduce el Cf de los Casos A y B y Rmax la excentricidad.

    Con t = 0.4 m, s = 5 m y B = 10 m: Rmin = 0.08 y Rmax = 0.04.
    """
    cf = cp.Cartel(5, 5, 10, 10, profundidad=0.4, doble_cara=True)
    assert cf.cf_casos_ab == pytest.approx(1.70 * (1 - 0.133 * 0.08))
    assert cf.excentricidad == pytest.approx((0.2 - 0.25 * 0.04) * 10)
    # El Caso C no lleva las reducciones de la doble cara.
    assert list(cf.cf_por_region.values()) == pytest.approx([2.25, 1.50])


def test_cartel_reducciones_de_doble_cara_fuera_de_rango():
    """Si Rmin o Rmax superan los límites de la Nota 2, no se reduce nada."""
    cf = cp.Cartel(5, 5, 10, 10, profundidad=5, doble_cara=True)
    # Rmin = 1.0 > 0.75 y Rmax = 0.5 > 0.4: ninguno de los dos alcanza.
    assert cf.cf_casos_ab == pytest.approx(1.70)
    assert cf.excentricidad == pytest.approx(0.2 * 10)


def test_cartel_epsilon_fuera_de_lineamientos():
    """La Figura 4.4-1 sólo cubre carteles llenos: aberturas menores al 30 %."""
    with pytest.raises(ValueError):
        cp.Cartel(5, 5, 10, 10, profundidad=1, epsilon=0.5)
    with pytest.raises(ValueError):
        cp.Cartel(5, 5, 10, 10, profundidad=1, epsilon=1.5)


@pytest.mark.parametrize("categoria_exp", list(enums.CategoriaExposicion))
def test_cartel_todas_las_categorias_de_exposicion(categoria_exp):
    cartel = Cartel(
        profundidad=1,
        ancho=10,
        altura_inferior=5,
        altura_superior=10,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=categoria_exp,
        considerar_topografia=False,
    )
    assert cartel.presiones.fuerzas_totales[enums.CasoCartel.CASO_A] > 0


def test_cubierta_aislada_calcula(cubierta_aislada: CubiertaAislada):
    assert cubierta_aislada.presiones is not None
    assert cubierta_aislada.cpn is not None


def _cpn_cubierta_aislada(cpn: cp.CubiertaAislada):
    """Los coeficientes indexados por dirección, caso y zona."""
    return {
        (entrada.direccion, entrada.caso, entrada.zona): entrada.valor
        for entrada in cpn.entradas
    }


def test_cpn_vertiente_unica_figura_2_4_4():
    """Valores de la Figura 2.4-4 a 15°, con y sin bloqueo."""
    cpn = cp.CubiertaAislada(enums.TipoCubierta.UN_AGUA, 15.0, False, 6.0, 10.0, 20.0)
    valores = _cpn_cubierta_aislada(cpn)
    g0 = enums.DireccionVientoCubiertaAislada.GAMMA_0
    g180 = enums.DireccionVientoCubiertaAislada.GAMMA_180
    a, b = enums.CasoCargaCubiertaAislada.CASO_A, enums.CasoCargaCubiertaAislada.CASO_B
    bar = enums.ZonaPresionCubiertaAislada.BARLOVENTO
    sot = enums.ZonaPresionCubiertaAislada.SOTAVENTO
    assert valores[(g0, a, bar)] == pytest.approx(-0.9)
    assert valores[(g0, a, sot)] == pytest.approx(-1.3)
    assert valores[(g0, b, bar)] == pytest.approx(-1.9)
    assert valores[(g0, b, sot)] == pytest.approx(0.0)
    assert valores[(g180, a, bar)] == pytest.approx(1.3)
    assert valores[(g180, a, sot)] == pytest.approx(1.6)
    assert valores[(g180, b, bar)] == pytest.approx(1.8)
    assert valores[(g180, b, sot)] == pytest.approx(0.6)

    cpn = cp.CubiertaAislada(enums.TipoCubierta.UN_AGUA, 15.0, True, 6.0, 10.0, 20.0)
    valores = _cpn_cubierta_aislada(cpn)
    assert valores[(g0, a, bar)] == pytest.approx(-1.1)
    assert valores[(g0, a, sot)] == pytest.approx(-1.5)
    assert valores[(g0, b, bar)] == pytest.approx(-2.1)
    assert valores[(g0, b, sot)] == pytest.approx(-0.6)
    assert valores[(g180, a, bar)] == pytest.approx(0.4)
    assert valores[(g180, a, sot)] == pytest.approx(-1.1)
    assert valores[(g180, b, bar)] == pytest.approx(1.2)
    assert valores[(g180, b, sot)] == pytest.approx(-0.3)


def test_cpn_vertiente_unica_interpolacion():
    """Interpolación lineal a 10°: 7,5° + un tercio del paso a 15° (γ = 0°)."""
    cpn = cp.CubiertaAislada(enums.TipoCubierta.UN_AGUA, 10.0, False, 6.0, 10.0, 20.0)
    valores = _cpn_cubierta_aislada(cpn)
    clave = (
        enums.DireccionVientoCubiertaAislada.GAMMA_0,
        enums.CasoCargaCubiertaAislada.CASO_A,
        enums.ZonaPresionCubiertaAislada.BARLOVENTO,
    )
    # CNW(7,5°) = -0,6 y CNW(15°) = -0,9; 10° está a 1/3 del intervalo.
    assert valores[clave] == pytest.approx(-0.7)


def test_cpn_vertiente_unica_menor_7_5_usa_valores_de_0():
    """Nota 3: para θ < 7,5° se usan los coeficientes de 0°."""
    cpn = cp.CubiertaAislada(enums.TipoCubierta.UN_AGUA, 3.0, False, 6.0, 10.0, 20.0)
    valores = _cpn_cubierta_aislada(cpn)
    g0 = enums.DireccionVientoCubiertaAislada.GAMMA_0
    g180 = enums.DireccionVientoCubiertaAislada.GAMMA_180
    a = enums.CasoCargaCubiertaAislada.CASO_A
    bar = enums.ZonaPresionCubiertaAislada.BARLOVENTO
    assert valores[(g0, a, bar)] == pytest.approx(1.2)
    # A 0° las dos direcciones comparten valores.
    assert valores[(g180, a, bar)] == pytest.approx(1.2)


def test_cpn_dos_aguas_figura_2_4_5():
    """Valores de la Figura 2.4-5 a 30°, con y sin bloqueo."""
    cpn = cp.CubiertaAislada(enums.TipoCubierta.DOS_AGUAS, 30.0, False, 8.0, 20.0, 30.0)
    valores = _cpn_cubierta_aislada(cpn)
    g0 = enums.DireccionVientoCubiertaAislada.GAMMA_0
    g180 = enums.DireccionVientoCubiertaAislada.GAMMA_180
    a, b = enums.CasoCargaCubiertaAislada.CASO_A, enums.CasoCargaCubiertaAislada.CASO_B
    bar = enums.ZonaPresionCubiertaAislada.BARLOVENTO
    sot = enums.ZonaPresionCubiertaAislada.SOTAVENTO
    assert valores[(g0, a, bar)] == pytest.approx(1.3)
    assert valores[(g0, a, sot)] == pytest.approx(0.3)
    assert valores[(g0, b, bar)] == pytest.approx(-0.1)
    assert valores[(g0, b, sot)] == pytest.approx(-0.9)
    # γ = 0° y 180° comparten tabla: la mitad de barlovento lleva CNW en
    # ambas direcciones (la cubierta es simétrica respecto de la cumbrera).
    assert valores[(g180, a, bar)] == pytest.approx(1.3)
    assert valores[(g180, a, sot)] == pytest.approx(0.3)

    cpn = cp.CubiertaAislada(enums.TipoCubierta.DOS_AGUAS, 30.0, True, 8.0, 20.0, 30.0)
    valores = _cpn_cubierta_aislada(cpn)
    assert valores[(g0, a, bar)] == pytest.approx(-0.7)
    assert valores[(g0, b, sot)] == pytest.approx(-1.1)


def test_cpn_dos_aguas_diedro_negativo_figura_2_4_6():
    """Valores de la Figura 2.4-6 a -15°, sin bloqueo."""
    cpn = cp.CubiertaAislada(
        enums.TipoCubierta.DOS_AGUAS, -15.0, False, 6.0, 20.0, 12.0
    )
    valores = _cpn_cubierta_aislada(cpn)
    g0 = enums.DireccionVientoCubiertaAislada.GAMMA_0
    a, b = enums.CasoCargaCubiertaAislada.CASO_A, enums.CasoCargaCubiertaAislada.CASO_B
    bar = enums.ZonaPresionCubiertaAislada.BARLOVENTO
    sot = enums.ZonaPresionCubiertaAislada.SOTAVENTO
    assert valores[(g0, a, bar)] == pytest.approx(-1.1)
    assert valores[(g0, a, sot)] == pytest.approx(0.4)
    assert valores[(g0, b, bar)] == pytest.approx(0.1)
    assert valores[(g0, b, sot)] == pytest.approx(1.1)
    assert cpn.entradas[0].referencia == "Figura 2.4-6"


def test_cpn_dos_aguas_angulo_menor_7_5_usa_vertiente_unica():
    """Notas 3 de las Figuras 2.4-5 y 2.4-6: valores de vertiente única a 0°."""
    cpn = cp.CubiertaAislada(enums.TipoCubierta.DOS_AGUAS, 5.0, False, 6.0, 20.0, 12.0)
    valores = _cpn_cubierta_aislada(cpn)
    g0 = enums.DireccionVientoCubiertaAislada.GAMMA_0
    a, b = enums.CasoCargaCubiertaAislada.CASO_A, enums.CasoCargaCubiertaAislada.CASO_B
    bar = enums.ZonaPresionCubiertaAislada.BARLOVENTO
    sot = enums.ZonaPresionCubiertaAislada.SOTAVENTO
    assert valores[(g0, a, bar)] == pytest.approx(1.2)
    assert valores[(g0, a, sot)] == pytest.approx(0.3)
    assert valores[(g0, b, bar)] == pytest.approx(-1.1)
    assert valores[(g0, b, sot)] == pytest.approx(-0.1)
    assert cpn.entradas[0].referencia == "Figura 2.4-4"


def test_cpn_viento_paralelo_figura_2_4_7():
    """Valores de la Figura 2.4-7 por banda, con y sin bloqueo."""
    cpn = cp.CubiertaAislada(enums.TipoCubierta.DOS_AGUAS, 30.0, False, 8.0, 20.0, 30.0)
    valores = _cpn_cubierta_aislada(cpn)
    g90 = enums.DireccionVientoCubiertaAislada.GAMMA_90
    a, b = enums.CasoCargaCubiertaAislada.CASO_A, enums.CasoCargaCubiertaAislada.CASO_B
    hasta_h = enums.ZonaPresionCubiertaAislada.HASTA_H
    entre = enums.ZonaPresionCubiertaAislada.ENTRE_H_Y_2H
    mayor = enums.ZonaPresionCubiertaAislada.MAYOR_2H
    assert valores[(g90, a, hasta_h)] == pytest.approx(-0.8)
    assert valores[(g90, b, hasta_h)] == pytest.approx(0.8)
    assert valores[(g90, a, entre)] == pytest.approx(-0.6)
    assert valores[(g90, b, entre)] == pytest.approx(0.5)
    assert valores[(g90, a, mayor)] == pytest.approx(-0.3)
    assert valores[(g90, b, mayor)] == pytest.approx(0.3)

    cpn = cp.CubiertaAislada(enums.TipoCubierta.DOS_AGUAS, 30.0, True, 8.0, 20.0, 30.0)
    valores = _cpn_cubierta_aislada(cpn)
    assert valores[(g90, a, hasta_h)] == pytest.approx(-1.2)
    assert valores[(g90, b, mayor)] == pytest.approx(0.3)


def test_cpn_zonas_de_bandas_segun_longitud():
    """Sólo se generan las bandas que caben en la longitud de la cubierta."""
    # Con h = 5 la banda central termina en 2h = 10 y la última empieza ahí:
    # con longitud 10 la banda x > 2h no existe.
    cpn = cp.CubiertaAislada(enums.TipoCubierta.UN_AGUA, 15.0, False, 5.0, 10.0, 10.0)
    zonas = {
        (entrada.direccion, entrada.zona)
        for entrada in cpn.entradas
        if entrada.direccion is enums.DireccionVientoCubiertaAislada.GAMMA_90
    }
    g90 = enums.DireccionVientoCubiertaAislada.GAMMA_90
    assert (g90, enums.ZonaPresionCubiertaAislada.MAYOR_2H) not in zonas
    assert (g90, enums.ZonaPresionCubiertaAislada.HASTA_H) in zonas
    assert (g90, enums.ZonaPresionCubiertaAislada.ENTRE_H_Y_2H) in zonas


def test_cubierta_aislada_presion_y_friccion(cubierta_aislada: CubiertaAislada):
    """p = qh·G·Cpn y p_fricción = Cf·qh·n, con n = 2 con flujo libre."""
    fila = cubierta_aislada.resultados.filtrar(
        direccion=enums.DireccionVientoCubiertaAislada.GAMMA_0,
        caso=enums.CasoCargaCubiertaAislada.CASO_A,
        zona=enums.ZonaPresionCubiertaAislada.BARLOVENTO,
    ).unica()
    assert fila.cpn == pytest.approx(1.1)
    assert fila.presion == pytest.approx(fila.q.valor * fila.factor_rafaga * fila.cpn)
    # Cf = 0,02 (Tabla 2.4-1, ondulaciones transversales) y dos superficies.
    assert fila.presion_friccion == pytest.approx(0.02 * 2 * fila.q.valor)


def test_cubierta_aislada_friccion_con_bloqueo():
    """Con flujo obstruido la fricción actúa sólo sobre la superficie superior."""
    cubierta = CubiertaAislada(
        ancho=10,
        longitud=20,
        altura_alero=5,
        altura_cumbrera=6,
        bloqueo=60,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        coeficiente_friccion=0.02,
        velocidad=45,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
    fila = cubierta.resultados.filtrar(
        direccion=enums.DireccionVientoCubiertaAislada.GAMMA_0,
        caso=enums.CasoCargaCubiertaAislada.CASO_A,
        zona=enums.ZonaPresionCubiertaAislada.BARLOVENTO,
    ).unica()
    assert fila.presion_friccion == pytest.approx(0.02 * fila.q.valor)


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


def test_cubierta_angulo_menor_diez_la_longitud_no_divide_zonas():
    """Regresión del issue #36: la longitud no agrega zonas con viento normal.

    Con cubierta de pequeña pendiente, las zonas de cubierta con viento
    normal a la cumbrera son las de la Figura 2.4-1 (cont.): de 0 a h/2, de
    h/2 a h, de h a 2h y de 2h al ancho. Si la longitud del edificio cae
    entre 2h y el ancho, dividía la última zona en dos y el cálculo fallaba
    por tener más zonas que coeficientes.
    """
    edificio = Edificio(
        ancho=22,
        longitud=17,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=7,
        tipo_cubierta=enums.TipoCubierta.UN_AGUA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
    cubierta_normal = edificio.resultados_sprfv.filtrar(
        zona=enums.ZonaEdificio.CUBIERTA,
        direccion=enums.DireccionVientoMetodoDireccionalSprfv.NORMAL,
        caso=None,
    )
    assert tuple(fila.rango for fila in cubierta_normal) == (
        (0, 3),
        (3, 6),
        (6, 12),
        (12, 22),
    )
    assert tuple(fila.cp for fila in cubierta_normal) == pytest.approx(
        (-0.9, -0.9, -0.5, -0.3)
    )


@pytest.mark.parametrize("longitud", (11, 12, 13, 14, 17, 20, 22, 25, 30))
@pytest.mark.parametrize(
    "tipo_cubierta", (enums.TipoCubierta.UN_AGUA, enums.TipoCubierta.DOS_AGUAS)
)
def test_cubierta_angulo_menor_diez_calcula_con_toda_longitud(tipo_cubierta, longitud):
    """Regresión del issue #36: el edificio calcula para toda longitud.

    Con cubierta de pequeña pendiente y longitudes cercanas a 2h o al ancho
    -o entre ambos-, el cálculo terminaba con más zonas que coeficientes.
    """
    edificio = Edificio(
        ancho=22,
        longitud=longitud,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=7,
        tipo_cubierta=tipo_cubierta,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
    )
    assert edificio.resultados_sprfv.filas


def test_alero_referencia_articulo_2_4_4():
    """El alero a barlovento cita el Art. 2.4.4 y el resto sólo la figura.

    A barlovento el coeficiente combina la superficie superior de la Figura
    2.4-1 con la presión externa positiva de la superficie inferior del
    voladizo, Cp = +0.8 (Art. 2.4.4), así que la referencia lo menciona.
    """
    edificio_pequeno = _edificio_angulo_pequeno(alero=1)
    edificio_grande = Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=8,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=1,
    )
    for edificio in (edificio_pequeno, edificio_grande):
        alero = edificio.resultados_sprfv.filtrar(zona=enums.ZonaEdificio.ALERO)
        for fila in alero.filtrar(posicion=enums.PosicionCubiertaAleroSprfv.BARLOVENTO):
            assert fila.referencia == "Figura 2.4-1 (cont.) y Art. 2.4.4"
        for fila in alero.filtrar(posicion=enums.PosicionCubiertaAleroSprfv.SOTAVENTO):
            assert fila.referencia == "Figura 2.4-1 (cont.)"
        for fila in alero.filtrar(
            direccion=enums.DireccionVientoMetodoDireccionalSprfv.PARALELO
        ):
            assert fila.referencia == "Figura 2.4-1 (cont.)"


def test_alero_barlovento_combina_superficie_inferior():
    """El cp del alero a barlovento es el de la cubierta menos 0.8.

    El Art. 2.4.4 combina la presión externa positiva de la superficie
    inferior del voladizo, Cp = +0.8, con la de la superficie superior de la
    Figura 2.4-1: con el mismo q y G la combinación equivale a restar 0.8 al
    coeficiente superior, para ambos casos de presión a barlovento.
    """
    edificio = Edificio(
        ancho=20,
        longitud=30,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=8,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=1,
    )
    resultados = edificio.resultados_sprfv
    normal = enums.DireccionVientoMetodoDireccionalSprfv.NORMAL
    for caso in (
        enums.TipoPresionCubiertaBarloventoSprfv.NEGATIVA,
        enums.TipoPresionCubiertaBarloventoSprfv.POSITIVA,
    ):
        cp_cubierta = (
            resultados.filtrar(
                zona=enums.ZonaEdificio.CUBIERTA,
                direccion=normal,
                caso=caso,
            )
            .filtrar(posicion=enums.PosicionCubiertaAleroSprfv.BARLOVENTO)
            .unica()
            .cp
        )
        cp_alero = (
            resultados.filtrar(
                zona=enums.ZonaEdificio.ALERO,
                direccion=normal,
                caso=caso,
            )
            .filtrar(posicion=enums.PosicionCubiertaAleroSprfv.BARLOVENTO)
            .unica()
            .cp
        )
        assert cp_alero == pytest.approx(cp_cubierta - 0.8)


def test_cubierta_aislada_angulo_fuera_de_lineamientos_es_rechazada():
    """El CIRSOC cubre ángulos de 0° a 45° (|ángulo| para dos aguas)."""
    datos_base = {
        "ancho": 10,
        "longitud": 20,
        "altura_alero": 5,
        "bloqueo": 0,
        "coeficiente_friccion": 0.02,
        "velocidad": 45,
        "categoria_exp": enums.CategoriaExposicion.B,
        "considerar_topografia": False,
    }
    # A dos aguas el diedro puede ser negativo, pero no pasar de 45°.
    with pytest.raises(ErrorLineamientos, match="ángulo"):
        CubiertaAislada(
            altura_cumbrera=11,
            tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
            **datos_base,
        )
    with pytest.raises(ErrorLineamientos, match="ángulo"):
        CubiertaAislada(
            altura_cumbrera=16,
            tipo_cubierta=enums.TipoCubierta.UN_AGUA,
            **datos_base,
        )
    with pytest.raises(ErrorLineamientos, match="ángulo"):
        CubiertaAislada(
            altura_cumbrera=3,
            tipo_cubierta=enums.TipoCubierta.UN_AGUA,
            **datos_base,
        )


def test_cubierta_aislada_relacion_h_l_fuera_de_lineamientos_es_rechazada():
    """Las Figuras 2.4-4 a 2.4-7 exigen 0,25 ≤ h/L ≤ 1,0 en cada dirección."""
    with pytest.raises(ErrorLineamientos, match="h/L"):
        CubiertaAislada(
            ancho=30,
            longitud=30,
            altura_alero=5,
            altura_cumbrera=5.1,
            bloqueo=0,
            tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
            coeficiente_friccion=0.02,
            velocidad=45,
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
            bloqueo=0,
            tipo_cubierta=enums.TipoCubierta.PLANA,
            coeficiente_friccion=0.02,
            velocidad=45,
            categoria_exp=enums.CategoriaExposicion.B,
            considerar_topografia=False,
        )


def _componentes_aislada(cpn: cp.ComponentesCubiertaAislada, componente: str):
    """Los coeficientes de un componente indexados por zona y signo."""
    return {
        (entrada.zona_componente, entrada.tipo_presion): entrada.valor
        for entrada in cpn.entradas
        if entrada.componente == componente
    }


def test_componentes_aislada_figura_5_5_1():
    """Valores de la Figura 5.5-1 a 15°, con y sin bloqueo, área ≤ a²."""
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 15.0, False, 6.0, 10.0, 20.0, {"Chapa": 0.5}
    )
    valores = _componentes_aislada(cpn, "Chapa")
    uno, dos, tres = (
        enums.ZonaComponenteCubiertaAislada.UNO,
        enums.ZonaComponenteCubiertaAislada.DOS,
        enums.ZonaComponenteCubiertaAislada.TRES,
    )
    pos = enums.TipoPresionComponentesParedesCubierta.POSITIVA
    neg = enums.TipoPresionComponentesParedesCubierta.NEGATIVA
    assert cpn.referencia == "Figura 5.5-1"
    assert cpn.distancia_a == pytest.approx(1.0)
    assert valores[(tres, pos)] == pytest.approx(3.6)
    assert valores[(tres, neg)] == pytest.approx(-3.8)
    assert valores[(dos, pos)] == pytest.approx(2.7)
    assert valores[(dos, neg)] == pytest.approx(-2.9)
    assert valores[(uno, pos)] == pytest.approx(1.8)
    assert valores[(uno, neg)] == pytest.approx(-1.9)

    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 15.0, True, 6.0, 10.0, 20.0, {"Chapa": 0.5}
    )
    valores = _componentes_aislada(cpn, "Chapa")
    assert valores[(tres, pos)] == pytest.approx(2.4)
    assert valores[(tres, neg)] == pytest.approx(-4.2)
    assert valores[(dos, pos)] == pytest.approx(1.8)
    assert valores[(dos, neg)] == pytest.approx(-3.2)
    assert valores[(uno, pos)] == pytest.approx(1.2)
    assert valores[(uno, neg)] == pytest.approx(-2.1)


def test_componentes_aislada_figura_5_5_2():
    """Valores de la Figura 5.5-2 a 30°, área en el segundo rango."""
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.DOS_AGUAS, 30.0, False, 8.0, 20.0, 30.0, {"Chapa": 5.0}
    )
    valores = _componentes_aislada(cpn, "Chapa")
    uno, dos, tres = (
        enums.ZonaComponenteCubiertaAislada.UNO,
        enums.ZonaComponenteCubiertaAislada.DOS,
        enums.ZonaComponenteCubiertaAislada.TRES,
    )
    pos = enums.TipoPresionComponentesParedesCubierta.POSITIVA
    neg = enums.TipoPresionComponentesParedesCubierta.NEGATIVA
    assert cpn.referencia == "Figura 5.5-2"
    # a = 2 m, así que 5 m² cae en > a², ≤ 4a².
    assert cpn.distancia_a == pytest.approx(2.0)
    assert valores[(tres, pos)] == pytest.approx(2.0)
    assert valores[(tres, neg)] == pytest.approx(-1.4)
    assert valores[(dos, pos)] == pytest.approx(2.0)
    assert valores[(dos, neg)] == pytest.approx(-1.4)
    assert valores[(uno, pos)] == pytest.approx(1.3)
    assert valores[(uno, neg)] == pytest.approx(-0.9)


def test_componentes_aislada_figura_5_5_3():
    """El diedro negativo usa la Figura 5.5-3 con el módulo del ángulo."""
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.DOS_AGUAS, -15.0, False, 6.0, 20.0, 12.0, {"Chapa": 1.0}
    )
    valores = _componentes_aislada(cpn, "Chapa")
    uno, dos, tres = (
        enums.ZonaComponenteCubiertaAislada.UNO,
        enums.ZonaComponenteCubiertaAislada.DOS,
        enums.ZonaComponenteCubiertaAislada.TRES,
    )
    pos = enums.TipoPresionComponentesParedesCubierta.POSITIVA
    neg = enums.TipoPresionComponentesParedesCubierta.NEGATIVA
    assert cpn.referencia == "Figura 5.5-3"
    # a = 1,2 m, así que 1 m² cae en ≤ a².
    assert cpn.distancia_a == pytest.approx(1.2)
    assert valores[(tres, pos)] == pytest.approx(2.2)
    assert valores[(tres, neg)] == pytest.approx(-2.2)
    assert valores[(dos, pos)] == pytest.approx(1.7)
    assert valores[(dos, neg)] == pytest.approx(-1.7)
    assert valores[(uno, pos)] == pytest.approx(1.1)
    assert valores[(uno, neg)] == pytest.approx(-1.1)


def test_componentes_aislada_interpolacion():
    """Nota 3: interpolación lineal a 10°, un tercio del paso de 7,5° a 15°."""
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 10.0, False, 6.0, 10.0, 20.0, {"Chapa": 0.5}
    )
    valores = _componentes_aislada(cpn, "Chapa")
    tres = enums.ZonaComponenteCubiertaAislada.TRES
    pos = enums.TipoPresionComponentesParedesCubierta.POSITIVA
    neg = enums.TipoPresionComponentesParedesCubierta.NEGATIVA
    # Zona 3 positiva: 3,2 a 7,5° y 3,6 a 15°; 10° está a 1/3 del intervalo.
    assert valores[(tres, pos)] == pytest.approx(3.2 + 0.4 / 3)
    # Zona 3 negativa: -4,2 a 7,5° y -3,8 a 15°.
    assert valores[(tres, neg)] == pytest.approx(-4.2 + 0.4 / 3)


def test_componentes_aislada_rangos_area_efectiva():
    """El rango de área efectiva elige la columna de la tabla."""
    tres = enums.ZonaComponenteCubiertaAislada.TRES
    pos = enums.TipoPresionComponentesParedesCubierta.POSITIVA
    # A 7,5° sin bloqueo la Zona 3 positiva distingue los tres rangos:
    # 3,2 / 2,4 / 1,6 para a = 1 m.
    for area, esperado in ((0.5, 3.2), (2.0, 2.4), (5.0, 1.6)):
        cpn = cp.ComponentesCubiertaAislada(
            enums.TipoCubierta.UN_AGUA, 7.5, False, 6.0, 10.0, 20.0, {"Chapa": area}
        )
        valores = _componentes_aislada(cpn, "Chapa")
        assert valores[(tres, pos)] == pytest.approx(esperado)
    # Los límites de los rangos son inclusivos: a² cierra el primero y 4a² el
    # segundo.
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 7.5, False, 6.0, 10.0, 20.0, {"Chapa": 1.0}
    )
    assert _componentes_aislada(cpn, "Chapa")[(tres, pos)] == pytest.approx(3.2)
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 7.5, False, 6.0, 10.0, 20.0, {"Chapa": 4.0}
    )
    assert _componentes_aislada(cpn, "Chapa")[(tres, pos)] == pytest.approx(2.4)


def test_componentes_aislada_sin_componentes():
    """Sin componentes cargados no hay coeficientes."""
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 15.0, False, 6.0, 10.0, 20.0
    )
    assert cpn.entradas == ()


def test_componentes_aislada_relacion_h_l_fuera_de_lineamientos():
    """Las Figuras 5.5-1 a 5.5-3 exigen 0,25 ≤ h/L ≤ 1,0 con L = ancho."""
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 15.0, False, 2.0, 10.0, 20.0, {"Chapa": 0.5}
    )
    with pytest.raises(ErrorLineamientos, match="h/L"):
        _ = cpn.entradas


def test_componentes_aislada_presiones():
    """La presión de cada fila es q_h · G · C_N, sin presión interna, con el mínimo del Art. 5.2.2 aplicado."""
    cubierta = CubiertaAislada(
        ancho=10,
        longitud=20,
        altura_alero=6,
        altura_cumbrera=7.5,
        bloqueo=0,
        tipo_cubierta=enums.TipoCubierta.UN_AGUA,
        coeficiente_friccion=0.02,
        velocidad=45,
        categoria_exp=enums.CategoriaExposicion.C,
        considerar_topografia=False,
        componentes={"Chapa": 0.5, "Correa": 2.0},
    )
    filas = cubierta.resultados_componentes
    assert len(filas) == 12
    for fila in filas:
        esperado = presion_minima(fila.q.valor * fila.factor_rafaga * fila.cpn)
        assert fila.presion == pytest.approx(esperado)
    # El área elige la columna: Chapa (0,5 m² ≤ a²) y Correa (> a², ≤ 4a²)
    # tienen valores distintos en la misma zona.
    pos = enums.TipoPresionComponentesParedesCubierta.POSITIVA
    chapa = filas.filtrar(
        componente="Chapa",
        zona_componente=enums.ZonaComponenteCubiertaAislada.TRES,
        tipo_presion=pos,
    ).unica()
    correa = filas.filtrar(
        componente="Correa",
        zona_componente=enums.ZonaComponenteCubiertaAislada.TRES,
        tipo_presion=pos,
    ).unica()
    assert chapa.cpn != pytest.approx(correa.cpn)


def test_presion_minima_se_aplica_a_los_componentes_aislada():
    """Art. 5.2.2: ninguna fila de C&R de la aislada baja de ±0,80 kN/m².

    Con una velocidad baja varias filas calculadas quedan por debajo del
    mínimo: el test exige que el recorte ocurra y que el signo sobreviva. El
    SPRFV de la aislada (Figuras 2.4-4 a 2.4-7) no aplica este mínimo.
    """
    cubierta = CubiertaAislada(
        ancho=10,
        longitud=20,
        altura_alero=5,
        altura_cumbrera=6,
        bloqueo=0,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        coeficiente_friccion=0.02,
        velocidad=25,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        componentes={"Chapa": 5.0, "Correa": 10.0},
    )
    filas = cubierta.resultados_componentes
    assert filas
    assert any(
        abs(fila.q.valor * fila.factor_rafaga * fila.cpn) < 800 for fila in filas
    )
    for fila in filas:
        assert abs(fila.presion) >= 800 - 1e-9
        # El recorte conserva el signo del coeficiente.
        assert (fila.presion > 0) == (fila.cpn > 0)

    # El mínimo es de componentes: el SPRFV de la aislada tiene el suyo, y es
    # sólo una nota (Art. 2.1.5, edificios abiertos).
    assert any(abs(fila.presion) < 800 for fila in cubierta.resultados)


def test_componentes_aislada_distancias_zonas_anillos():
    """Vertiente única: anillos concéntricos de ancho a."""
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.UN_AGUA, 15.0, False, 6.0, 10.0, 20.0, {"Chapa": 0.5}
    )
    zonas = cpn.distancias_zonas
    uno, dos, tres = (
        enums.ZonaComponenteCubiertaAislada.UNO,
        enums.ZonaComponenteCubiertaAislada.DOS,
        enums.ZonaComponenteCubiertaAislada.TRES,
    )
    # El anillo perimetral son dos tiras a lo largo del ancho y dos a lo
    # largo de la longitud.
    assert len(zonas[tres]) == 4
    assert len(zonas[dos]) == 4
    assert zonas[uno] == ((2.0, 8.0, -2.0, -18.0),)


def test_componentes_aislada_distancias_zonas_bandas():
    """Dos aguas con ángulo de 10° o más: anillos por faldón.

    La Figura 5.5-1 se aplica a cada faldón: a = 1,2 m (limitado a ancho/8),
    cada faldón mide 10 m de X y 12 m de Z, y las Zonas 3 de ambos faldones
    se tocan en la cumbrera.
    """
    cpn = cp.ComponentesCubiertaAislada(
        enums.TipoCubierta.DOS_AGUAS, 15.0, False, 6.0, 20.0, 12.0, {"Chapa": 0.5}
    )
    zonas = cpn.distancias_zonas
    uno, dos, tres = (
        enums.ZonaComponenteCubiertaAislada.UNO,
        enums.ZonaComponenteCubiertaAislada.DOS,
        enums.ZonaComponenteCubiertaAislada.TRES,
    )
    # Zona 1: el rectángulo interior de cada faldón.
    assert len(zonas[uno]) == 2
    assert zonas[uno][0] == pytest.approx((2.4, 7.6, -2.4, -9.6))
    assert zonas[uno][1] == pytest.approx((12.4, 17.6, -2.4, -9.6))
    # Zona 2: el anillo interior de cada faldón, cuatro rectángulos por
    # faldón.
    assert len(zonas[dos]) == 8
    # Zona 3: el anillo perimetral de cada faldón, cuatro rectángulos por
    # faldón, con la franja junto a la cumbrera incluida.
    assert len(zonas[tres]) == 8
    # Las franjas de Zona 3 junto a la cumbrera: se tocan entre faldones
    # en X = 10.
    assert any(r == pytest.approx((8.8, 10.0, 0.0, -12.0)) for r in zonas[tres])
    assert any(r == pytest.approx((10.0, 11.2, 0.0, -12.0)) for r in zonas[tres])


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
    """Art. 5.2.2: la presión neta de C&R no baja de 0,80 kN/m² en ningún signo."""
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
    """Verifica el factor de reducción Ri y GCpi reducido según Art. 1.11.1.

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
    """Verifica las condiciones de cerramiento según Tabla 1.11-1."""
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


# ---------------------------------------------------------------------------
# Parapetos (Arts. 2.4.5 y 5.6)
# ---------------------------------------------------------------------------


def test_altura_parapeto(edificio_plana_con_parapeto: Edificio):
    """La coronación del parapeto queda en cumbrera + parapeto.

    Con cubierta plana la cumbrera coincide con el alero, así que la
    coronación es alero + parapeto. No es una altura de la estructura: el
    array de alturas termina en la cubierta.
    """
    geometria = edificio_plana_con_parapeto.geometria
    assert geometria.altura_parapeto == pytest.approx(11)
    assert np.asarray(geometria.alturas).max() == pytest.approx(10)
    assert 11 not in np.asarray(geometria.alturas)


def test_topografia_factor_en():
    """El factor topográfico a una altura arbitraria sale de la misma fórmula.

    El parapeto necesita el Kzt de su coronación, que no es una de las alturas
    de la estructura: en las alturas consideradas tiene que coincidir con el
    factor del array y fuera de ellas, con la expresión 1.8-1.
    """
    alturas = np.arange(0.0, 21.0, 1.0)
    topografia = Topografia(
        enums.CategoriaExposicion.C,
        True,
        enums.TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        30,
        100,
        50,
        enums.DireccionTopografia.BARLOVENTO,
        alturas,
    )
    for altura, factor in zip(alturas, topografia.factor, strict=True):
        assert topografia.factor_en(altura) == pytest.approx(factor)
    k3 = np.e ** (-3.0 * 20.5 / 100)
    parametros = topografia.parametros
    assert topografia.factor_en(20.5) == pytest.approx(
        (1 + parametros.k1 * parametros.k2 * k3) ** 2
    )


def test_parapeto_sprfv_valores(edificio_plana_con_parapeto: Edificio):
    """Art. 2.4.5: p = q_p (GC_pn), con GC_pn de +1,5 y -1,0.

    El coeficiente ya incluye el ráfaga (factor 1,0) y no interviene la
    presión interna: ambos signos de la fila coinciden.
    """
    filas = edificio_plana_con_parapeto.resultados_sprfv.filtrar(
        zona=enums.ZonaEdificio.PARAPETO
    )
    assert len(filas) == 2
    por_pared = {fila.pared: fila for fila in filas}
    barlovento = por_pared[enums.ParedEdificioSprfv.BARLOVENTO]
    sotavento = por_pared[enums.ParedEdificioSprfv.SOTAVENTO]
    assert barlovento.referencia == "Art. 2.4.5"
    assert barlovento.cp == pytest.approx(1.5)
    assert sotavento.cp == pytest.approx(-1.0)
    assert barlovento.factor_rafaga == pytest.approx(1.0)
    assert not barlovento.con_presion_interna
    q_p = barlovento.q.valor
    assert barlovento.pos == pytest.approx(1.5 * q_p)
    assert barlovento.neg == pytest.approx(barlovento.pos)
    assert sotavento.pos == pytest.approx(-q_p)
    assert sotavento.neg == pytest.approx(sotavento.pos)


def test_parapeto_presion_dinamica_en_la_coronacion(
    edificio_plana_con_parapeto: Edificio,
):
    """q_p se evalúa en la coronación del parapeto y no en la cubierta.

    Con exposición B (alfa = 7,5), el Kz de 11 m sobre el de 10 m guarda la
    relación (11/10)^(2/7,5), y con Kzt = Ke = 1 la presión de velocidad
    escala igual.
    """
    q_p = (
        edificio_plana_con_parapeto.resultados_sprfv.filtrar(
            zona=enums.ZonaEdificio.PARAPETO
        )
        .filas[0]
        .q
    )
    qz_10 = next(
        fila.q
        for fila in edificio_plana_con_parapeto.resultados_sprfv
        if fila.q.altura == 10
    )
    assert q_p.altura == pytest.approx(11)
    assert q_p.kz == pytest.approx(qz_10.kz * 1.1 ** (2 / 7.5))
    assert q_p.valor == pytest.approx(qz_10.valor * 1.1 ** (2 / 7.5))


def test_parapeto_componentes_valores(edificio_plana_con_parapeto: Edificio):
    """Art. 5.6: cuatro filas, dos casos de carga por dos segmentos.

    El coeficiente combinado es el positivo de pared menos el negativo de la
    zona posterior (la succión suma al empuje). Referencias reglamentarias
    fijas: positivo de pared con el descuento por pendiente baja (0,8522) y
    negativos de la Tabla C 5.3-2 (Zona 2) y de la Tabla C 5.3-1 (Zonas 4 y
    5) interpolados con A = 2 m². La Nota 5 iguala la esquina al borde.
    """
    filas = edificio_plana_con_parapeto.resultados_componentes.filtrar(
        zona=enums.ZonaEdificio.PARAPETO
    )
    assert len(filas) == 4
    referencias = {
        (enums.ParedEdificioSprfv.BARLOVENTO, enums.ZonaParapeto.BORDE): 2.9927,
        (enums.ParedEdificioSprfv.BARLOVENTO, enums.ZonaParapeto.ESQUINA): 2.9927,
        (enums.ParedEdificioSprfv.SOTAVENTO, enums.ZonaParapeto.BORDE): 1.7943,
        (enums.ParedEdificioSprfv.SOTAVENTO, enums.ZonaParapeto.ESQUINA): 2.0165,
    }
    for fila in filas:
        clave = (fila.pared, fila.zona_parapeto)
        assert fila.referencia == "Art. 5.6"
        assert fila.componente == "Parapeto"
        assert fila.q.altura == pytest.approx(11)
        assert fila.cp == pytest.approx(referencias[clave], abs=0.001)
        assert fila.cp == pytest.approx(fila.cp_frontal - fila.cp_posterior)
        assert fila.cp_frontal == pytest.approx(0.8522, abs=0.001)
        # La envolvente no porosa del parapeto: ±0,18 (Tabla 1.11-1).
        assert fila.gcpi == pytest.approx(0.18)
        assert fila.pos == pytest.approx(fila.q.valor * (fila.cp - 0.18))
        assert fila.neg == pytest.approx(fila.q.valor * (fila.cp + 0.18))


def test_parapeto_componentes_nota_iguala_esquina_al_borde():
    """Con parapeto de 1 m o más, la esquina del Caso A usa la Zona 2."""
    parapeto = {
        (entrada.pared, entrada.zona_parapeto): entrada.valor
        for entrada in ParapetoComponentes(30, 40, 10, 1, 2).entradas
    }
    barlovento = enums.ParedEdificioSprfv.BARLOVENTO
    borde, esquina = enums.ZonaParapeto.BORDE, enums.ZonaParapeto.ESQUINA
    assert parapeto[(barlovento, esquina)] == pytest.approx(
        parapeto[(barlovento, borde)]
    )

    # Con menos de 1 m la Nota 5 no aplica: la esquina recupera la Zona 3 de
    # la Tabla C 5.3-2, (-3.2, -1.4) interpolada con A = 2 m².
    sin_nota = {
        (entrada.pared, entrada.zona_parapeto): entrada.valor
        for entrada in ParapetoComponentes(30, 40, 10, 0.5, 2).entradas
    }
    assert sin_nota[(barlovento, esquina)] == pytest.approx(3.7332, abs=0.001)
    assert sin_nota[(barlovento, esquina)] != pytest.approx(
        sin_nota[(barlovento, borde)]
    )


def test_parapeto_componentes_valores_figura_5_4_1():
    """Gran altura (h > 20 m): el positivo y los negativos salen de la Figura 5.4-1.

    El positivo va sin descuento por pendiente baja (0,9); los negativos se
    interpolan con A = 2 m² en el rango de áreas (1, 50) de la Figura para la
    cubierta y en el (2, 50) del positivo de pared para las Zonas 4 y 5. La
    Nota 7 iguala la esquina al borde.
    """
    entradas = {
        (entrada.pared, entrada.zona_parapeto): entrada
        for entrada in ParapetoComponentes(30, 40, 25, 1, 2).entradas
    }
    referencia = {
        (enums.ParedEdificioSprfv.BARLOVENTO, enums.ZonaParapeto.BORDE): 3.076,
        (enums.ParedEdificioSprfv.BARLOVENTO, enums.ZonaParapeto.ESQUINA): 3.076,
        (enums.ParedEdificioSprfv.SOTAVENTO, enums.ZonaParapeto.BORDE): 1.8,
        (enums.ParedEdificioSprfv.SOTAVENTO, enums.ZonaParapeto.ESQUINA): 2.7,
    }
    for clave, entrada in entradas.items():
        assert entrada.valor == pytest.approx(referencia[clave], abs=0.001)
        assert entrada.cp_frontal == pytest.approx(0.9)


def test_parapeto_componentes_sin_area_lanza_error():
    """Sin área efectiva de viento no hay coeficientes del Art. 5.6."""
    with pytest.raises(ErrorLineamientos):
        _ = ParapetoComponentes(30, 40, 10, 1, None).entradas


def test_parapeto_distancias_esquina():
    """El largo del tramo de esquina sale de la figura de cada cara posterior.

    En el Caso A es el brazo de la Zona 3 de la cubierta (0,6 h con la Tabla
    C 5.3-2, la distancia "a" con la Figura 5.4-1) y en el Caso B la
    distancia "a" de las paredes, con la excepción de edificios bajos y
    planos de la Tabla C 5.3-1.
    """
    parapeto = ParapetoComponentes(30, 40, 10, 1, 2)
    assert parapeto.distancias_esquina == pytest.approx(
        (0.6 * 10, distancia_a(30, 40, 10))
    )

    gran_altura = ParapetoComponentes(30, 40, 25, 1, 2)
    assert gran_altura.distancias_esquina == pytest.approx(
        (distancia_a(30, 40, 25), distancia_a(30, 40, 25))
    )

    # Edificio plano de dimensión mínima > 90 m: "a" se limita a 0,8 h.
    excepcion = ParapetoComponentes(95, 120, 4, 1, 2)
    assert excepcion.distancias_esquina[1] == pytest.approx(
        min(distancia_a(95, 120, 4), 0.8 * 4)
    )


def test_parapeto_solo_cubierta_plana(edificio_con_parapeto: Edificio):
    """El cálculo del parapeto es de cubierta plana: a dos aguas quedan las notas.

    El parapeto de 1 m del fixture activa la Nota 5 sobre los coeficientes de
    la cubierta, pero no agrega filas de parapeto a ningún sistema resistente.
    """
    assert not edificio_con_parapeto.resultados_sprfv.filtrar(
        zona=enums.ZonaEdificio.PARAPETO
    )
    assert not edificio_con_parapeto.resultados_componentes.filtrar(
        zona=enums.ZonaEdificio.PARAPETO
    )


def test_parapeto_no_extiende_las_alturas_del_edificio():
    """La coronación no es una altura de la estructura.

    La pared a barlovento y los componentes de pared de gran altura se
    resuelven con qz altura por altura hasta la altura de la cubierta: si la
    coronación entrara al array de alturas aparecerían filas extra a esa
    altura, y las presiones del parapeto son filas propias.
    """
    edificio = Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=25,
        altura_cumbrera=25,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        parapeto=1,
        area_parapeto=2,
        componentes_paredes={"Viga": 10.0},
    )
    assert np.asarray(edificio.geometria.alturas).max() == pytest.approx(25)
    alturas_barlovento = {
        fila.q.altura
        for fila in edificio.resultados_sprfv.filtrar(
            zona=enums.ZonaEdificio.PAREDES,
            pared=enums.ParedEdificioSprfv.BARLOVENTO,
        )
    }
    assert max(alturas_barlovento) == pytest.approx(25)
    alturas_componentes = {
        fila.q.altura
        for fila in edificio.resultados_componentes
        if fila.zona != enums.ZonaEdificio.PARAPETO
    }
    assert max(alturas_componentes) == pytest.approx(25)
    # Las filas del parapeto, en cambio, están en su coronación.
    alturas_parapeto = {
        fila.q.altura
        for fila in edificio.resultados_sprfv.filtrar(zona=enums.ZonaEdificio.PARAPETO)
    }
    assert alturas_parapeto == {26.0}


def test_presion_minima_se_aplica_al_parapeto():
    """El recorte del Art. 5.2.2 también alcanza a las filas del parapeto.

    Con V = 20 m/s el valor neto del Caso A queda por debajo de 0,80 kN/m² en
    ambos signos de presión interna, y sube al mínimo. El SPRFV no lo usa.
    """
    edificio = Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=10,
        altura_cumbrera=10,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=20,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        parapeto=1,
        area_parapeto=2,
    )
    filas = edificio.resultados_componentes.filtrar(zona=enums.ZonaEdificio.PARAPETO)
    assert filas
    for fila in filas:
        assert fila.pos == pytest.approx(800)
        assert fila.neg == pytest.approx(800)

    q_p = (
        edificio.resultados_sprfv.filtrar(zona=enums.ZonaEdificio.PARAPETO)
        .filas[0]
        .q.valor
    )
    assert edificio.resultados_sprfv.filtrar(zona=enums.ZonaEdificio.PARAPETO).filas[
        0
    ].pos == pytest.approx(1.5 * q_p)
