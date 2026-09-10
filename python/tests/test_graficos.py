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
    ESCALA_BASE_FLECHA,
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

    vastago = mallas.MallaVastagoFlecha()
    # 12 triángulos sueltos (8 laterales + 4 del pie), sin índice.
    assert len(vastago.vertexData()) == 12 * 3 * 6 * 4

    punta = mallas.MallaPuntaFlecha()
    # 12 triángulos sueltos (8 del marco + 4 laterales), sin índice.
    assert len(punta.vertexData()) == 12 * 3 * 6 * 4

    assert mallas.MallaAristasVastagoFlecha().vertexData()
    assert mallas.MallaAristasPuntaFlecha().vertexData()
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


def test_el_trazo_cerrado_aporta_dos_vertices_por_esquina(qapp):
    """El glow usa el trazo a inglete: cada esquina abre para los dos lados.

    Cada vértice lleva la esquina previa (COLOR) y la siguiente (NORMAL), que
    es lo que el shader necesita para calcular el inglete en pantalla.
    """
    trazo = mallas.MallaTrazo([(CUADRADO, True)])
    v = np.frombuffer(trazo.vertexData().data(), dtype="<f4").reshape(-1, 10)

    # Dos vértices (lado +1 y -1) por cada una de las 4 esquinas.
    assert len(v) == 8
    # El quad que une cada par de esquinas contiguas, incluida la vuelta de
    # la última contra la primera: 6 índices por tramo.
    assert len(trazo.indexData()) == 4 * 6 * 4

    # La esquina (1, 0, 0): su tramo previo llega desde (0, 0, 0) y el
    # siguiente sale hacia (1, 1, 0).
    en_esquina = v[np.all(np.isclose(v[:, :3], (1, 0, 0)), axis=1)]
    assert len(en_esquina) == 2
    assert np.allclose(en_esquina[:, 3:6], (0, 0, 0))
    assert np.allclose(en_esquina[:, 7:10], (1, 1, 0))
    assert sorted(en_esquina[:, 6]) == [-1.0, 1.0]


def test_el_trazo_abierto_deja_topes_rectos(qapp):
    """En los extremos de un trazo abierto no hay tramo del otro lado: la
    esquina que falta repite al propio vértice y el shader cae en la
    perpendicular pura del tramo que sí hay."""
    linea = ((0, 0, 0), (1, 0, 0), (2, 0, 0))
    trazo = mallas.MallaTrazo([(linea, False)])
    v = np.frombuffer(trazo.vertexData().data(), dtype="<f4").reshape(-1, 10)

    assert len(v) == 6  # 3 esquinas x 2 lados

    puntas = v[np.all(np.isclose(v[:, :3], (0, 0, 0)), axis=1)]
    assert np.allclose(puntas[:, 3:6], (0, 0, 0))  # previa == posición
    assert np.allclose(puntas[:, 7:10], (1, 0, 0))


def test_la_punta_de_la_flecha_es_una_piramide(qapp):
    """La punta es una pirámide de base cuadrada sobre un marco.

    En el ápice confluyen las 4 caras laterales —el cono viejo juntaba ahí los
    30 triángulos de su anillo— y la base queda en el origen, en el plano donde
    empalma con el vastago, con el ápice a LARGO_PUNTA_FLECHA.
    """
    v = np.frombuffer(mallas.MallaPuntaFlecha().vertexData().data(), dtype="<f4")
    v = v.reshape(-1, 6)

    apice = v[np.all(np.isclose(v[:, :3], (0, mallas.LARGO_PUNTA_FLECHA, 0)), axis=1)]
    # Una entrada por cara lateral: las 4 de la pirámide.
    assert len(apice) == 4

    # Sobre el plano de la base, las esquinas exteriores quedan a radio_punta
    # y las del vastago —el agujero del marco— a radio_vastago.
    sobre_base = v[np.isclose(v[:, 1], 0)]
    radios = np.linalg.norm(sobre_base[:, [0, 2]], axis=1)
    exteriores = sobre_base[np.isclose(radios, mallas.RADIO_PUNTA_FLECHA)][:, :3]
    assert len(np.unique(np.round(exteriores, 4), axis=0)) == 4
    for esquina in exteriores:
        # Dos caras laterales y tres triángulos del marco: los dos de su
        # trapecio y uno del contiguo.
        assert np.count_nonzero(np.all(np.isclose(v[:, :3], esquina), axis=1)) == 5
    interiores = sobre_base[np.isclose(radios, mallas.RADIO_VASTAGO_FLECHA)][:, :3]
    assert len(np.unique(np.round(interiores, 4), axis=0)) == 4
    for esquina in interiores:
        # Los dos triángulos de su trapecio y uno del contiguo.
        assert np.count_nonzero(np.all(np.isclose(v[:, :3], esquina), axis=1)) == 3


def test_las_aristas_de_la_flecha(qapp):
    """Con todas las caras planas van todas las aristas, por cuerpo.

    El vastago aporta sus cuatro cantos verticales y los cuadrados del pie y
    del tope —12 segmentos sobre un prisma de largo 1— y la punta sus cuatro
    cantos y el perímetro de su base —8 segmentos de tamaño fijo—. El borde
    interior del marco lo dibuja el cuadrado del tope del vastago.
    """
    vastago = mallas.MallaAristasVastagoFlecha()
    # 12 aristas; cada una son 4 vértices de 7 floats y 2 triángulos de 3 índices.
    assert len(vastago.vertexData()) == 12 * 4 * 7 * 4
    assert len(vastago.indexData()) == 12 * 2 * 3 * 4
    v = np.frombuffer(vastago.vertexData().data(), dtype="<f4").reshape(-1, 7)
    extremos = np.unique(np.round(v[:, :3], 4), axis=0)
    alturas = extremos[:, 1]
    # Dos cuadrados de 4 esquinas: el pie en y=0 y el tope en y=1.
    assert len(extremos) == 8
    for altura, cantidad in ((0, 4), (1, 4)):
        assert np.count_nonzero(np.isclose(alturas, altura)) == cantidad
    # Todas las esquinas del vastago quedan a radio_vastago del eje.
    radios = np.linalg.norm(v[:, [0, 2]], axis=1)
    assert np.allclose(radios, mallas.RADIO_VASTAGO_FLECHA)

    punta = mallas.MallaAristasPuntaFlecha()
    assert len(punta.vertexData()) == 8 * 4 * 7 * 4
    assert len(punta.indexData()) == 8 * 2 * 3 * 4
    v = np.frombuffer(punta.vertexData().data(), dtype="<f4").reshape(-1, 7)
    extremos = np.unique(np.round(v[:, :3], 4), axis=0)
    alturas = extremos[:, 1]
    # Las 4 esquinas de la base y el ápice.
    assert len(extremos) == 5
    for altura, cantidad in ((0, 4), (mallas.LARGO_PUNTA_FLECHA, 1)):
        assert np.count_nonzero(np.isclose(alturas, altura)) == cantidad
    radios = np.linalg.norm(v[:, [0, 2]], axis=1)
    assert np.allclose(radios[radios > 0.1], mallas.RADIO_PUNTA_FLECHA)
    assert np.allclose(radios[radios <= 0.1], 0.0)


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
    assert actor.flecha.largo == pytest.approx(ESCALA_BASE_FLECHA)
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
    # arranca en la cara. La punta, de tamaño fijo, le suma su largo a la base.
    assert empuje.z() > succion.z()
    assert np.allclose((succion.x(), succion.y(), succion.z()), actor.centro)
    distancia = empuje.z() - actor.centro[2]
    assert distancia == pytest.approx(actor.flecha.largo + mallas.LARGO_PUNTA_FLECHA)


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


def test_los_soportes_del_cartel(qapp):
    """El cartel apoya en una pata central, o en dos si el ancho pasa el límite."""
    from zonda.graficos.directores import cartel as director_cartel

    escena = Escena3D()
    director = director_cartel.Geometria(
        escena, ancho=6, profundidad=1, altura_inferior=5, altura_superior=10
    )
    director.inicializar_actores()
    assert len(escena.solidos) == 1

    director.ancho = director_cartel.ANCHO_DOS_SOPORTES + 1
    director.inicializar_actores()
    assert len(escena.solidos) == 2


