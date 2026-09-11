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

"""El detalle de cálculo de una fila de resultados, listo para la vista 3D.

Al tocar una zona de presión la vista muestra cómo se calculó su valor. Este
módulo es el único lugar donde se arma ese texto: usa los mismos datos y el
mismo desglose que la tabla del reporte (``macros.md``), con un solo criterio
para unidades y etiquetas. La vista sólo dibuja lo que acá sale.

El detalle son pares ``etiqueta`` / ``valor``: la vista los acomoda en dos
columnas y los valores quedan alineados, todos arrancando con el ``=``. La
presión que se muestra es la que la vista tiene asignada —con el signo de
presión interna vigente—, no las dos del par.
"""

from __future__ import annotations

from zonda.cirsoc.resultados import (
    FilaCartel,
    FilaComponentesCubiertaAislada,
    FilaCubiertaAislada,
    FilaEdificio,
)
from zonda.enums import (
    SistemaResistente,
    TipoPresionComponentesParedesCubierta,
    Unidad,
)
from zonda.unidades import convertir_unidad

Fila = list[str]
"""Un par ``[etiqueta, valor]`` del detalle."""


def texto(
    fila: FilaEdificio
    | FilaCartel
    | FilaCubiertaAislada
    | FilaComponentesCubiertaAislada,
    unidad: Unidad,
    unidad_fuerza: Unidad | None = None,
    presion_aplicada: float | None = None,
) -> dict[str, object]:
    """Arma el detalle de cálculo de una fila de resultados.

    Args:
        fila: La fila de la que se quiere el detalle.
        unidad: La unidad en la que se muestran las presiones.
        unidad_fuerza: La unidad para las fuerzas. Sólo la usan las filas del
            cartel.
        presion_aplicada: La presión que la vista tiene asignada, en N/m². Es
            la que define el signo del GCpi que se muestra y el valor de la
            fila ``p``.

    Returns:
        Un diccionario con ``titulo`` y ``filas``. El título identifica la
        zona; cada fila es el par ``[etiqueta, valor]``, con el valor
        arrancando en ``=``.
    """
    titulo, filas = _por_tipo_de_fila(fila, unidad, unidad_fuerza, presion_aplicada)
    # Las filas van como listas y no como tuplas a propósito: PyQt convierte
    # las listas a QVariantList y QML las ve como arrays, pero una tupla
    # anidada en el diccionario cruza como objeto opaco, sin length ni
    # indexación, y la vista no puede recorrerla.
    return {"titulo": titulo, "filas": [[etiqueta, valor] for etiqueta, valor in filas]}


def _por_tipo_de_fila(
    fila, unidad: Unidad, unidad_fuerza: Unidad | None, presion_aplicada: float | None
) -> tuple[str, list[Fila]]:
    """Despacha el armado del detalle según el tipo de fila."""
    if isinstance(fila, FilaEdificio):
        return _edificio(fila, unidad, presion_aplicada)
    if isinstance(fila, FilaCartel):
        return _cartel(fila, unidad, unidad_fuerza)
    if isinstance(fila, FilaCubiertaAislada):
        return _cubierta_aislada(fila, unidad)
    if isinstance(fila, FilaComponentesCubiertaAislada):
        return _componentes_cubierta_aislada(fila, unidad)
    return "Zona sin detalle", []


def _presion(valor: float, unidad: Unidad) -> str:
    """El valor de una presión convertido, con su unidad."""
    return f"{convertir_unidad(valor, unidad):.2f} {unidad.value}/m²"


def _filas_q(q, unidad: Unidad) -> list[Fila]:
    """Las filas de la presión de velocidad: el valor y sus factores."""
    return [
        ["q", f"= {_presion(q.valor, unidad)}"],
        ["Kz", f"= {q.kz:.2f}"],
        ["Kzt", f"= {q.kzt:.2f}"],
        ["Ke", f"= {q.ke:.2f}"],
        ["z", f"= {q.altura:.2f} m"],
    ]


def _fila_referencia(referencia: str, distancia_a: float | None = None) -> Fila:
    """La fila de la referencia del Reglamento."""
    valor = referencia
    if distancia_a is not None:
        valor += f" · a = {distancia_a:.2f} m"
    return ["Ref", valor]


def _edificio(
    fila: FilaEdificio, unidad: Unidad, presion_aplicada: float | None
) -> tuple[str, list[Fila]]:
    """El detalle de una fila de edificio, SPRFV o componentes."""
    return _titulo_edificio(fila), _filas_edificio(fila, unidad, presion_aplicada)


