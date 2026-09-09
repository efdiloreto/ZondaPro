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

"""Secciones de datos y de parámetros que comparten las tres tipologías.

El reporte exportado arma estos bloques en ``base.md`` y las plantillas de
cada tipología los reutilizan con ``super()``; acá ocurre lo mismo: viento,
ráfaga y topografía se arman una sola vez y las páginas de edificio, cartel
y cubierta aislada los piden de acá.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6 import QtWidgets

from zonda.cirsoc.factores import Rafaga
from zonda.enums import DireccionVientoMetodoDireccionalSprfv
from zonda.widgets.custom import crear_capsula, crear_segmento
from zonda.widgets.reportes import tablas
from zonda.widgets.reportes.secciones import Nota, Seccion, Subseccion, TablaDatos

if TYPE_CHECKING:
    from zonda.enums import Flexibilidad

RafagasTipo = Rafaga | dict[DireccionVientoMetodoDireccionalSprfv, Rafaga]

# El ancho que comparten el desplegable y la cápsula de superficies del
# selector de componentes.
ANCHO_SELECTOR = 260


def apilador_componentes(
    superficies: list[tuple[str, list[str], list[QtWidgets.QWidget]]],
) -> QtWidgets.QWidget:
    """El selector de componentes de la página de C&R.

    Muestra de a un componente por vez: una cápsula segmentada elige la
    superficie cuando hay más de una —pared o cubierta en el edificio— y
    un desplegable elige el componente; el contenido de cada uno va en un
    apilador. Cuando sólo hay una superficie la cápsula no aparece y si
    además no tiene componentes —un parapeto solo— la fila de selectores
    se omite.

    Args:
        superficies: Por cada superficie, su etiqueta, los nombres de sus
            componentes y la página de cada uno, en el mismo orden.

    Returns:
        El widget con los selectores y el apilador de contenido.
    """
    apilador = QtWidgets.QStackedWidget()
    arranques: list[int] = []
    for _, _, páginas in superficies:
        arranques.append(apilador.count())
        for página in páginas:
            apilador.addWidget(página)

    combo = QtWidgets.QComboBox()
    combo.setProperty("class", "selector-componente")
    combo.setMinimumWidth(ANCHO_SELECTOR)

    fila_selectores = QtWidgets.QWidget()
    layout_selectores = QtWidgets.QHBoxLayout(fila_selectores)
    layout_selectores.setContentsMargins(0, 0, 0, 0)
    layout_selectores.setSpacing(9)

    grupo: QtWidgets.QButtonGroup | None = None
    if len(superficies) > 1:
        grupo = QtWidgets.QButtonGroup(fila_selectores)
        grupo.setExclusive(True)
        segmentos = []
        for indice, (etiqueta, _, _) in enumerate(superficies):
            segmento = crear_segmento(etiqueta)
            # Más bajo que los del panel: acá es un selector de página,
            # no la barra principal.
            segmento.setProperty("compacto", True)
            segmento.setChecked(indice == 0)
            grupo.addButton(segmento, indice)
            segmentos.append(segmento)
        # La cápsula entera mide lo mismo que el desplegable: los
        # segmentos reparten el ancho, con la letra baja del QSS.
        ancho_segmento = (ANCHO_SELECTOR - 3 * (len(segmentos) - 1)) // len(segmentos)
        for segmento in segmentos:
            segmento.setFixedWidth(ancho_segmento)
        layout_selectores.addWidget(crear_capsula(*segmentos))
    layout_selectores.addWidget(combo)
    layout_selectores.addStretch(1)

    estado = {"superficie": 0}

    def _mostrar_superficie(indice: int) -> None:
        """Conmuta la superficie: repuebla el desplegable con sus
        componentes y muestra el primero."""
        estado["superficie"] = indice
        nombres = superficies[indice][1]
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(nombres)
        combo.blockSignals(False)
        combo.setVisible(bool(nombres))
        apilador.setCurrentIndex(arranques[indice])

    def _mostrar_componente(indice: int) -> None:
        """Muestra la página del componente elegido de la superficie."""
        apilador.setCurrentIndex(arranques[estado["superficie"]] + indice)

    if grupo is not None:
        grupo.idClicked.connect(_mostrar_superficie)
    combo.currentIndexChanged.connect(_mostrar_componente)
    _mostrar_superficie(0)

    contenedor = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(9)
    if grupo is not None or any(nombres for _, nombres, _ in superficies):
        layout.addWidget(fila_selectores)
    layout.addWidget(apilador)
    return contenedor


def _numero(valor: float) -> str:
    return tablas.numero(valor)


def pagina(*secciones: QtWidgets.QWidget) -> QtWidgets.QWidget:
    """Apila secciones en una página del reporte.

    Args:
        *secciones: Las secciones de la página, en orden de lectura.

    Returns:
        El widget de la página.
    """
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(18)
    for seccion in secciones:
        layout.addWidget(seccion)
    layout.addStretch(1)
    return widget


def seccion_viento(estructura) -> Seccion:
    """La sección Viento de los datos de entrada.

    Args:
        estructura: La estructura calculada.

    Returns:
        La sección armada.
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

    seccion = Seccion("Viento")
    seccion.agregar(TablaDatos(filas))
    return seccion