def test_escena_del_cartel(qapp, cartel):
    from zonda.graficos.escenas import cartel as escena_cartel

    escena = Escena3D()
    presiones = escena_cartel.Presiones(escena, cartel, enums.Unidad.N, enums.Unidad.N)

    # Arranca en el Caso A: un actor de presión en la cara a barlovento.
    # Las caras son las 5 sin presión, la cara a barlovento y las 2 regiones
    # del Caso C (creadas ocultas: la fixture tiene B/s = 2).
    assert len(escena.caras) == 8
    assert len(escena.solidos) == 2  # los soportes: el fixture es ancho
    assert "Caso A" in escena.titulo
    assert escena.etiquetasEscala

    presiones.actualizar_caso(enums.CasoCartel.CASO_B)
    assert "Caso B" in escena.titulo
    # La excentricidad del Caso B va en la etiqueta de la flecha.
    etiqueta = next(flecha.texto for flecha in escena.presiones if flecha.visible)
    assert "e = 2.00 m" in etiqueta

    # El Caso C reparte la presión entre las regiones: la fixture tiene
    # B/s = 2, así que son dos.
    presiones.actualizar_caso(enums.CasoCartel.CASO_C)
    assert "Caso C" in escena.titulo
    assert len(escena.presiones) == 3  # la cara a barlovento oculta + 2 regiones
    visibles = [flecha for flecha in escena.presiones if flecha.visible]
    assert len(visibles) == 2
    assert "región" in visibles[0].texto


def test_escena_de_la_cubierta_aislada(qapp, cubierta_aislada):
    from zonda.graficos.escenas import aisladas as escena_aisladas

    escena = Escena3D()
    presiones = escena_aisladas.Presiones(escena, cubierta_aislada, enums.Unidad.N)
    for direccion in enums.DireccionVientoCubiertaAislada:
        presiones.actualizar_direccion(direccion)
    presiones.actualizar_caso(enums.CasoCargaCubiertaAislada.CASO_B)

    assert escena.caras
    assert escena.lineas  # los soportes
    assert escena.presiones
    assert escena.titulo == "Presión γ = 270º Caso B"


def test_escena_cubierta_aislada_zonas_cubren_la_superficie(qapp, cubierta_aislada):
    """Las zonas de cada dirección cubren la cubierta sin huecos ni solapes."""
    from zonda.graficos.escenas import aisladas as escena_aisladas

    def area(actores):
        """El área total de una zona, con actores sueltos o en tuplas."""
        try:
            return sum(area(a) for a in actores)
        except TypeError:
            return actores.poligono.area()

    escena = Escena3D()
    presiones = escena_aisladas.Presiones(escena, cubierta_aislada, enums.Unidad.N)
    for direccion in enums.DireccionVientoCubiertaAislada:
        presiones.actualizar_direccion(direccion)
        actores = presiones._actores_actuales
        for zona in actores:
            fila = presiones._filas[
                (direccion, zona, enums.CasoCargaCubiertaAislada.CASO_A)
            ]
            assert fila, f"la zona {zona} quedó sin presión"
        assert sum(area(actores[zona]) for zona in actores) == pytest.approx(
            cubierta_aislada.geometria.area, rel=0.01
        )


def test_escena_cubierta_aislada_normales_hacia_arriba(qapp, cubierta_aislada):
    """Las normales de todos los actores apuntan hacia arriba.

    El sentido de la flecha de presión se apoya en la normal del polígono: si
    alguna queda invertida (por ejemplo al medir las bandas del viento desde
    el contrafrente), la flecha atraviesa la cubierta en lugar de salir de
    ella.
    """
    from zonda.graficos.escenas import aisladas as escena_aisladas

    escena = Escena3D()
    presiones = escena_aisladas.Presiones(escena, cubierta_aislada, enums.Unidad.N)

    for direccion in enums.DireccionVientoCubiertaAislada:
        presiones.actualizar_direccion(direccion)
        for actores in presiones._actores_actuales.values():
            try:
                for actor in actores:
                    assert actor.normal[1] > 0, (
                        "la normal de un polígono apunta hacia abajo"
                    )
            except TypeError:
                assert actores.normal[1] > 0


def _area_de_actores(actores) -> float:
    """El área total de un grupo de actores, sueltos o en tuplas."""
    try:
        return sum(_area_de_actores(a) for a in actores)
    except TypeError:
        return actores.poligono.area()


def _contar_actores(actores) -> int:
    """La cantidad de actores de un grupo, sueltos o en tuplas."""
    try:
        return sum(_contar_actores(a) for a in actores)
    except TypeError:
        return 1


def test_escena_cubierta_aislada_componentes(qapp, cubierta_aislada_con_componentes):
    from zonda.graficos.escenas import aisladas as escena_aisladas

    escena = Escena3D()
    componentes = escena_aisladas.Componentes(
        escena, cubierta_aislada_con_componentes, enums.Unidad.N
    )
    componentes.actualizar_componente("Chapa")
    componentes.actualizar_tipo_presion(
        enums.TipoPresionComponentesParedesCubierta.POSITIVA
    )
    assert escena.caras
    assert escena.lineas  # los soportes
    assert escena.presiones
    assert "Chapa" in escena.titulo
    assert "positiva" in escena.titulo

    componentes.actualizar_componente("Correa")
    componentes.actualizar_tipo_presion(
        enums.TipoPresionComponentesParedesCubierta.NEGATIVA
    )
    assert "Correa" in escena.titulo
    assert "negativa" in escena.titulo

    # Cada zona muestra la presión de su fila para el componente y el signo
    # vigentes: ninguna flecha queda sin valor ni con el de otra zona.
    from zonda.unidades import convertir_unidad

    textos = [flecha.texto for flecha in escena.presiones if flecha.visible]
    assert len(textos) == sum(
        _contar_actores(actores) for actores in componentes._actores_cubierta.values()
    )
    for zona in enums.ZonaComponenteCubiertaAislada:
        fila = componentes._filas[
            ("Correa", zona, enums.TipoPresionComponentesParedesCubierta.NEGATIVA)
        ].unica()
        valor = f"{convertir_unidad(fila.presion, enums.Unidad.N):.2f}"
        assert any(valor in texto for texto in textos), (
            f"la zona {zona.value} no muestra su presión"
        )


def test_escena_componentes_zonas_cubren_la_superficie(
    qapp, cubierta_aislada_con_componentes
):
    """Las zonas de componentes cubren la cubierta sin huecos ni solapes."""
    from zonda.graficos.escenas import aisladas as escena_aisladas

    escena = Escena3D()
    componentes = escena_aisladas.Componentes(
        escena, cubierta_aislada_con_componentes, enums.Unidad.N
    )
    actores = componentes._actores_cubierta
    assert set(actores) == set(enums.ZonaComponenteCubiertaAislada)
    for tipo in enums.TipoPresionComponentesParedesCubierta:
        for zona in actores:
            fila = componentes._filas[("Chapa", zona, tipo)]
            assert fila, f"la zona {zona} quedó sin presión para {tipo.value}"
    assert sum(_area_de_actores(actores[zona]) for zona in actores) == pytest.approx(
        cubierta_aislada_con_componentes.geometria.area, rel=0.01
    )


def test_escena_componentes_normales_hacia_arriba(
    qapp, cubierta_aislada_con_componentes
):
    """Las normales de todos los actores de zonas apuntan hacia arriba."""
    from zonda.graficos.escenas import aisladas as escena_aisladas

    escena = Escena3D()
    componentes = escena_aisladas.Componentes(
        escena, cubierta_aislada_con_componentes, enums.Unidad.N
    )
    for actores in componentes._actores_cubierta.values():
        try:
            for actor in actores:
                assert actor.normal[1] > 0, (
                    "la normal de un polígono apunta hacia abajo"
                )
        except TypeError:
            assert actores.normal[1] > 0


def test_escena_componentes_anillos_cubren_la_superficie(qapp):
    """Vertiente única: los anillos también cubren la cubierta entera."""
    from zonda.cirsoc import CubiertaAislada
    from zonda.graficos.escenas import aisladas as escena_aisladas

    cubierta = CubiertaAislada(
        ancho=10,
        longitud=20,
        altura_alero=5,
        altura_cumbrera=6.325,
        bloqueo=0,
        tipo_cubierta=enums.TipoCubierta.UN_AGUA,
        coeficiente_friccion=0.02,
        velocidad=45,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        componentes={"Chapa": 0.5},
    )
    escena = Escena3D()
    componentes = escena_aisladas.Componentes(escena, cubierta, enums.Unidad.N)
    actores = componentes._actores_cubierta
    assert set(actores) == set(enums.ZonaComponenteCubiertaAislada)
    assert sum(_area_de_actores(actores[zona]) for zona in actores) == pytest.approx(
        cubierta.geometria.area, rel=0.01
    )


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


