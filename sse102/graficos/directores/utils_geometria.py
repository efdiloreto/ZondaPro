from __future__ import annotations

from typing import TYPE_CHECKING, List, Union, Tuple

import numpy as np
import vg

if TYPE_CHECKING:
    from sse102.tipos import Punto, Punto2D, ParNumerico


def punto_sobre_vector(
    distancia: float, origen: Punto2D, fin: Punto2D, dist_eucl: bool = False
) -> Union[np.ndarray, Punto2D]:
    """Obtiene la coordenada de un punto sobre un vector dado por los puntos origen y fin, a una distancia dada sobre el
    vector desde el punto origen.

    Args:
        distancia: La distancia sobre el vector.
        origen: El puntos origen.
        fin: El punto fin.
        dist_eucl: Indica si la distancia es la distancia entre los puntos, en este caso retorna el valor de fin.

    Examples:

        Se quiere conocer la coordenada de un punto que se encuentra a una distancia de "2" del punto origen
        sobre el vector que forman los puntos (0, 6) y (15, 16).

        >>> punto_sobre_vector(2, (0, 6), (15, 16))  # Resultado = array([1.66410059, 7.10940039])

    Returns:
        Las coordenadas finales (o se podria decir el punto final) del vector respecto al vector origen.
    """
    if dist_eucl:
        return fin
    _origen = np.array(origen)
    _fin = np.array(fin)
    norm_esc = vg.normalize(_fin - _origen) * distancia
    return _origen + norm_esc


def coords_pared_rectangular(
    ancho: float,
    alt_izq: float,
    alt_der: float,
    x0: float = 0.0,
    z0: float = 0.0,
    elevacion: float = 0.0,
    sobre_eje_z: bool = False,
    invertir_sentido: bool = False,
):
    """

    Args:
        ancho: El ancho de la pared.
        alt_izq: La altura sobre el lado izquierdo.
        alt_der: La altura sobre el lado derecho.
        x0: La distancia de inicio sobre el eje X.
        z0: La profundidad sobre el eje Z en la que se encuentra.
        elevacion: La elevación inferior (o valor sobre el eje Y inicial)
        sobre_eje_z: Indica si la pared se encuentra sobre el eje Z. En este caso X se intercambia con Z.
        invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se quiere
            que la normal al poligono en VTK apareza de un lado o del otro.

    Returns:
        Una lista con los puntos coordenadas.
    """
    base_izq = (x0, elevacion, z0)
    alero_izq = (x0, alt_izq, z0)
    alero_der = (x0 + ancho, alt_der, z0)
    base_der = (x0 + ancho, elevacion, z0)

    # Es una lista porque tiene que permitir insertar un punto, por ejemplo el punto de cumbrera para la pared con cubierta a dos agua.
    coords = [base_izq, alero_izq, alero_der, base_der]
    if sobre_eje_z:
        coords = [(z, y, x) for x, y, z in coords]
    if invertir_sentido:
        return coords[::-1]
    return coords