def _titulo_edificio(fila: FilaEdificio) -> str:
    """El título que identifica la zona de la fila."""
    if fila.zona_parapeto is not None:
        caso = fila.pared.value.capitalize() if fila.pared else "sin pared"
        return f"Parapeto - Caso {caso} - {fila.zona_parapeto.value.capitalize()}"
    if fila.pared is not None:
        return f"Pared {fila.pared.value.capitalize()}"
    if fila.zona_componente is not None:
        if fila.zona_componente.name == "TODAS":
            titulo = "Todas las zonas"
        else:
            titulo = f"Zona {fila.zona_componente.value}"
        # El positivo suele ser único y viajar en la zona "todas". Cuando el
        # Reglamento lo distingue por zona (Fig. 5.3-2A, Nota 5, con parapeto),
        # la zona tiene dos filas y hay que decir cuál es cuál.
        if (
            fila.tipo_presion == TipoPresionComponentesParedesCubierta.POSITIVA
            and fila.zona_componente.name != "TODAS"
        ):
            titulo += " (positiva)"
        if fila.componente is not None:
            titulo = f"{fila.componente} - {titulo}"
        return titulo
    if fila.rango is not None:
        return f"Cubierta {fila.rango[0]:.2f} a {fila.rango[1]:.2f} m"
    titulo = fila.zona.value.capitalize()
    if fila.posicion is not None:
        titulo += f" {fila.posicion.value.capitalize()}"
    return titulo


def _filas_edificio(
    fila: FilaEdificio, unidad: Unidad, presion_aplicada: float | None
) -> list[Fila]:
    """El desglose del cálculo de una fila de edificio.

    Muestra las mismas columnas que la tabla del reporte: la presión de
    velocidad con sus factores, el coeficiente con el factor de ráfaga y la
    presión interna, y la presión final del signo que la vista está mostrando.
    """
    filas = _filas_q(fila.q, unidad)
    if fila.cp_frontal is not None:
        # El parapeto de componentes suma las dos caras (Art. 5.6): el
        # desglose del coeficiente combinado va en filas propias.
        filas += [
            ["GCp frontal", f"= {fila.cp_frontal:.2f}"],
            ["GCp posterior", f"= {fila.cp_posterior:.2f}"],
            ["GCp neto", f"= {fila.cp:.2f}"],
        ]
    else:
        simbolo = "GCp" if fila.sistema == SistemaResistente.COMPONENTES else "Cp"
        filas.append([simbolo, f"= {fila.cp:.2f}"])
    filas.append(["G", f"= {fila.factor_rafaga:.2f}"])
    if fila.con_presion_interna:
        presion = fila.pos if presion_aplicada is None else presion_aplicada
        # La escena asigna exactamente pos o neg según el signo de la presión
        # interna vigente: con eso sale el signo del GCpi que se está mostrando.
        gcpi = fila.gcpi if presion == fila.pos else -fila.gcpi
        filas.append(["GCpi", f"= {gcpi:+.2f}"])
        filas.append(["p", f"= {_presion(presion, unidad)}"])
    else:
        filas.append(["p", f"= {_presion(fila.pos, unidad)}"])
    filas.append(_fila_referencia(fila.referencia, fila.distancia_a))
    return filas


def _cartel(
    fila: FilaCartel, unidad: Unidad, unidad_fuerza: Unidad | None
) -> tuple[str, list[Fila]]:
    """El detalle de una fila de cartel."""
    unidad_fuerza = unidad_fuerza or Unidad.N
    titulo = f"Cartel - {fila.caso.value}"
    if fila.region is not None:
        titulo += f" - Región {fila.region.numero}"
    filas = [
        ["Cf", f"= {fila.cf:.2f}"],
        ["G", f"= {fila.factor_rafaga:.2f}"],
    ]
    if fila.excentricidad is not None:
        filas.append(["e", f"= {fila.excentricidad:.2f} m"])
    filas += _filas_q(fila.q, unidad)
    filas += [
        ["p", f"= {_presion(fila.presion, unidad)}"],
        ["Área", f"= {fila.area:.2f} m²"],
        [
            "F",
            f"= {convertir_unidad(fila.fuerza, unidad_fuerza):.2f} {unidad_fuerza.value}",
        ],
        _fila_referencia(fila.referencia),
    ]
    return titulo, filas


def _cubierta_aislada(
    fila: FilaCubiertaAislada, unidad: Unidad
) -> tuple[str, list[Fila]]:
    """El detalle de una fila de cubierta aislada."""
    titulo = fila.caso.value
    if fila.zona is not None:
        titulo += f" - {fila.zona.value}"
    filas = [
        ["Cpn", f"= {fila.cpn:.2f}"],
        ["G", f"= {fila.factor_rafaga:.2f}"],
        *_filas_q(fila.q, unidad),
        ["p", f"= {_presion(fila.presion, unidad)}"],
        ["p fricción", f"= {_presion(fila.presion_friccion, unidad)}"],
        _fila_referencia(fila.referencia),
    ]
    return titulo, filas


def _componentes_cubierta_aislada(
    fila: FilaComponentesCubiertaAislada, unidad: Unidad
) -> tuple[str, list[Fila]]:
    """El detalle de una fila de componentes de cubierta aislada."""
    titulo = f"{fila.componente} - Zona {fila.zona_componente.value}"
    titulo += f" ({fila.tipo_presion.value})"
    filas = [
        ["C_N", f"= {fila.cpn:.2f}"],
        ["G", f"= {fila.factor_rafaga:.2f}"],
        *_filas_q(fila.q, unidad),
        ["p", f"= {_presion(fila.presion, unidad)}"],
        _fila_referencia(fila.referencia, fila.distancia_a),
    ]
    return titulo, filas
