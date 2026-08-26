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

"""Tests de la capa gráfica: mallas, colores, cámara, actores y escenas.

Son smoke tests con algunas verificaciones numéricas donde el valor se puede
calcular a mano (áreas, recortes, direcciones de cámara). No comparan imágenes.
"""

import numpy as np
import pytest

from zonda import enums
from zonda.graficos import camara, mallas
from zonda.graficos.actores import (
    ActorPresion,
    Poligono,
    crear_poligono,
    recortar_poligono,
)
from zonda.graficos.colores import TablaColores
from zonda.graficos.escena import Escena3D

CUADRADO = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))


# --- Mallas ---------------------------------------------------------------


def test_la_normal_sale_del_orden_de_los_puntos():
    """Los directores invierten el orden justamente para dar la vuelta la normal."""
    assert np.allclose(mallas.normal(CUADRADO), (0, 0, 1))
    assert np.allclose(mallas.normal(CUADRADO[::-1]), (0, 0, -1))


def test_el_area_de_un_poligono_conocido():
    assert mallas.area(CUADRADO) == pytest.approx(1.0)
    triangulo = ((0, 0, 0), (4, 0, 0), (0, 3, 0))
    assert mallas.area(triangulo) == pytest.approx(6.0)


def test_el_area_de_la_pared_a_dos_aguas():
    """Rectángulo de 20 x 6 más el triángulo de cumbrera de 2 m de flecha."""
    pared = (
        (0, 0, 0),
        (0, 6, 0),
        (10, 8, 0),
        (20, 6, 0),
        (20, 0, 0),
    )
    assert mallas.area(pared) == pytest.approx(140.0)


def test_el_centro_es_el_promedio_de_los_vertices():
    assert np.allclose(mallas.centro(CUADRADO), (0.5, 0.5, 0))


def test_las_mallas_se_construyen(qapp):
    poligono = mallas.MallaPoligono(CUADRADO)
    # 4 vértices de 6 floats (posición + normal), 2 triángulos de 3 índices.
    assert len(poligono.vertexData()) == 4 * 6 * 4
    assert len(poligono.indexData()) == 2 * 3 * 4

    contorno = mallas.MallaContorno(CUADRADO)
    # 4 aristas, cada una un rectángulo de 4 vértices de 7 floats (posición, el
    # otro extremo y el lado) y 2 triángulos de 3 índices.
    assert len(contorno.vertexData()) == 4 * 4 * 7 * 4
    assert len(contorno.indexData()) == 4 * 2 * 3 * 4

    assert mallas.MallaFlecha().vertexData()
    assert mallas.MallaCilindro(1.0, 4.0, (0.0, 0.0)).vertexData()
    assert mallas.MallaLineas(((0, 0, 0), (0, 5, 0))).vertexData()


def test_el_contorno_le_pasa_al_shader_el_otro_extremo_de_la_arista(qapp):
    """El grosor lo abre contorno.vert, y depende de que el dato llegue bien.

    Los cuatro vértices de una arista nacen pegados sobre sus extremos: dos sobre
    A mirando a B y dos sobre B mirando a A, con el lado invertido en B porque
    allá la perpendicular que saca el shader apunta al revés.
    """
    contorno = mallas.MallaContorno(CUADRADO)
    v = np.frombuffer(contorno.vertexData().data(), dtype="<f4").reshape(-1, 7)

    # Primera arista del cuadrado: de (0, 0, 0) a (1, 0, 0).
    assert np.allclose(v[:4, :3], ((0, 0, 0), (0, 0, 0), (1, 0, 0), (1, 0, 0)))
    assert np.allclose(v[:4, 3:6], ((1, 0, 0), (1, 0, 0), (0, 0, 0), (0, 0, 0)))
    assert np.allclose(v[:4, 6], (1, -1, -1, 1))

    # Un rectángulo por arista, sin área propia: la malla sola no se ve.
    assert len(v) == 4 * 4
    for arista in v.reshape(4, 4, 7):
        assert len(np.unique(arista[:, :3], axis=0)) == 2