def coords_zona_cubierta(
    origen: Punto2D,
    fin: Punto2D,
    z_inicio: float,
    z_fin: float,
    dist_inicio: float = 0,
    dist_fin: float = 0,
    dist_eucl: bool = False,
    invertir_sentido: bool = False,
) -> Tuple[Punto, Punto, Punto, Punto]:
    """Crea las coordenadas para un sector de cubierta que sirven para generar un poligono en VTK.

    La inclinacion de la cubierta esta dada por los puntos origen y fin, mientras que los valores de z_inicio y z_fin
    corresponden a los valores de inicio y fin sobre el eje Z (perpendicular a la pantalla).

    Si la distancia euclidiana esta activa, se calculan las coordenadas para los puntos origen y fin que dan la inclinacion
    a la cubierta. Por ejemplo, seria el caso de un faldon de cubierta entero.

    Si la distancia euclidiana no está activa, se calculan las coordenadas para una zona de la cubierta que empieza a una
    distancia inicial y termina a una distancia final, ambas calculadas desde el punto de origen, siguiendo la inclinación
    que da el vector dado por los puntos origen y fin. Por ejemplo este es el caso cuando se tiene que generar diferentes
    zonas sobre la cubierta para viento normal a la cumbrera o para las zonas de los componentes.

    Ver gráfico: https://i.imgur.com/kHgFXjN.png

    Args:
        origen: El punto origen desde donde se miden las distancias.
        fin: El punto que define el limite y ademas, junto con el punto origen, le da la dirección al vector sobre el
            cual se ubican los puntos calculados en las distancias.
        z_inicio: La profundidad inicial del poligono.
        z_fin: La profundidad final del poligono.
        dist_inicio: Distancia desde el punto origen, que define el inicio del poligono sobre el vector que forman los
            puntos origen y fin.
        dist_fin: Distancia desde el punto origen, que define el inicio del poligono sobre el vector que forman los
            puntos origen y fin.
        dist_eucl: Indica si la distancia inicial coincide con el punto origen (distancia = 0) y la distancia final coincide
            con el punto fin (distancia = distancia entre puntos).
        invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se quiere
            que la normal al poligono en VTK apareza de un lado o del otro.

    Returns:
        Las coordenadas del poligono.
    """
    x_inicio, y_inicio = punto_sobre_vector(dist_inicio, origen, fin)
    x_fin, y_fin = punto_sobre_vector(dist_fin, origen, fin, dist_eucl)
    coords = (
        (x_inicio, y_inicio, z_inicio),
        (x_fin, y_fin, z_inicio),
        (x_fin, y_fin, z_fin),
        (x_inicio, y_inicio, z_fin),
    )
    if invertir_sentido:
        return coords[::-1]
    return coords


def proyeccion_punto_horizontal_sobre_cubierta(valor_x: float, origen: Punto2D, fin: Punto2D) -> Punto2D:
    """Proyecta un punto horizontal 2D, el cual se asume que es P=(valor_x, 0), sobre la cubierta cuya inclinacion esta
    dada por el vector que forman los puntos origen y fin.

    Ver gráfico: https://i.imgur.com/wGj93BA.png

    Args:
        valor_x: Coordenada X.
        origen: El punto 2D que da inicio al vector que forma la cubierta.
        fin: El punto 2D que da inicio al vector que forma la cubierta.

    Returns:
        Punto 2D sobre la cubierta.
    """
    x, y = zip(origen, fin)
    return valor_x, np.interp(valor_x, x, y, left=y[1], right=y[0])


def coords_zona_cubierta_desde_proyeccion(
    zona: ParNumerico, origen: Punto2D, fin: Punto2D, z_inicio: float, z_fin: float, invertir_sentido: bool = False
):
    """Crea las coordenadas para un sector de cubierta que sirven para generar un poligono en VTK, desde la proyeccion
    de dos puntos sobre el eje X.

    Args:
        zona: Zona representada por dos valores sobre el eje X lo cuales indican el inicio y fin de la misma.
        origen: El punto origen desde donde se miden las distancias.
        fin: El punto que define el limite y ademas, junto con el punto origen, le da la dirección al vector sobre el
            cual se ubican los puntos calculados en las distancias.
        z_inicio: La profundidad inicial del poligono.
        z_fin: La profundidad final del poligono.
        invertir_sentido: Indica si los puntos se tiene que retornar en el sentido inverso. Es util para cuando se quiere
            que la normal al poligono en VTK apareza de un lado o del otro.

    Returns:
        La zona de cubierta.
    """
    dist_inicio, dist_fin = zona
    array_origen = np.array(origen + (0,))  # Se le suma la coordenada z ya que lo requiere la función
    array_punto_inicio_proyectado = np.array(
        proyeccion_punto_horizontal_sobre_cubierta(dist_inicio, origen, fin) + (0,)
    )
    array_punto_fin_proyectado = np.array(proyeccion_punto_horizontal_sobre_cubierta(dist_fin, origen, fin) + (0,))
    # noinspection PyTypeChecker
    dist_inicio_proyectada: float = vg.euclidean_distance(array_origen, array_punto_inicio_proyectado)
    # noinspection PyTypeChecker
    dist_fin_proyectada: float = vg.euclidean_distance(array_origen, array_punto_fin_proyectado)
    return coords_zona_cubierta(
        origen,
        fin,
        z_inicio,
        z_fin,
        dist_inicio_proyectada,
        dist_fin_proyectada,
        dist_eucl=False,
        invertir_sentido=invertir_sentido,
    )