def test_escena_del_edificio_sprfv_angulo_menor_diez(qapp, edificio_angulo_pequeno):
    """La escena recorre los dos casos de cubierta barlovento con ángulo < 10°."""
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesSprfvMetodoDireccional(
        escena, edificio_angulo_pequeno, enums.Unidad.N
    )
    presiones.actualizar_direccion_viento(
        enums.DireccionVientoMetodoDireccionalSprfv.NORMAL
    )
    for tipo in enums.TipoPresionCubiertaBarloventoSprfv:
        presiones.actualizar_presion_cubierta_inclinada(tipo)

    assert escena.caras
    assert escena.presiones
    assert "GCpi" in escena.titulo


def test_titulo_un_agua_angulo_menor_diez_sotavento_muestra_el_caso(qapp):
    """Con ángulo < 10° el caso aplica a toda la cubierta y va en el título.

    Aunque la cubierta a un agua esté en posición sotavento, el caso de
    presión de la cubierta sigue siendo visible en la escena (el combobox del
    widget queda habilitado), así que el título lo muestra.
    """
    from zonda.cirsoc import Edificio
    from zonda.graficos.escenas import edificio as escena_edificio

    edificio = Edificio(
        ancho=20,
        longitud=30,
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
    escena = Escena3D()
    presiones = escena_edificio.PresionesSprfvMetodoDireccional(
        escena, edificio, enums.Unidad.N
    )
    presiones.actualizar_direccion_viento(
        enums.DireccionVientoMetodoDireccionalSprfv.NORMAL
    )
    presiones.actualizar_posicion_cubierta_un_agua(
        enums.PosicionCubiertaAleroSprfv.SOTAVENTO
    )

    assert "Caso" in escena.titulo


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


def _edificio_dos_aguas_angulo_bajo(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a dos aguas de θ ≈ 3.8°.

    Con altura de alero 8 m -que para θ ≤ 10° es la altura media- las zonas de
    la Figura 5.3-2A quedan en 1.6 m (Zona 3), 4.8 m (Zona 2) y 9.6 m (Zona 1).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con un componente de cubierta cargado.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=8,
        altura_cumbrera=9,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_cubierta={"Correa": 5.0},
    )


def _areas_por_zona(actores):
    """El área total de los polígonos de cada zona.

    Args:
        actores: Los actores agrupados por zona.

    Returns:
        El área de cada zona.
    """
    return {
        zona: sum(actor._poligono.area() for actor in actores_zona)
        for zona, actores_zona in actores.items()
    }


def test_zonas_de_componentes_de_la_tabla_c_5_3_2(qapp):
    """Las zonas de la Figura 5.3-2A cubren la cubierta sin huecos ni solapes.

    La Zona 3 son cuatro cuadrados de 0.2h de lado medidos en planta, así que
    sobre el faldón su área crece con la inclinación.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_angulo_bajo()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {zonas.UNO_PRIMA, zonas.UNO, zonas.DOS, zonas.TRES}

    # Las áreas se calculan en planta y se llevan al plano del faldón, cuya
    # inclinación es la flecha de 1 m sobre la semiluz de 15 m.
    inclinacion = np.hypot(1, 15) / 15
    # Una "L" por esquina: dos brazos de 1.6 m de espesor y 4.8 m de largo,
    # descontando el cuadrado de 1.6 m donde se cruzan.
    zona_3 = 4 * (2 * 1.6 * 4.8 - 1.6**2)
    esperadas = {
        zonas.TRES: zona_3,
        # Franja perimetral de 4.8 m, sin las "L" de las esquinas.
        zonas.DOS: 30 * 40 - 20.4 * 30.4 - zona_3,
        # Franja que va de 4.8 m a 9.6 m del borde.
        zonas.UNO: 20.4 * 30.4 - 10.8 * 20.8,
        # El interior, más allá de 9.6 m del borde.
        zonas.UNO_PRIMA: 10.8 * 20.8,
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(30 * 40 * inclinacion)


def test_zonas_de_componentes_de_la_tabla_c_5_3_2_con_alero(qapp):
    """Con voladizo las distancias se miden desde su borde exterior (Nota 7).

    La cubierta sigue cubierta por completo y los actores del alero suman el
    área del voladizo, que es de 1 m sobre el plano de cada faldón.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_angulo_bajo(alero=1)
    )
    areas_cubierta = _areas_por_zona(director.actores_cubierta)
    areas_alero = _areas_por_zona(director.actores_alero)

    faldon = np.hypot(1, 15)
    assert sum(areas_cubierta.values()) == pytest.approx(2 * faldon * 40)
    assert sum(areas_alero.values()) == pytest.approx(2 * 1 * 40)


def _edificio_dos_aguas_gran_altura(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a dos aguas de h > 20 m (Fig. 5.4-1).

    Con altura de alero 22 m y cumbrera a 23 m la semiluz de 15 m da un ángulo
    de unos 3.8° y una altura media de 22.5 m: aplica la Figura 5.4-1 con la
    distancia "a" en 3 m (0,1 de la menor dimensión horizontal contra 0,4h).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con componentes de paredes y cubierta cargados.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=22,
        altura_cumbrera=23,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_paredes={"Viga": 10.0},
        componentes_cubierta={"Correa": 5.0},
    )


def _edificio_dos_aguas_angulo_medio(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a dos aguas de θ ≈ 7.6°.

    Con altura de alero 8 m y cumbrera a 10 m la semiluz de 15 m da un ángulo
    en el rango de la Tabla C 5.3-3 (7° < θ ≤ 20°), y la distancia "a" queda
    en 3 m (0,1 de la menor dimensión horizontal contra 0,4h).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con un componente de cubierta cargado.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=8,
        altura_cumbrera=10,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_cubierta={"Correa": 5.0},
    )


def _edificio_dos_aguas_angulo_empinado(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a dos aguas de θ ≈ 25°.

    Con altura de alero 6 m y cumbrera a 13 m la semiluz de 15 m da un ángulo
    en el rango de la Tabla C 5.3-4 (20° < θ ≤ 27°), y la distancia "a" queda
    en 3 m (0,1 de la menor dimensión horizontal contra 0,4h).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con un componente de cubierta cargado.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=6,
        altura_cumbrera=13,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_cubierta={"Correa": 5.0},
    )


def _edificio_dos_aguas_angulo_muy_empinado(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a dos aguas de θ ≈ 36°.

    Con altura de alero 5 m y cumbrera a 16 m la semiluz de 15 m da un ángulo
    en el rango de la Tabla C 5.3-5 (27° < θ ≤ 45°), y la distancia "a" queda
    en 3 m (0,1 de la menor dimensión horizontal contra 0,4h).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con un componente de cubierta cargado.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=5,
        altura_cumbrera=16,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_cubierta={"Correa": 5.0},
    )


def _edificio_un_agua_angulo_bajo(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a un agua de θ ≈ 5.7°.

    Con altura de alero 8 m y cumbrera a 11 m la luz de 30 m da un ángulo en
    el rango de la Figura 5.3-5A (3° < θ ≤ 10°), y la distancia "a" queda en
    3 m (0,1 de la menor dimensión horizontal contra 0,4h, con h = 8 m).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con un componente de cubierta cargado.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=8,
        altura_cumbrera=11,
        tipo_cubierta=enums.TipoCubierta.UN_AGUA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_cubierta={"Correa": 5.0},
    )


def _edificio_un_agua_angulo_muy_bajo(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a un agua de θ ≈ 0.8°.

    Con altura de alero 8 m y cumbrera a 8.4 m la Nota 5 de la Figura 5.3-5A
    manda estos ángulos a la Figura 5.3-2A: las distancias de las zonas son
    las de la Tabla C 5.3-2 (0,2h, 0,6h y 1,2h, con h = 8 m).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con un componente de cubierta cargado.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=8,
        altura_cumbrera=8.4,
        tipo_cubierta=enums.TipoCubierta.UN_AGUA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_cubierta={"Correa": 5.0},
    )


