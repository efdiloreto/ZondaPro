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

"""Grupos de datos y de parámetros que comparten las tres tipologías.

Viento, ráfaga y topografía se arman una sola vez como bloques del modelo
de :mod:`zonda.widgets.reportes.documento`, y las páginas de edificio,
cartel y cubierta aislada los piden de acá, igual que hacen con el resto
de su contenido.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from zonda.cirsoc.factores import Rafaga
from zonda.enums import DireccionVientoMetodoDireccionalSprfv
from zonda.widgets.reportes import tablas
from zonda.widgets.reportes.documento import Bloque, Datos, Grupo, Nota, Titulo

if TYPE_CHECKING:
    from zonda.enums import Flexibilidad

RafagasTipo = Rafaga | dict[DireccionVientoMetodoDireccionalSprfv, Rafaga]


def _numero(valor: float) -> str:
    return tablas.numero(valor)


def grupo_viento(estructura) -> Grupo:
    """El grupo Viento de los datos de entrada.

    Args:
        estructura: La estructura calculada.

    Returns:
        El grupo armado.
    """
    filas: list[tuple[str, str]] = [
        ("Velocidad básica", f"{_numero(estructura.velocidad)} m/s"),
        ("Categoría de exposición", estructura.categoria_exp.value),
    ]
    if estructura.altitud:
        filas.append(
            ("Altitud sobre el nivel del mar", f"{_numero(estructura.altitud)} m")
        )
        filas.append(("Factor de altitud, Ke", f"{estructura.factor_altitud:.3f}"))
    else:
        filas.append(("Factor de altitud, Ke", _numero(estructura.factor_altitud)))

    return Grupo("Viento", [Datos(filas)])


def grupo_rafaga(
    estructura,
    texto_simplificado: str,
) -> Grupo:
    """El grupo Factor de ráfaga de los datos de entrada.

    Args:
        estructura: La estructura calculada.
        texto_simplificado: La frase que se muestra cuando se adopta el
            factor simplificado; cada tipología cita su artículo.

    Returns:
        El grupo armado.
    """
    if estructura.factor_g_simplificado:
        return Grupo(
            "Factor de Ráfaga", [Nota(texto_simplificado, "Factor simplificado")]
        )
    return Grupo(
        "Factor de Ráfaga",
        [
            Datos(
                (
                    ("Flexibilidad", estructura.flexibilidad.value.capitalize()),
                    ("Frecuencia natural", f"{_numero(estructura.frecuencia)} Hz"),
                    ("Relación de amortiguamiento", f"{_numero(estructura.beta)}"),
                )
            )
        ],
    )


def grupo_topografia(estructura) -> Grupo:
    """El grupo Topografía de los datos de entrada.

    Args:
        estructura: La estructura calculada.

    Returns:
        El grupo armado, con los parámetros si hay terreno cargado o con
        la aclaración de que no se consideró.
    """
    if not estructura.considerar_topografia:
        return Grupo("Topografía", [Datos([("Topografía", "No considerada")])])

    bloques: list[Bloque] = [
        Datos(
            (
                ("Tipo de terreno", estructura.tipo_terreno.value.capitalize()),
                ("Altura de terreno", f"{_numero(estructura.altura_terreno)} m"),
                ("Distancia a la cresta", f"{_numero(estructura.distancia_cresta)} m"),
                (
                    f"Distancia a {estructura.direccion.value}",
                    f"{_numero(estructura.distancia_barlovento_sotavento)} m",
                ),
            )
        )
    ]
    if not estructura.topografia.topografia_considerada():
        bloques.append(
            Nota(
                "No se considera la topografía debido a que no se cumplen "
                "todas las condiciones del artículo 1.8.1."
            )
        )
    return Grupo("Topografía", bloques)


def grupo_constantes_terreno(rafaga: Rafaga) -> Grupo:
    """El grupo con las constantes de exposición del terreno.

    Args:
        rafaga: Una ráfaga, de donde salen las constantes.

    Returns:
        El grupo armado.
    """
    return Grupo(
        "Constantes de exposición del terreno",
        [tablas.tabla_constantes_terreno(rafaga.constantes_exp_terreno)],
        referencia="Tabla 1.6-1",
    )


def grupo_factor_rafaga(
    rafagas: RafagasTipo,
    flexibilidad: Flexibilidad,
    texto_simplificado: str,
) -> Grupo:
    """El grupo con el factor de ráfaga calculado.

    Con el factor simplificado muestra el valor 0,85; si se calcula,
    muestra los parámetros de cada dirección de viento, tal como el PDF
    arma una tabla por dirección para el edificio.

    Args:
        rafagas: Una ráfaga, o el diccionario por dirección del edificio.
        flexibilidad: La flexibilidad de la estructura.
        texto_simplificado: Qué artículo respalda el valor 0,85.

    Returns:
        El grupo armado.
    """
    if isinstance(rafagas, dict):
        if not any(rafaga.factor_g_simplificado for rafaga in rafagas.values()):
            bloques: list[Bloque] = []
            for direccion, rafaga in rafagas.items():
                bloques.append(Titulo(f"{direccion.value.capitalize()} a la cumbrera"))
                bloques.append(tablas.tabla_rafaga(rafaga, flexibilidad))
            return Grupo("Factor de Ráfaga", bloques)
        return Grupo(
            "Factor de Ráfaga",
            [
                Datos([("Factor de ráfaga", "0.85")]),
                Nota(texto_simplificado),
            ],
        )

    if rafagas.factor_g_simplificado:
        return Grupo(
            "Factor de Ráfaga",
            [
                Datos([("Factor de ráfaga", "0.85")]),
                Nota(texto_simplificado),
            ],
        )
    return Grupo("Factor de Ráfaga", [tablas.tabla_rafaga(rafagas, flexibilidad)])


def grupo_factor_topografico(estructura, k3: float, notas_altura: list[str]) -> Grupo:
    """El grupo con el factor topográfico.

    Args:
        estructura: La estructura calculada.
        k3: El factor K3 a la altura de referencia de la tipología.
        notas_altura: Las notas que aclaran a qué altura corresponde el
            K3 mostrado.

    Returns:
        El grupo armado.
    """
    if estructura.topografia.topografia_considerada():
        return Grupo(
            "Factor Topográfico",
            [
                tablas.tabla_topografia(estructura.topografia, k3),
                *[Nota(texto) for texto in notas_altura],
                Nota("Los valores de Kzt se encuentran en las tablas de presiones."),
            ],
            referencia="Figura 1.8-1",
        )

    bloques: list[Bloque] = [Datos([("Factor topográfico, Kzt", "1.00")])]
    if estructura.considerar_topografia:
        bloques.append(
            Nota(
                "No se considera la topografía debido a que no se cumplen "
                "todas las condiciones del artículo 1.8.1."
            )
        )
    return Grupo("Factor Topográfico", bloques, referencia="Figura 1.8-1")