def test_la_flecha_lleva_la_normal_suavizada_para_su_borde(qapp):
    """El borde se hincha sobre esta normal, y tiene que ser continua.

    Con la normal de cara —la que ilumina— el casco se abriría en cada arista y
    el borde saldría con muescas, así que cada vértice lleva además el promedio
    de las caras que tocan su posición: dos vértices en el mismo lugar tienen que
    traer la misma.
    """
    v = np.frombuffer(mallas.MallaFlecha().vertexData().data(), dtype="<f4")
    v = v.reshape(-1, 10)

    suavizadas = v[:, 6:9]
    assert np.allclose(np.linalg.norm(suavizadas, axis=1), 1.0, atol=1e-6)

    posiciones = np.round(v[:, :3], 4)
    for posicion in np.unique(posiciones, axis=0):
        juntos = suavizadas[np.all(posiciones == posicion, axis=1)]
        assert np.allclose(juntos, juntos[0], atol=1e-6)

    # La normal de cara, en cambio, no se promedia: la flecha se ve facetada.
    assert len(np.unique(np.round(v[:, 3:6], 4), axis=0)) > 1


def test_el_contorno_queda_sobre_la_cara_sin_desplazarse(qapp):
    """El contorno no se despega en metros: lo acerca el shader a la cámara.

    Desplazarlo sobre la normal lo dejaba atrás de la cara al mirarla del otro
    lado, y las caras se dibujan sin descarte.
    """
    contorno = mallas.MallaContorno(CUADRADO)
    v = np.frombuffer(contorno.vertexData().data(), dtype="<f4").reshape(-1, 7)
    assert np.allclose(v[:, 2], 0.0)


# --- Escala de colores ----------------------------------------------------


def test_los_extremos_de_la_escala(qapp):
    """El mínimo queda azul y el máximo rojo, interpolando el matiz."""
    tabla = TablaColores(-500, 500)
    assert tabla.color(-500).hueF() == pytest.approx(0.66, abs=1e-3)
    assert tabla.color(500).hueF() == pytest.approx(0.0, abs=1e-3)
    assert tabla.color(0).hueF() == pytest.approx(0.33, abs=1e-3)


def test_los_valores_fuera_de_rango_se_pegan_a_los_extremos(qapp):
    tabla = TablaColores(0, 100)
    assert tabla.color(-9999).name() == tabla.color(0).name()
    assert tabla.color(9999).name() == tabla.color(100).name()


def test_la_escala_con_rango_nulo_no_divide_por_cero(qapp):
    tabla = TablaColores(10, 10)
    assert tabla.color(10) is not None


def test_las_etiquetas_de_la_escala_van_de_mayor_a_menor():
    etiquetas = TablaColores(0, 300).etiquetas(4)
    assert etiquetas == [300, 200, 100, 0]


# --- Recorte de polígonos ------------------------------------------------


def test_el_recorte_por_un_plano_deja_la_mitad():
    mitad = recortar_poligono(crear_poligono(CUADRADO), (0.5, 0, 0), (1, 0, 0))
    assert mitad is not None
    assert mitad.area() == pytest.approx(0.5)


def test_el_recorte_que_no_toca_el_poligono_lo_deja_entero():
    entero = recortar_poligono(crear_poligono(CUADRADO), (-1, 0, 0), (1, 0, 0))
    assert entero.area() == pytest.approx(1.0)


def test_el_recorte_que_deja_todo_afuera_devuelve_none():
    assert recortar_poligono(crear_poligono(CUADRADO), (2, 0, 0), (1, 0, 0)) is None


def test_un_poligono_necesita_una_secuencia_de_puntos():
    """El TypeError es parte del contrato de ``aplicar_func_recursivamente``.

    Es lo que le permite distinguir un polígono de una secuencia de polígonos.
    """
    with pytest.raises(TypeError):
        Poligono((0, 5, 0))