def _edificio_un_agua_angulo_medio(alero: float = 0):
    """Un edificio de 30 x 40 con cubierta a un agua de θ ≈ 20.1°.

    Con altura de alero 5 m y cumbrera a 16 m la luz de 30 m da un ángulo en
    el rango de la Figura 5.3-5B (10° < θ ≤ 30°), y la distancia "a" queda en
    3 m (0,1 de la menor dimensión horizontal contra 0,4h).

    Args:
        alero: La dimensión del alero.

    Returns:
        El edificio, con un componente de cubierta cargado.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=5,
        altura_cumbrera=16,
        tipo_cubierta=enums.TipoCubierta.UN_AGUA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        alero=alero,
        componentes_cubierta={"Correa": 5.0},
    )


def test_zonas_de_componentes_de_la_tabla_c_5_3_3(qapp):
    """Las zonas de la Figura 5.3-2B cubren la cubierta sin huecos ni solapes.

    Las Zonas 3 son los cuadrados de "a" de lado que se apoyan en la cumbrera
    en las cabeceras; las Zonas 2 son el listón de cumbrera del tramo central
    -que conecta las Zonas 3- y los cuadrados de las cabeceras junto al borde;
    la Zona 1 es el resto. Las áreas se miden en planta y se llevan al plano
    del faldón, cuya inclinación es la flecha de 2 m sobre la semiluz de 15 m.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_angulo_medio()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {zonas.UNO, zonas.DOS, zonas.TRES}

    inclinacion = np.hypot(2, 15) / 15
    ancho_total = 30.0
    profundidad = 40.0
    x_cumbrera = 15.0
    a = 3.0
    ancho_borde = x_cumbrera - a  # campo de borde de cada faldón
    tramo_central = profundidad - 2 * a
    esperadas = {
        # Cuatro cuadrados de "a" de lado en la cumbrera de las cabeceras.
        zonas.TRES: 4 * a * a,
        # Listón de cumbrera del tramo central (los dos faldones) + los cuatro
        # cuadrados de borde de las cabeceras.
        zonas.DOS: 2 * a * tramo_central + 4 * ancho_borde * a,
        zonas.UNO: 2 * ancho_borde * tramo_central,
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(ancho_total * profundidad * inclinacion)


def test_zonas_de_componentes_de_la_tabla_c_5_3_3_con_alero(qapp):
    """Con voladizo las distancias se miden desde su borde exterior (Nota 7).

    La cubierta sigue cubierta por completo y los actores del alero suman el
    área del voladizo: en el trecho central el alero es Zona 1 y en las
    cabeceras Zona 2.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_angulo_medio(alero=1)
    )
    areas_cubierta = _areas_por_zona(director.actores_cubierta)
    areas_alero = _areas_por_zona(director.actores_alero)

    faldon = np.hypot(2, 15)
    assert sum(areas_cubierta.values()) == pytest.approx(2 * faldon * 40)
    assert sum(areas_alero.values()) == pytest.approx(2 * 1 * 40)


def test_la_escena_de_componentes_pinta_todas_las_zonas_de_la_tabla_c_5_3_3(qapp):
    """Cada zona de la Figura 5.3-2B recibe su presión en la escena."""
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(
        escena, _edificio_dos_aguas_angulo_medio(), enums.Unidad.N
    )
    presiones.actualizar_componente_cubierta("Correa")
    zonas = enums.ZonaComponenteCubiertaEdificio
    director = presiones.director
    for zona, actores_zona in director.actores_cubierta.items():
        for actor in actores_zona:
            assert actor.flecha.texto, f"zona {zona.value} sin presión"
    assert set(director.actores_cubierta) == {zonas.UNO, zonas.DOS, zonas.TRES}


def _actores_de(valor):
    """Una vista de los actores de un grupo, sea uno solo o varios.

    El director agrupa la Zona 4 como un actor único y la Zona 5 como un par
    (un listón por borde).

    Args:
        valor: El actor o la tupla de actores del grupo.

    Yields:
        Cada actor del grupo.
    """
    if isinstance(valor, (list, tuple, frozenset)):
        yield from valor
    else:
        yield valor


def test_zonas_de_componentes_de_la_figura_5_4_1(qapp):
    """Las zonas de la Figura 5.4-1 cubren la cubierta sin huecos ni solapes.

    Con la distancia "a" de 3 m, la Zona 3 son las "L" perimetrales de "a" de
    ancho junto a los bordes, la Zona 2 la franja de "2a" que le sigue y la
    Zona 1 el interior. Las áreas se miden en planta y se llevan al plano del
    faldón, cuya inclinación es la flecha de 1 m sobre la semiluz de 15 m.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_gran_altura()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {zonas.UNO, zonas.DOS, zonas.TRES}

    inclinacion = np.hypot(1, 15) / 15
    a = 3.0
    ancho_planta = 30.0
    profundidad = 40.0
    esperadas = {
        # Cuatro "L" de las esquinas: cada una de dos brazos de "a" de espesor
        # y "2a"+"a" de largo, que en la suma dan 3 "a" cuadradas por esquina.
        zonas.TRES: 12 * a**2,
        # Franja de "2a" que sigue a las "L", rodeando el interior.
        zonas.DOS: 2 * a * (ancho_planta + profundidad - 8 * a),
        zonas.UNO: (ancho_planta - 2 * a) * (profundidad - 2 * a),
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(
        ancho_planta * profundidad * inclinacion
    )


def test_zonas_de_paredes_de_la_figura_5_4_1(qapp):
    """Las Zonas 4 y 5 dividen las paredes de la Figura 5.4-1 sin huecos.

    Sobre cada pared, la Zona 4 es el ancho central y la Zona 5 los listones
    de "a" de los bordes: entre las dos cubren la pared completa. Las de
    frente y contrafrente son las que llevan el triángulo del frontón: el
    rectángulo hasta el alero más el triángulo de la pendiente.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_gran_altura()
    )
    paredes = director.obtener_paredes()
    zonas = enums.ZonaComponenteParedEdificio
    areas_por_pared = {
        pared: {
            zona: sum(actor._poligono.area() for actor in _actores_de(actores))
            for zona, actores in zonas_actor.items()
        }
        for pared, zonas_actor in paredes.items()
    }
    for areas in areas_por_pared.values():
        assert set(areas) == {zonas.CUATRO, zonas.CINCO}
        assert areas[zonas.CUATRO] > 0
        assert areas[zonas.CINCO] > 0

    # Frente y contrafrente: rectángulo de 30 x 22 hasta el alero más el
    # frontón de 1 m de flecha sobre la luz de 30 m.
    frente = 30 * 22 + 0.5 * 30 * 1
    for pared in (
        enums.ParedEdificioSprfv.BARLOVENTO,
        enums.ParedEdificioSprfv.SOTAVENTO,
    ):
        assert sum(areas_por_pared[pared].values()) == pytest.approx(frente)


def test_la_escena_de_componentes_pinta_todas_las_zonas_de_la_figura_5_4_1(qapp):
    """Cada zona de la Figura 5.4-1 recibe su presión en la escena.

    Las paredes se evalúan con qz a la altura elegida (Nota 4) tanto en la
    presión positiva como en la negativa: la escena expone las alturas y al
    cambiarlas repinta todas las paredes en los dos modos del signo.
    """
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(
        escena, _edificio_dos_aguas_gran_altura(), enums.Unidad.N
    )
    presiones.actualizar_componente_pared("Viga")
    presiones.actualizar_componente_cubierta("Correa")

    zonas = enums.ZonaComponenteParedEdificio
    director = presiones.director
    for pared, zonas_actor in director.actores_paredes.items():
        for zona, actores in zonas_actor.items():
            for actor in _actores_de(actores):
                assert actor.flecha.texto, (
                    f"pared {pared} zona {zona.value} sin presión"
                )

    assert presiones.por_altura_paredes
    alturas = presiones.alturas_presiones_paredes
    assert alturas and alturas[-1] == pytest.approx(23)

    # La altura de qz cambia el valor de las paredes en los dos modos.
    for tipo in enums.TipoPresionComponentesParedesCubierta:
        presiones.actualizar_tipo_presion(tipo)
        actor_4 = director.actores_paredes[enums.ParedEdificioSprfv.BARLOVENTO][
            zonas.CUATRO
        ]
        presiones.actualizar_altura_paredes(alturas[0])
        assert f"({alturas[0]:.2f} m)" in actor_4.flecha.texto
        presiones.actualizar_altura_paredes(alturas[-1])
        assert f"({alturas[-1]:.2f} m)" in actor_4.flecha.texto


def test_zonas_de_componentes_de_la_tabla_c_5_3_4(qapp):
    """Las zonas de la Figura 5.3-2C cubren la cubierta sin huecos ni solapes.

    La Tabla C 5.3-4 reparte las zonas igual que la 5.3-3, así que las áreas
    esperadas son las mismas con la inclinación del faldón del nuevo ángulo: la
    flecha de 7 m sobre la semiluz de 15 m.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_angulo_empinado()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {zonas.UNO, zonas.DOS, zonas.TRES}

    inclinacion = np.hypot(7, 15) / 15
    ancho_total = 30.0
    profundidad = 40.0
    x_cumbrera = 15.0
    a = 3.0
    ancho_borde = x_cumbrera - a  # campo de borde de cada faldón
    tramo_central = profundidad - 2 * a
    esperadas = {
        # Cuatro cuadrados de "a" de lado en la cumbrera de las cabeceras.
        zonas.TRES: 4 * a * a,
        # Listón de cumbrera del tramo central (los dos faldones) + los cuatro
        # cuadrados de borde de las cabeceras.
        zonas.DOS: 2 * a * tramo_central + 4 * ancho_borde * a,
        zonas.UNO: 2 * ancho_borde * tramo_central,
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(ancho_total * profundidad * inclinacion)


def test_zonas_de_componentes_de_la_tabla_c_5_3_4_con_alero(qapp):
    """Con voladizo las distancias se miden desde su borde exterior (Nota 7).

    Igual que en la 5.3-3: la cubierta sigue cubierta por completo y los
    actores del alero suman el área del voladizo.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(),
        TablaColores(-500, 500),
        _edificio_dos_aguas_angulo_empinado(alero=1),
    )
    areas_cubierta = _areas_por_zona(director.actores_cubierta)
    areas_alero = _areas_por_zona(director.actores_alero)

    faldon = np.hypot(7, 15)
    assert sum(areas_cubierta.values()) == pytest.approx(2 * faldon * 40)
    assert sum(areas_alero.values()) == pytest.approx(2 * 1 * 40)


def test_la_escena_de_componentes_pinta_todas_las_zonas_de_la_tabla_c_5_3_4(qapp):
    """Cada zona de la Figura 5.3-2C recibe su presión en la escena."""
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(
        escena, _edificio_dos_aguas_angulo_empinado(), enums.Unidad.N
    )
    presiones.actualizar_componente_cubierta("Correa")
    zonas = enums.ZonaComponenteCubiertaEdificio
    director = presiones.director
    for zona, actores_zona in director.actores_cubierta.items():
        for actor in actores_zona:
            assert actor.flecha.texto, f"zona {zona.value} sin presión"
    assert set(director.actores_cubierta) == {zonas.UNO, zonas.DOS, zonas.TRES}


def test_zonas_de_componentes_de_la_tabla_c_5_3_5(qapp):
    """Las zonas de la Figura 5.3-2D cubren la cubierta sin huecos ni solapes.

    Cada faldón se divide en dos bandas de profundidad "a" junto a las
    cabeceras y un campo central. Las Zonas 3 son los cuadrados a×a de las
    esquinas; las Zonas 2 el resto de las bandas -el tramo entre la esquina y
    la cumbrera-; la Zona 1 el campo central. Las áreas se miden en planta y
    se llevan al plano del faldón, cuya inclinación es la flecha de 11 m sobre
    la semiluz de 15 m.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_angulo_muy_empinado()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {zonas.UNO, zonas.DOS, zonas.TRES}

    inclinacion = np.hypot(11, 15) / 15
    ancho_total = 30.0
    profundidad = 40.0
    a = 3.0
    esperadas = {
        # Cuatro cuadrados de "a" de lado en las esquinas.
        zonas.TRES: 4 * a * a,
        # Resto de las dos bandas de cabecera (de ancho ancho_total - 2a).
        zonas.DOS: 2 * a * (ancho_total - 2 * a),
        # Campo central a todo el ancho, entre las dos bandas.
        zonas.UNO: ancho_total * (profundidad - 2 * a),
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(ancho_total * profundidad * inclinacion)


def test_zonas_de_componentes_de_la_tabla_c_5_3_5_con_alero(qapp):
    """Con voladizo las distancias se miden desde su borde exterior (Nota 7).

    Igual que en la 5.3-3: la cubierta sigue cubierta por completo y los
    actores del alero suman el área del voladizo.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(),
        TablaColores(-500, 500),
        _edificio_dos_aguas_angulo_muy_empinado(alero=1),
    )
    areas_cubierta = _areas_por_zona(director.actores_cubierta)
    areas_alero = _areas_por_zona(director.actores_alero)

    faldon = np.hypot(11, 15)
    assert sum(areas_cubierta.values()) == pytest.approx(2 * faldon * 40)
    assert sum(areas_alero.values()) == pytest.approx(2 * 1 * 40)


def test_la_escena_de_componentes_pinta_todas_las_zonas_de_la_tabla_c_5_3_5(qapp):
    """Cada zona de la Figura 5.3-2D recibe su presión en la escena."""
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(
        escena, _edificio_dos_aguas_angulo_muy_empinado(), enums.Unidad.N
    )
    presiones.actualizar_componente_cubierta("Correa")
    zonas = enums.ZonaComponenteCubiertaEdificio
    director = presiones.director
    for zona, actores_zona in director.actores_cubierta.items():
        for actor in actores_zona:
            assert actor.flecha.texto, f"zona {zona.value} sin presión"
    assert set(director.actores_cubierta) == {zonas.UNO, zonas.DOS, zonas.TRES}


def test_zonas_de_componentes_de_la_figura_5_3_5a(qapp):
    """Las zonas de la Figura 5.3-5A cubren la cubierta a un agua sin huecos.

    La Zona 3 son los cuadrados de 2a de lado de las esquinas del borde de
    alero y la Zona 3' los de la cumbrera, de 4a de profundidad; la Zona 2 la
    franja de ancho a entre las dos Zonas 3 y la Zona 2' el resto de la franja
    perimetral; la Zona 1 el campo interior. Las áreas se miden en planta y se
    llevan al plano del faldón único, cuya inclinación es la flecha de 3 m
    sobre los 30 m de luz.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_un_agua_angulo_bajo()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {
        zonas.UNO,
        zonas.DOS,
        zonas.DOS_PRIMA,
        zonas.TRES,
        zonas.TRES_PRIMA,
    }

    inclinacion = np.hypot(3, 30) / 30
    ancho_total = 30.0
    profundidad = 40.0
    a = 3.0
    esperadas = {
        # Dos cuadrados de 2a de lado y 4a de profundidad contra la cumbrera.
        zonas.TRES_PRIMA: 2 * (2 * a) * (4 * a),
        # El resto de la franja perimetral: dos bandas de 2a a los bordes
        # testeros y el tramo de 2a de ancho contra la cumbrera.
        zonas.DOS_PRIMA: 2 * (2 * a) * (ancho_total - 4 * a)
        + (2 * a) * (profundidad - 8 * a),
        # Dos cuadrados de 2a de lado contra el alero.
        zonas.TRES: 2 * (2 * a) * (2 * a),
        # La franja de "a" de ancho entre las dos Zonas 3.
        zonas.DOS: a * (profundidad - 4 * a),
        # El campo interior.
        zonas.UNO: (ancho_total - 3 * a) * (profundidad - 4 * a),
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(ancho_total * profundidad * inclinacion)


def test_zonas_de_componentes_de_la_figura_5_3_5a_con_alero(qapp):
    """Con voladizo las distancias se miden desde su borde exterior (Nota 7).

    La cubierta a un agua sigue cubierta por completo y los actores del alero
    suman el área del voladizo, que es de 1 m sobre el plano del faldón único.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(),
        TablaColores(-500, 500),
        _edificio_un_agua_angulo_bajo(alero=1),
    )
    areas_cubierta = _areas_por_zona(director.actores_cubierta)
    areas_alero = _areas_por_zona(director.actores_alero)

    faldon = np.hypot(3, 30)
    assert sum(areas_cubierta.values()) == pytest.approx(faldon * 40)
    assert sum(areas_alero.values()) == pytest.approx(1 * 40)


def test_la_escena_de_componentes_pinta_todas_las_zonas_de_la_figura_5_3_5a(qapp):
    """Cada zona de la Figura 5.3-5A recibe su presión en la escena."""
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(
        escena, _edificio_un_agua_angulo_bajo(), enums.Unidad.N
    )
    presiones.actualizar_componente_cubierta("Correa")
    zonas = enums.ZonaComponenteCubiertaEdificio
    director = presiones.director
    for zona, actores_zona in director.actores_cubierta.items():
        for actor in actores_zona:
            assert actor.flecha.texto, f"zona {zona.value} sin presión"
    assert set(director.actores_cubierta) == {
        zonas.UNO,
        zonas.DOS,
        zonas.DOS_PRIMA,
        zonas.TRES,
        zonas.TRES_PRIMA,
    }


def test_zonas_de_componentes_de_la_tabla_c_5_3_5b(qapp):
    """Las zonas de la Figura 5.3-5B cubren la cubierta a un agua sin huecos.

    La Zona 3 son los rectángulos de 2a de ancho y 4a de profundidad contra la
    cumbrera en las cabeceras; la Zona 2 la franja perimetral del resto -las
    dos bandas de "a" de los bordes testeros, el tramo de cumbrera entre las
    Zonas 3 y la franja de "a" a todo lo largo del alero-; la Zona 1 el campo
    interior. Las áreas se miden en planta y se llevan al plano del faldón
    único, cuya inclinación es la flecha de 11 m sobre los 30 m de luz.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_un_agua_angulo_medio()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {zonas.UNO, zonas.DOS, zonas.TRES}

    inclinacion = np.hypot(11, 30) / 30
    ancho_total = 30.0
    profundidad = 40.0
    a = 3.0
    esperadas = {
        # Dos rectángulos de 2a de ancho y 4a de profundidad contra la cumbrera.
        zonas.TRES: 2 * (2 * a) * (4 * a),
        # Dos bandas de "a" a los bordes testeros, el tramo de 2a de ancho
        # contra la cumbrera y la franja de "a" a todo lo largo del alero.
        zonas.DOS: 2 * a * (ancho_total - 3 * a)
        + (2 * a) * (profundidad - 8 * a)
        + a * profundidad,
        # El campo interior.
        zonas.UNO: (ancho_total - 3 * a) * (profundidad - 2 * a),
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(ancho_total * profundidad * inclinacion)


def test_zonas_de_componentes_de_la_tabla_c_5_3_5b_con_alero(qapp):
    """Con voladizo las distancias se miden desde su borde exterior (Nota 7).

    Igual que en la Figura 5.3-5A: la cubierta a un agua sigue cubierta por
    completo y los actores del alero suman el área del voladizo.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(),
        TablaColores(-500, 500),
        _edificio_un_agua_angulo_medio(alero=1),
    )
    areas_cubierta = _areas_por_zona(director.actores_cubierta)
    areas_alero = _areas_por_zona(director.actores_alero)

    faldon = np.hypot(11, 30)
    assert sum(areas_cubierta.values()) == pytest.approx(faldon * 40)
    assert sum(areas_alero.values()) == pytest.approx(1 * 40)


def test_la_escena_de_componentes_pinta_todas_las_zonas_de_la_tabla_c_5_3_5b(qapp):
    """Cada zona de la Figura 5.3-5B recibe su presión en la escena."""
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(
        escena, _edificio_un_agua_angulo_medio(), enums.Unidad.N
    )
    presiones.actualizar_componente_cubierta("Correa")
    zonas = enums.ZonaComponenteCubiertaEdificio
    director = presiones.director
    for zona, actores_zona in director.actores_cubierta.items():
        for actor in actores_zona:
            assert actor.flecha.texto, f"zona {zona.value} sin presión"
    assert set(director.actores_cubierta) == {zonas.UNO, zonas.DOS, zonas.TRES}


def test_zonas_de_componentes_de_la_tabla_c_5_3_2_a_un_agua(qapp):
    """Con θ ≤ 3° la cubierta a un agua reparte como la Figura 5.3-2A.

    La Nota 5 de la Figura 5.3-5A manda esos ángulos a la Figura 5.3-2A, sobre
    el faldón único: la Zona 3 son cuatro "L" de 0,2h en las esquinas, la 2 la
    franja perimetral de 0,6h, la 1 la franja de 0,6h a 1,2h y la 1' el
    interior.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_un_agua_angulo_muy_bajo()
    )
    areas = _areas_por_zona(director.actores_cubierta)

    zonas = enums.ZonaComponenteCubiertaEdificio
    assert set(areas) == {zonas.UNO_PRIMA, zonas.UNO, zonas.DOS, zonas.TRES}

    # Las áreas se calculan en planta y se llevan al plano del faldón único,
    # cuya inclinación es la flecha de 0.4 m sobre los 30 m de luz.
    inclinacion = np.hypot(0.4, 30) / 30
    zona_3 = 4 * (2 * 1.6 * 4.8 - 1.6**2)
    esperadas = {
        zonas.TRES: zona_3,
        zonas.DOS: 30 * 40 - 20.4 * 30.4 - zona_3,
        zonas.UNO: 20.4 * 30.4 - 10.8 * 20.8,
        zonas.UNO_PRIMA: 10.8 * 20.8,
    }
    for zona, area_en_planta in esperadas.items():
        assert areas[zona] == pytest.approx(area_en_planta * inclinacion)
    assert sum(areas.values()) == pytest.approx(30 * 40 * inclinacion)


def test_la_escena_lee_el_positivo_por_zona_con_parapeto(qapp):
    """Con parapeto, la Zona 2 pinta su propio positivo y no el de la zona "todas".

    Es el camino que habilita la Nota 5 de la Figura 5.3-2A: la escena busca
    primero el positivo de la zona y sólo cae en el único si no existe.

    La velocidad es alta a propósito: con una baja, la presión mínima de
    ±500 N/m² recorta los dos valores y la diferencia no se vería.
    """
    from zonda.cirsoc import Edificio
    from zonda.graficos.escenas import edificio as escena_edificio

    edificio = Edificio(
        ancho=30,
        longitud=40,
        elevacion=0,
        altura_alero=8,
        altura_cumbrera=9,
        tipo_cubierta=enums.TipoCubierta.DOS_AGUAS,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=70,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        parapeto=1,
        componentes_cubierta={"Correa": 5.0},
    )
    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(escena, edificio, enums.Unidad.N)
    presiones.actualizar_componente_cubierta("Correa")
    presiones.actualizar_tipo_presion(
        enums.TipoPresionComponentesParedesCubierta.POSITIVA
    )
    presiones.actualizar_gcpi(1)

    zonas = enums.ZonaComponenteCubiertaEdificio
    actores = presiones.director.obtener_cubierta()
    textos = {
        zona: actores[zona][0].flecha.texto
        for zona in (zonas.UNO_PRIMA, zonas.UNO, zonas.DOS, zonas.TRES)
    }
    # Las Zonas 1' y 1 comparten el positivo único; las 2 y 3 el de pared.
    assert textos[zonas.UNO_PRIMA] == textos[zonas.UNO]
    assert textos[zonas.DOS] == textos[zonas.TRES]
    assert textos[zonas.DOS] != textos[zonas.UNO]


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


def test_la_escena_de_componentes_pinta_todas_las_zonas_de_la_tabla_c_5_3_2(qapp):
    """Cada zona de la Figura 5.3-2A recibe su presión en la escena.

    Es la zona 1' la que interesa: si la tabla de resultados no trajera una
    fila para una zona nueva, sus actores quedarían sin valor y sin flecha.
    """
    from zonda.graficos.escenas import edificio as escena_edificio

    edificio = _edificio_dos_aguas_angulo_bajo(alero=1)
    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(escena, edificio, enums.Unidad.N)
    presiones.actualizar_componente_cubierta("Correa")

    zonas = enums.ZonaComponenteCubiertaEdificio
    todas = {zonas.UNO_PRIMA, zonas.UNO, zonas.DOS, zonas.TRES}
    for tipo in enums.TipoPresionComponentesParedesCubierta:
        presiones.actualizar_tipo_presion(tipo)
        actores_cubierta = presiones.director.obtener_cubierta()
        actores_alero = presiones.director.obtener_alero()
        assert set(actores_cubierta) == todas
        # El voladizo de 1 m entra entero en la franja de la Zona 2 (0.6h =
        # 4.8 m), así que sobre él no hay polígonos de las Zonas 1 y 1'.
        assert set(actores_alero) == {zonas.DOS, zonas.TRES}
        for actores in (actores_cubierta, actores_alero):
            for zona, actores_zona in actores.items():
                for actor in actores_zona:
                    assert actor.flecha.texto, f"zona {zona.value} sin presión"


# --- Parapeto --------------------------------------------------------------


def _edificio_plana_con_parapeto(ancho: float = 30, parapeto: float = 1):
    """Un edificio de cubierta plana con parapeto.

    30 (o el ancho dado) x 40 con alero y cumbrera a 10 m, así que la
    coronación del parapeto queda a 11 m.

    Args:
        ancho: El ancho del edificio.
        parapeto: La dimensión del parapeto.

    Returns:
        El edificio, con componentes de pared y cubierta cargados.
    """
    from zonda.cirsoc import Edificio

    return Edificio(
        ancho=ancho,
        longitud=40,
        elevacion=0,
        altura_alero=10,
        altura_cumbrera=10,
        tipo_cubierta=enums.TipoCubierta.PLANA,
        cerramiento=enums.Cerramiento.CERRADO,
        velocidad=45,
        factor_g_simplificado=True,
        categoria_exp=enums.CategoriaExposicion.B,
        considerar_topografia=False,
        parapeto=parapeto,
        area_parapeto=2,
        componentes_paredes={"Viga": 10.0},
        componentes_cubierta={"Correa": 5.0},
    )


def test_la_geometria_dibuja_las_bandas_del_parapeto(qapp):
    """La vista de geometría agrega una franja por pared, de alero a coronación."""
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.Geometria(
        Escena3D(), 30, 40, 10, 10, enums.TipoCubierta.PLANA, parapeto=1
    )
    director.inicializar_actores()

    paredes = enums.ParedEdificioSprfv
    actores = director.actores_parapeto
    assert actores[paredes.BARLOVENTO].poligono.area() == pytest.approx(30)
    assert actores[paredes.SOTAVENTO].poligono.area() == pytest.approx(30)
    assert sum(a.poligono.area() for a in actores[paredes.LATERAL]) == pytest.approx(
        2 * 40
    )


def test_la_geometria_sin_parapeto_no_dibuja_bandas(qapp):
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.Geometria(
        Escena3D(), 30, 40, 10, 10, enums.TipoCubierta.PLANA
    )
    director.inicializar_actores()
    assert director.actores_parapeto is None


def test_las_bandas_del_parapeto_cubren_el_perimetro_sin_huecos_ni_solapes(qapp):
    """Cada banda se parte en borde y esquinas y cubre su pared completa.

    Con h = 10 m la esquina del Caso A mide 0,6 h = 6 m y la del Caso B, la
    distancia "a" = 3 m: en ambos casos entran dos esquinas y el borde.
    """
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_plana_con_parapeto()
    )

    paredes = enums.ParedEdificioSprfv
    zonas = enums.ZonaParapeto
    actores = director.actores_parapeto
    assert set(actores) == {paredes.BARLOVENTO, paredes.SOTAVENTO}
    for banda in actores.values():
        assert set(banda) == {zonas.BORDE, zonas.ESQUINA}
        assert len(banda[zonas.ESQUINA]) == 2
        largo = sum(
            actor.poligono.area() for tramos in banda.values() for actor in tramos
        )
        assert largo == pytest.approx(30)


def test_cuando_el_ancho_no_alcanza_la_banda_entra_entera_en_la_esquina(qapp):
    from zonda.graficos.directores import edificio as directores_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_plana_con_parapeto(ancho=10)
    )
    zonas = enums.ZonaParapeto
    banda = director.actores_parapeto[enums.ParedEdificioSprfv.BARLOVENTO]
    # Con ancho 10 y esquina 6 m no hay tramo de borde.
    assert set(banda) == {zonas.ESQUINA}
    assert len(banda[zonas.ESQUINA]) == 1
    assert banda[zonas.ESQUINA][0].poligono.area() == pytest.approx(10)


def test_la_escena_sprfv_actualiza_las_bandas_del_parapeto_por_direccion(qapp):
    """En cada dirección el parapeto a barlovento y el de sotavento tienen su valor.

    El coeficiente no depende de la dirección, así que las bandas que cambian
    de pared conservan el mismo valor.
    """
    from zonda.graficos.escenas import edificio as escena_edificio

    paredes = enums.ParedEdificioSprfv
    direcciones = enums.DireccionVientoMetodoDireccionalSprfv

    escena = Escena3D()
    presiones = escena_edificio.PresionesSprfvMetodoDireccional(
        escena, _edificio_plana_con_parapeto(), enums.Unidad.N
    )
    presiones.actualizar_direccion_viento(direcciones.PARALELO)
    actores = presiones.director.obtener_parapeto()
    assert set(actores) == {paredes.BARLOVENTO, paredes.SOTAVENTO}
    texto_barlovento = actores[paredes.BARLOVENTO].flecha.texto
    texto_sotavento = actores[paredes.SOTAVENTO].flecha.texto

    presiones.actualizar_direccion_viento(direcciones.NORMAL)
    actores = presiones.director.obtener_parapeto()
    # En la dirección normal son los laterales los que toman los roles.
    assert actores[paredes.BARLOVENTO].flecha.texto == texto_barlovento
    assert actores[paredes.SOTAVENTO].flecha.texto == texto_sotavento


def test_la_escena_de_componentes_asigna_presion_a_todas_las_bandas_del_parapeto(qapp):
    """Los dos casos de carga quedan pintados y responden al signo del GCpi."""
    from zonda.graficos.escenas import edificio as escena_edificio

    paredes = enums.ParedEdificioSprfv
    zonas = enums.ZonaParapeto

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(
        escena, _edificio_plana_con_parapeto(), enums.Unidad.N
    )
    banda = presiones.director.actores_parapeto[paredes.BARLOVENTO]
    for tramos in presiones.director.actores_parapeto.values():
        for actores in tramos.values():
            for actor in actores:
                assert actor.flecha.texto

    texto_positiva = banda[zonas.BORDE][0].flecha.texto
    presiones.actualizar_gcpi(1)
    assert banda[zonas.BORDE][0].flecha.texto != texto_positiva


def test_sin_parapeto_las_escenas_no_tienen_bandas(qapp):
    from zonda.graficos.directores import edificio as directores_edificio
    from zonda.graficos.escenas import edificio as escena_edificio

    director = directores_edificio.PresionesComponentes(
        Escena3D(), TablaColores(-500, 500), _edificio_dos_aguas_angulo_bajo()
    )
    assert director.obtener_parapeto() == {}

    presiones = escena_edificio.PresionesSprfvMetodoDireccional(
        Escena3D(), _edificio_dos_aguas_angulo_bajo(), enums.Unidad.N
    )
    presiones.actualizar_direccion_viento(
        enums.DireccionVientoMetodoDireccionalSprfv.PARALELO
    )
    assert presiones.director.obtener_parapeto() is None


# --- El detalle de cálculo de una zona -----------------------------------
#
# Al tocar una zona en la vista 3D se muestra cómo se calculó su presión. El
# detalle se arma en zonda.graficos.detalle y viaja en la fila: el actor la
# retiene en cada asignar_presion y la expone por su propiedad `detalle`.


def _una_fila_edificio():
    """Una fila de edificio con valores conocidos, para el texto del detalle."""
    from zonda.cirsoc.resultados import FilaEdificio, PresionVelocidad

    return FilaEdificio(
        zona=enums.ZonaEdificio.PAREDES,
        sistema=enums.SistemaResistente.SPRFV,
        q=PresionVelocidad(altura=10.0, kz=1.04, kzt=1.0, valor=850.0),
        cp=-0.7,
        factor_rafaga=0.85,
        gcpi=0.18,
        pos=-510.0,
        neg=-731.0,
        referencia="Fig. 2.4-1",
        pared=enums.ParedEdificioSprfv.SOTAVENTO,
    )


def test_asignar_presion_retiene_la_fila(qapp):
    escena = Escena3D()
    tabla = TablaColores(-1000, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    assert actor.fila is None

    fila = _una_fila_edificio()
    actor.asignar_presion(-510, enums.Unidad.N, fila=fila)
    assert actor.fila is fila


def test_la_flecha_conoce_a_su_actor(qapp):
    """La vista usa la referencia para seleccionar la zona tocando la flecha."""
    escena = Escena3D()
    tabla = TablaColores(-500, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    assert actor.flecha.actor is actor


def test_el_detalle_muestra_el_desglose_del_calculo(qapp):
    """El desglose es el mismo que imprime la tabla del reporte, un valor por línea."""
    escena = Escena3D()
    tabla = TablaColores(-1000, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    actor.asignar_presion(-510, enums.Unidad.N, fila=_una_fila_edificio())

    detalle = actor.detalle
    assert detalle["titulo"] == "Pared Sotavento"
    # La vista acomoda las filas en dos columnas: tienen que cruzar como
    # listas de listas, no como tuplas, que llegan como objetos opacos sin
    # length ni indexación.
    assert isinstance(detalle["filas"], list)
    assert all(isinstance(fila, list) for fila in detalle["filas"])
    filas = dict(detalle["filas"])
    assert filas["q"] == "= 850.00 N/m²"
    assert filas["Kz"] == "= 1.04"
    assert filas["Kzt"] == "= 1.00"
    assert filas["Ke"] == "= 1.00"
    assert filas["z"] == "= 10.00 m"
    assert filas["Cp"] == "= -0.70"
    assert filas["G"] == "= 0.85"
    assert filas["GCpi"] == "= +0.18"
    assert filas["p"] == "= -510.00 N/m²"
    assert filas["Ref"] == "Fig. 2.4-1"


def test_el_detalle_muestra_el_gcpi_del_signo_mostrado(qapp):
    """El signo del GCpi y la presión son los de la zona seleccionada."""
    escena = Escena3D()
    tabla = TablaColores(-1000, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    actor.asignar_presion(-731, enums.Unidad.N, fila=_una_fila_edificio())

    filas = dict(actor.detalle["filas"])
    assert filas["GCpi"] == "= -0.18"
    assert filas["p"] == "= -731.00 N/m²"


def test_el_detalle_convierte_a_la_unidad_de_la_escena(qapp):
    escena = Escena3D()
    tabla = TablaColores(-1000, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    actor.asignar_presion(-510, enums.Unidad.KN, fila=_una_fila_edificio())

    filas = dict(actor.detalle["filas"])
    assert filas["q"] == "= 0.85 kN/m²"
    assert filas["p"] == "= -0.51 kN/m²"


def test_el_detalle_sin_presion_interna_muestra_una_sola_presion(qapp):
    """El alero y el parapeto SPRFV no llevan presión interna."""
    from dataclasses import replace

    fila = replace(_una_fila_edificio(), con_presion_interna=False, pos=-731.0)
    escena = Escena3D()
    tabla = TablaColores(-1000, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    actor.asignar_presion(-731, enums.Unidad.N, fila=fila)

    filas = dict(actor.detalle["filas"])
    assert filas["p"] == "= -731.00 N/m²"
    assert "GCpi" not in filas


def test_el_detalle_del_parapeto_componentes_desglosa_los_coeficientes(qapp):
    """El Art. 5.6 suma las dos caras del parapeto: el desglose lo muestra."""
    from dataclasses import replace

    fila = replace(
        _una_fila_edificio(),
        pared=enums.ParedEdificioSprfv.BARLOVENTO,
        zona=enums.ZonaEdificio.PARAPETO,
        sistema=enums.SistemaResistente.COMPONENTES,
        zona_parapeto=enums.ZonaParapeto.BORDE,
        cp_frontal=0.12,
        cp_posterior=-1.2,
        cp=-1.08,
        pos=-918.0,
        neg=-1000.0,
    )
    escena = Escena3D()
    tabla = TablaColores(-1000, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    actor.asignar_presion(-918, enums.Unidad.N, fila=fila)

    detalle = actor.detalle
    assert detalle["titulo"] == "Parapeto - Caso Barlovento - Borde"
    filas = dict(detalle["filas"])
    assert filas["GCp frontal"] == "= 0.12"
    assert filas["GCp posterior"] == "= -1.20"
    assert filas["GCp neto"] == "= -1.08"
    assert filas["GCpi"] == "= +0.18"


def test_el_detalle_de_un_actor_sin_fila_es_none(qapp):
    """Los actores de geometría no llevan fila: la vista no les abre popup."""
    escena = Escena3D()
    tabla = TablaColores(-500, 500)
    actor = ActorPresion(escena, CUADRADO, tabla_colores=tabla, presion=True)
    actor.asignar_presion(500, enums.Unidad.N)
    assert actor.detalle is None


def test_el_detalle_del_cartel_muestra_area_y_fuerza(qapp, cartel):
    from zonda.graficos.escenas import cartel as escena_cartel

    escena = Escena3D()
    escena_cartel.Presiones(escena, cartel, enums.Unidad.N, enums.Unidad.KN)
    actor = next(a for a in escena.actores_presion if a.flecha.visible)

    detalle = actor.detalle
    assert detalle["titulo"] == "Cartel - Caso A"
    filas = dict(detalle["filas"])
    assert filas["Cf"].startswith("= ")
    assert filas["Área"].startswith("= ")
    assert filas["F"].startswith("= ")
    assert "kN" in filas["F"]
    assert filas["Ref"]


def test_la_escena_sprfv_entrega_la_fila_de_cada_actor_visible(qapp, edificio):
    """Toda zona con etiqueta visible tiene su fila para el detalle."""
    from zonda.cirsoc.resultados import FilaEdificio
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesSprfvMetodoDireccional(
        escena, edificio, enums.Unidad.N
    )
    presiones.actualizar_direccion_viento(
        enums.DireccionVientoMetodoDireccionalSprfv.PARALELO
    )
    alturas = presiones.alturas_presion_barlovento[
        enums.DireccionVientoMetodoDireccionalSprfv.PARALELO
    ]
    presiones.actualizar_altura_pared_barlovento(alturas)
    presiones.actualizar_gcpi(1)

    # La fila de la pared a sotavento es exactamente la del índice.
    fila_esperada = presiones._paredes[
        (
            enums.DireccionVientoMetodoDireccionalSprfv.PARALELO,
            enums.ParedEdificioSprfv.SOTAVENTO,
        )
    ].unica()
    actor = presiones._actores_actuales_paredes[enums.ParedEdificioSprfv.SOTAVENTO]
    assert isinstance(actor.fila, FilaEdificio)
    assert actor.fila is fila_esperada

    visibles = [a for a in escena.actores_presion if a.flecha.visible]
    assert visibles
    for actor in visibles:
        assert actor.fila is not None, "una zona visible quedó sin fila"


def test_la_escena_de_componentes_entrega_la_fila_de_cada_actor_visible(qapp, edificio):
    from zonda.graficos.escenas import edificio as escena_edificio

    escena = Escena3D()
    presiones = escena_edificio.PresionesComponentes(escena, edificio, enums.Unidad.N)
    presiones.actualizar_componente_pared("Viga")
    presiones.actualizar_componente_cubierta("Correa")
    presiones.actualizar_gcpi(1)

    visibles = [a for a in escena.actores_presion if a.flecha.visible]
    assert visibles
    for actor in visibles:
        assert actor.fila is not None, "una zona visible quedó sin fila"


def test_la_escena_del_cartel_entrega_la_fila_de_cada_actor_visible(qapp, cartel):
    from zonda.graficos.escenas import cartel as escena_cartel

    escena = Escena3D()
    presiones = escena_cartel.Presiones(escena, cartel, enums.Unidad.N, enums.Unidad.N)
    for caso in enums.CasoCartel:
        presiones.actualizar_caso(caso)
        visibles = [a for a in escena.actores_presion if a.flecha.visible]
        assert visibles
        for actor in visibles:
            assert actor.fila is not None, "una zona visible quedó sin fila"


def test_la_escena_de_la_cubierta_aislada_entrega_la_fila_de_cada_actor_visible(
    qapp, cubierta_aislada
):
    from zonda.graficos.escenas import aisladas as escena_aisladas

    escena = Escena3D()
    presiones = escena_aisladas.Presiones(escena, cubierta_aislada, enums.Unidad.N)
    for direccion in enums.DireccionVientoCubiertaAislada:
        presiones.actualizar_direccion(direccion)
        visibles = [a for a in escena.actores_presion if a.flecha.visible]
        assert visibles
        for actor in visibles:
            assert actor.fila is not None, "una zona visible quedó sin fila"
            detalle = actor.detalle
            filas = dict(detalle["filas"])
            assert filas["Cpn"].startswith("= ")
            assert filas["p fricción"].startswith("= ")