def seccion_rafaga(
    estructura,
    texto_simplificado: str,
) -> Seccion:
    """La sección Factor de ráfaga de los datos de entrada.

    Args:
        estructura: La estructura calculada.
        texto_simplificado: La frase que se muestra cuando se adopta el
            factor simplificado; cada tipología cita su artículo.

    Returns:
        La sección armada.
    """
    seccion = Seccion("Factor de Ráfaga")
    if estructura.factor_g_simplificado:
        seccion.agregar(Nota(texto_simplificado, "Factor simplificado"))
        return seccion
    seccion.agregar(
        TablaDatos(
            (
                ("Flexibilidad", estructura.flexibilidad.value.capitalize()),
                ("Frecuencia natural", f"{_numero(estructura.frecuencia)} Hz"),
                ("Relación de amortiguamiento", f"{_numero(estructura.beta)}"),
            )
        )
    )
    return seccion


def seccion_topografia(estructura) -> Seccion:
    """La sección Topografía de los datos de entrada.

    Args:
        estructura: La estructura calculada.

    Returns:
        La sección armada, con los parámetros si hay terreno cargado o con
        la aclaración de que no se consideró.
    """
    seccion = Seccion("Topografía")
    if not estructura.considerar_topografia:
        seccion.agregar(TablaDatos([("Topografía", "No considerada")]))
        return seccion

    seccion.agregar(
        TablaDatos(
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
    )
    if not estructura.topografia.topografia_considerada():
        seccion.agregar(
            Nota(
                "No se considera la topografía debido a que no se cumplen "
                "todas las condiciones del artículo 1.8.1.",
            )
        )
    return seccion


def subseccion_constantes_terreno(rafaga: Rafaga) -> Subseccion:
    """La subsección con las constantes de exposición del terreno.

    Args:
        rafaga: Una ráfaga, de donde salen las constantes.

    Returns:
        La subsección armada.
    """
    subseccion = Subseccion(
        "Constantes de exposición del terreno", referencia="Tabla 1.6-1"
    )
    subseccion.agregar(tablas.tabla_constantes_terreno(rafaga.constantes_exp_terreno))
    return subseccion


def subseccion_factor_rafaga(
    rafagas: RafagasTipo,
    flexibilidad: Flexibilidad,
    texto_simplificado: str,
) -> Subseccion:
    """La subsección con el factor de ráfaga calculado.

    Con el factor simplificado muestra el valor 0,85; si se calcula,
    muestra los parámetros de cada dirección de viento, tal como la
    exportación arma una tabla por dirección para el edificio.

    Args:
        rafagas: Una ráfaga, o el diccionario por dirección del edificio.
        flexibilidad: La flexibilidad de la estructura.
        texto_simplificado: Qué artículo respalda el valor 0,85.

    Returns:
        La subsección armada.
    """
    subseccion = Subseccion("Factor de Ráfaga")
    if isinstance(rafagas, dict):
        if not any(rafaga.factor_g_simplificado for rafaga in rafagas.values()):
            for direccion, rafaga in rafagas.items():
                etiqueta = QtWidgets.QLabel(
                    f"{direccion.value.capitalize()} a la cumbrera"
                )
                etiqueta.setProperty("class", "grupo-tabla")
                subseccion.agregar(etiqueta)
                subseccion.agregar(tablas.tabla_rafaga(rafaga, flexibilidad))
            return subseccion
        subseccion.agregar(
            TablaDatos([("Factor de ráfaga", "0.85")]),
        )
        subseccion.agregar(Nota(texto_simplificado))
        return subseccion

    if rafagas.factor_g_simplificado:
        subseccion.agregar(TablaDatos([("Factor de ráfaga", "0.85")]))
        subseccion.agregar(Nota(texto_simplificado))
        return subseccion
    subseccion.agregar(tablas.tabla_rafaga(rafagas, flexibilidad))
    return subseccion


def subseccion_factor_topografico(
    estructura, k3: float, notas_altura: list[str]
) -> Subseccion:
    """La subsección con el factor topográfico.

    Args:
        estructura: La estructura calculada.
        k3: El factor K3 a la altura de referencia de la tipología.
        notas_altura: Las notas que aclaran a qué altura corresponde el
            K3 mostrado.

    Returns:
        La subsección armada.
    """
    subseccion = Subseccion("Factor Topográfico", referencia="Figura 1.8-1")
    if estructura.topografia.topografia_considerada():
        subseccion.agregar(tablas.tabla_topografia(estructura.topografia, k3))
        for texto in notas_altura:
            subseccion.agregar(Nota(texto))
        subseccion.agregar(
            Nota("Los valores de Kzt se encuentran en las tablas de presiones.")
        )
        return subseccion
    subseccion.agregar(TablaDatos([("Factor topográfico, Kzt", "1.00")]))
    if estructura.considerar_topografia:
        subseccion.agregar(
            Nota(
                "No se considera la topografía debido a que no se cumplen "
                "todas las condiciones del artículo 1.8.1.",
            )
        )
    return subseccion