# --- Cámara ---------------------------------------------------------------


@pytest.mark.parametrize(
    "ojo, direccion",
    [
        ((5, 0, 0), (0, 0, 1)),
        ((5, 0, -10), (0, 0, -1)),
        ((10, 0, -5), (1, 0, 0)),
        ((0, 0, -5), (-1, 0, 0)),
    ],
)
def test_las_vistas_fijas_apuntan_donde_corresponde(qapp, ojo, direccion):
    from PyQt6.QtGui import QVector3D

    puntos = np.array(((0, 0, 0), (10, 10, -10)), dtype=float)
    vista = camara.calcular_vista(
        puntos,
        np.array((5.0, 0.0, -5.0)),
        np.array(ojo, dtype=float),
        camara.ARRIBA_POR_DEFECTO,
        1000,
        700,
    )
    obtenida = vista.rotacion.rotatedVector(QVector3D(0, 0, 1))
    assert np.allclose((obtenida.x(), obtenida.y(), obtenida.z()), direccion, atol=1e-6)


def test_la_vista_superior_usa_el_eje_x_como_vertical(qapp):
    """Mirando hacia abajo, el (0, 1, 0) se degenera."""
    from PyQt6.QtGui import QVector3D

    puntos = np.array(((0, 0, 0), (10, 10, -10)), dtype=float)
    vista = camara.calcular_vista(
        puntos,
        np.array((5.0, 0.0, -5.0)),
        np.array((5.0, 10.0, -5.0)),
        camara.ARRIBA_SUPERIOR,
        1000,
        700,
    )
    arriba = vista.rotacion.rotatedVector(QVector3D(0, 1, 0))
    assert np.allclose((arriba.x(), arriba.y(), arriba.z()), (1, 0, 0), atol=1e-6)


def test_el_encuadre_deja_la_escena_adentro(qapp):
    """La distancia tiene que alcanzar para que el punto más alejado entre."""
    puntos = np.array(((0, 0, 0), (20, 10, -30)), dtype=float)
    vista = camara.calcular_vista(
        puntos,
        np.array((10.0, 0.0, -15.0)),
        np.array((10.0, 0.0, 0.0)),
        camara.ARRIBA_POR_DEFECTO,
        1000,
        700,
    )
    assert vista.distancia > 0
    assert vista.magnificacion > 0


# --- Actores y escena ----------------------------------------------------


def test_los_actores_se_registran_en_la_escena(qapp):
    escena = Escena3D()
    tabla = TablaColores(-500, 500)
    sin_presion = ActorPresion(escena, CUADRADO, color_cara="Red")
    con_presion = ActorPresion(
        escena, CUADRADO, tabla_colores=tabla, presion=True, mostrar=False
    )

    assert sin_presion in escena.caras
    assert con_presion in escena.caras
    assert escena.actores_presion == (con_presion,)
    assert len(escena.presiones) == 1


def test_asignar_presion_cambia_color_flecha_y_etiqueta(qapp):
    escena = Escena3D()
    tabla = TablaColores(-500, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)

    actor.asignar_presion(500, enums.Unidad.N)
    assert actor.color.hueF() == pytest.approx(0.0, abs=1e-3)
    assert actor.flecha.largo == pytest.approx(7.0)
    assert "500.00 N/m²" in actor.flecha.texto

    largo_maximo = actor.flecha.largo
    actor.asignar_presion(250, enums.Unidad.N)
    assert actor.flecha.largo == pytest.approx(largo_maximo / 2)


def test_el_sentido_de_la_flecha_sigue_el_signo(qapp):
    escena = Escena3D()
    tabla = TablaColores(-500, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)

    actor.asignar_presion(500, enums.Unidad.N)
    empuje = actor.flecha.posicion
    actor.asignar_presion(-500, enums.Unidad.N)
    succion = actor.flecha.posicion

    # Con empuje la flecha arranca afuera y termina en la cara; con succión
    # arranca en la cara.
    assert empuje.z() > succion.z()
    assert np.allclose((succion.x(), succion.y(), succion.z()), actor.centro)


def test_ocultar_un_actor_oculta_su_flecha(qapp):
    escena = Escena3D()
    tabla = TablaColores(-500, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    actor.asignar_presion(100, enums.Unidad.N)
    assert actor.flecha.visible

    actor.ocultar()
    assert not actor.flecha.visible


def test_limpiar_la_escena_saca_todos_los_actores(qapp):
    escena = Escena3D()
    ActorPresion(escena, CUADRADO, color_cara="Red")
    assert escena.actores
    escena.limpiar()
    assert not escena.actores


def test_el_rayo_pega_en_el_medio_del_cuadrado():
    golpe = mallas.interseccion_rayo((0.5, 0.5, 3), (0, 0, -1), CUADRADO)
    assert golpe is not None
    t, punto = golpe
    assert t == pytest.approx(3.0)
    assert np.allclose(punto, (0.5, 0.5, 0))


def test_el_rayo_no_pega_afuera_del_cuadrado():
    assert mallas.interseccion_rayo((1.5, 0.5, 3), (0, 0, -1), CUADRADO) is None


def test_el_rayo_no_pega_para_atras():
    """El plano quedó detrás del origen: el cursor no puede engancharlo."""
    assert mallas.interseccion_rayo((0.5, 0.5, 3), (0, 0, 1), CUADRADO) is None


def test_el_rayo_pega_una_cara_vista_de_dorso():
    """Es lo que View3D.pick() no hace, y por eso la medición no lo usa."""
    invertido = CUADRADO[::-1]
    assert mallas.interseccion_rayo((0.5, 0.5, 3), (0, 0, -1), invertido) is not None


def test_el_rayo_pega_un_poligono_concavo():
    """La regla par-impar tiene que dejar afuera la muesca de la L."""
    ele = (
        (0, 0, 0),
        (3, 0, 0),
        (3, 1, 0),
        (1, 1, 0),
        (1, 3, 0),
        (0, 3, 0),
    )
    assert mallas.interseccion_rayo((0.5, 0.5, 3), (0, 0, -1), ele) is not None
    assert mallas.interseccion_rayo((2, 2, 3), (0, 0, -1), ele) is None


def test_la_cara_bajo_el_rayo_es_la_mas_cercana(qapp):
    from PyQt6.QtGui import QVector3D

    escena = Escena3D()
    ActorPresion(escena, CUADRADO, color_cara="Red")
    lejos = tuple((x, y, z - 5) for x, y, z in CUADRADO)
    ActorPresion(escena, lejos, color_cara="Blue")

    golpe = escena.caraBajoRayo(QVector3D(0.9, 0.95, 3), QVector3D(0, 0, -1))
    assert golpe is not None
    assert golpe["punto"].z() == pytest.approx(0.0)
    # El vértice más cercano al impacto, que es lo que engancha la medición.
    assert (golpe["vertice"].x(), golpe["vertice"].y()) == (1.0, 1.0)


def test_la_cara_bajo_el_rayo_ignora_las_ocultas(qapp):
    from PyQt6.QtGui import QVector3D

    escena = Escena3D()
    actor = ActorPresion(escena, CUADRADO, color_cara="Red")
    actor.ocultar()
    assert escena.caraBajoRayo(QVector3D(0.5, 0.5, 3), QVector3D(0, 0, -1)) is None


def test_el_punto_mas_cercano_engancha_un_vertice(qapp):
    from PyQt6.QtGui import QVector3D

    escena = Escena3D()
    ActorPresion(escena, CUADRADO, color_cara="Red")
    enganchado = escena.puntoMasCercano(QVector3D(0.9, 0.95, 0.0))
    assert (enganchado.x(), enganchado.y(), enganchado.z()) == (1.0, 1.0, 0.0)


def test_el_punto_mas_cercano_ignora_los_solidos(qapp):
    """Los puntos de un sólido son su caja envolvente, no están sobre el cuerpo."""
    from PyQt6.QtGui import QVector3D

    from zonda.graficos.actores import cilindro

    escena = Escena3D()
    ActorPresion(escena, CUADRADO, color_cara="Red")
    # La esquina de la caja del cilindro cae en (1.1, 0.9, 1.1), más cerca del
    # objetivo que cualquier vértice del cuadrado.
    cilindro(escena, radio=0.1, altura=0.9, centro_xz=(1.0, 1.0))
    enganchado = escena.puntoMasCercano(QVector3D(0.92, 0.92, 0.92))
    assert (enganchado.x(), enganchado.y(), enganchado.z()) == (1.0, 1.0, 0.0)


# --- Las escenas de cada estructura --------------------------------------


def test_escena_del_cartel(qapp, cartel):
    from zonda.graficos.escenas import cartel as escena_cartel

    escena = Escena3D()
    presiones = escena_cartel.Presiones(escena, cartel, enums.Unidad.N, enums.Unidad.N)
    presiones.actualizar_altura(10)

    assert len(escena.caras) == 6
    assert len(escena.solidos) == 1  # el soporte
    assert len(escena.presiones) == 1
    assert "Fuerza Total" in escena.titulo
    assert escena.etiquetasEscala


def test_escena_de_la_cubierta_aislada(qapp, cubierta_aislada):
    from zonda.graficos.escenas import aisladas as escena_aisladas

    escena = Escena3D()
    presiones = escena_aisladas.Presiones(escena, cubierta_aislada, enums.Unidad.N)
    presiones.actualizar_tipo_presion(enums.TipoPresionCubiertaAislada.LOCAL)
    presiones.actualizar_extremo_presion(enums.ExtremoPresion.MIN)

    assert escena.caras
    assert escena.lineas  # los soportes
    assert escena.presiones
    assert escena.titulo == "Presión Local Min"


def test_escena_del_edificio_sprfv(qapp, edificio):
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesSprfvMetodoDireccional(
        escena, edificio, enums.Unidad.N
    )
    for direccion in enums.DireccionVientoMetodoDireccionalSprfv:
        presiones.actualizar_direccion_viento(direccion)
    presiones.actualizar_gcpi(1)
    presiones.actualizar_altura_pared_barlovento(6.0)

    assert escena.caras
    assert escena.presiones
    assert "GCpi" in escena.titulo


def test_escena_del_edificio_componentes(qapp, edificio):
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(escena, edificio, enums.Unidad.N)
    presiones.actualizar_componente_pared("Viga")
    presiones.actualizar_componente_cubierta("Correa")
    presiones.actualizar_tipo_presion(
        enums.TipoPresionComponentesParedesCubierta.POSITIVA
    )

    assert escena.caras
    assert escena.presiones
    assert "Viga" in escena.titulo


def test_el_volumen_del_edificio_sale_del_area_de_la_pared(qapp):
    """20 x 30 con alero a 6 m y cumbrera a 8 m: (20*6 + 20*2/2) * 30."""
    from zonda.graficos.escenas import geometrias

    escena = Escena3D()
    geometria = geometrias.Geometria(escena, enums.Estructura.EDIFICIO)
    geometria.generar(20, 30, 6, 8, enums.TipoCubierta.DOS_AGUAS)
    assert geometria.director.volumen() == pytest.approx(4200.0)


def test_regenerar_la_geometria_no_acumula_actores(qapp):
    from zonda.graficos.escenas import geometrias

    escena = Escena3D()
    geometria = geometrias.Geometria(escena, enums.Estructura.CARTEL)
    geometria.generar(10, 1, 5, 10)
    primera = len(escena.caras)
    geometria.generar(12, 1, 5, 10)
    assert len(escena.caras) == primera
