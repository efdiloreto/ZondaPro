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

"""La página de reporte del edificio.

Arma las secciones que la plantilla ``edificio.md`` exporta: el resumen
con los valores clave, los datos de entrada, los parámetros de cálculo,
las presiones del SPRFV por dirección de viento y las de componentes y
revestimientos. Todo se lee de ``estructura.resultados_sprfv`` y
``estructura.resultados_componentes`` filtrando y agrupando la tabla
plana, igual que hace la plantilla con ``filtrar(...).agrupar(...)``.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from PyQt6 import QtWidgets

from zonda.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    TipoCubierta,
    Unidad,
    ZonaEdificio,
)
from zonda.excepciones import ErrorLineamientos
from zonda.unidades import convertir_unidad
from zonda.widgets.reportes import tablas
from zonda.widgets.reportes.comunes import (
    pagina,
    seccion_rafaga,
    seccion_topografia,
    seccion_viento,
    subseccion_constantes_terreno,
    subseccion_factor_rafaga,
    subseccion_factor_topografico,
)
from zonda.widgets.reportes.navegacion import VistaReporte
from zonda.widgets.reportes.secciones import (
    Nota,
    Seccion,
    Subseccion,
    TablaDatos,
    Tarjeta,
    fila_tarjetas,
    unidades_desde_settings,
)

if TYPE_CHECKING:
    from zonda.cirsoc import Edificio
    from zonda.cirsoc.resultados import FilaEdificio

TEXTO_RAFAGA_SIMPLIFICADA = (
    "Se adopta el factor de ráfaga igual a 0.85 de acuerdo al artículo 5.8.1."
)
NOTA_MINIMAS_SPRFV = (
    "La carga de viento que se debe usar en el diseño del SPRFV para un "
    "edificio cerrado o parcialmente cerrado, no debe ser menor que 0,75 "
    "kN/m² multiplicado por el área de la pared del edificio proyectada "
    "sobre un plano vertical normal a la dirección supuesta del viento, y "
    "0,4 kN/m² multiplicado por el área de la cubierta proyectada sobre un "
    "plano horizontal. Las cargas de paredes y cubiertas se deben aplicar "
    "simultáneamente. La fuerza del viento de diseño para edificios "
    "abiertos no debe ser menor que 0,75 kN/m² multiplicado por el área Af."
)
NOTA_MINIMAS_COMPONENTES = (
    "La presión de viento de diseño para componentes y revestimientos de "
    "edificios y otras estructuras no debe ser menor que una presión neta "
    "de 0,80 kN/m² actuando en cualquier dirección normal a la superficie. "
    "Los valores de las tablas ya la tienen aplicada."
)
NOTA_PARAPETO_SPRFV = (
    "La presión neta combinada del parapeto (Art. 2.4.5) no depende de la "
    "dirección del viento: el coeficiente GCpn de +1,5 corresponde al "
    "parapeto a barlovento y el de −1,0 al de sotavento, en cada dirección "
    "considerada. El signo positivo empuja hacia el lado frontal (exterior) "
    "del parapeto y el negativo se aleja de él."
)
NOTA_PARAPETO_COMPONENTES = (
    "La presión del parapeto (Art. 5.6) es la combinación de las presiones "
    "externas de sus dos caras: en el Caso de carga A (parapeto a "
    "barlovento) la cara posterior toma la presión negativa de la Zona de "
    "borde o esquina de cubierta, y en el Caso de carga B (parapeto a "
    "sotavento), la de la Zona de pared. El coeficiente interno es el de "
    "la envolvente no porosa del parapeto."
)
NOTA_K3 = (
    "El valor de K3 que se muestra en la tabla es el correspondiente a la "
    "altura media. Los valores para las demás alturas se calculan "
    "automáticamente y no son mostrados."
)


def vista(edificio: Edificio) -> VistaReporte:
    """Arma la vista de reporte del edificio.

    Args:
        edificio: El edificio calculado.

    Returns:
        La vista con sus páginas.
    """
    unidades = unidades_desde_settings()
    paginas: list[tuple[str, QtWidgets.QWidget]] = [
        ("Resumen", _pagina_resumen(edificio, unidades)),
        ("Datos de entrada", _pagina_datos(edificio)),
        ("Parámetros de cálculo", _pagina_parametros(edificio)),
        ("Presiones - SPRFV", _pagina_sprfv(edificio, unidades)),
    ]
    pagina_componentes = None
    with contextlib.suppress(ErrorLineamientos):
        # Sin lineamientos para componentes, el reporte del SPRFV sigue
        # siendo válido y la página simplemente no aparece.
        pagina_componentes = _pagina_componentes(edificio, unidades)
    if pagina_componentes is not None:
        # En el índice la página va con el nombre corto que usan las
        # pestañas del panel; la sección de adentro lleva el completo.
        paginas.append(("Componentes (C&R)", pagina_componentes))
    return VistaReporte(
        edificio, "edificio.md", "PRESIONES DE VIENTO — EDIFICIO", paginas
    )


def _ubicacion(fila: FilaEdificio) -> str:
    """Describe dónde se produce la presión de una fila.

    Args:
        fila: La fila de resultado.

    Returns:
        El texto con la superficie, el caso y la dirección del viento.
    """
    partes: list[str] = []
    if fila.componente:
        partes.append(f"Componente {fila.componente}")
        if fila.zona_componente and fila.zona_componente.name != "TODAS":
            partes.append(f"zona {fila.zona_componente.value}")
    elif fila.zona == ZonaEdificio.PAREDES:
        partes.append(f"Pared {fila.pared.value}" if fila.pared else "Paredes")
    elif fila.zona == ZonaEdificio.CUBIERTA:
        partes.append("Cubierta")
    elif fila.zona == ZonaEdificio.ALERO:
        partes.append("Alero")
    elif fila.zona == ZonaEdificio.PARAPETO:
        partes.append("Parapeto")
    if fila.pared is not None and fila.zona == ZonaEdificio.PARAPETO:
        partes.append(fila.pared.value)
    if fila.posicion is not None and not fila.componente:
        partes.append(fila.posicion.value)
    if fila.caso is not None:
        partes.append(fila.caso.value)
    if fila.direccion is not None and not fila.componente:
        partes.append(f"viento {fila.direccion.value}")
    return ", ".join(partes)


def _unidad_presion(unidades: dict[str, Unidad]) -> str:
    return f"{unidades['presion'].value}/m²"


def _tarjetas_extremos(
    edificio: Edificio, unidades: dict[str, Unidad]
) -> list[Tarjeta]:
    """Las tarjetas de los valores extremos del SPRFV.

    Args:
        edificio: El edificio calculado.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        Las tarjetas que correspondan: la de máxima presión sólo si hay
        empuje en alguna superficie, y la de máxima succión sólo si hay
        succión.
    """
    unidad = _unidad_presion(unidades)
    minimo, maximo = edificio.resultados_sprfv.min_max()
    tarjetas: list[Tarjeta] = []
    if maximo > 0:
        fila_max = next(
            fila for fila in edificio.resultados_sprfv if maximo in fila.presiones
        )
        tarjetas.append(
            Tarjeta(
                "Máxima presión",
                f"{convertir_unidad(maximo, unidades['presion']):+.2f} {unidad}",
                detalle=_ubicacion(fila_max),
                destacada=True,
            )
        )
    if minimo < 0:
        fila_min = next(
            fila for fila in edificio.resultados_sprfv if minimo in fila.presiones
        )
        tarjetas.append(
            Tarjeta(
                "Máxima succión",
                f"{convertir_unidad(minimo, unidades['presion']):+.2f} {unidad}",
                detalle=_ubicacion(fila_min),
                destacada=True,
            )
        )
    return tarjetas


def _pagina_resumen(
    edificio: Edificio, unidades: dict[str, Unidad]
) -> QtWidgets.QWidget:
    """La página con los valores que gobiernan el diseño.

    Args:
        edificio: El edificio calculado.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La página armada.
    """
    sprfv = edificio.presiones.cubierta.sprfv
    kzt = (
        max(edificio.topografia.factor)
        if edificio.topografia.topografia_considerada()
        else 1.0
    )
    seccion = Seccion("Resumen")
    seccion.agregar(
        fila_tarjetas(
            Tarjeta("Velocidad básica", f"{edificio.velocidad:.2f} m/s"),
            Tarjeta("Coeficiente de presión interna", f"±{sprfv.gcpi:.2f}"),
            Tarjeta(
                "Factor topográfico, Kzt",
                f"{kzt:.2f}",
                detalle="máximo entre las alturas" if kzt != 1.0 else None,
            ),
        )
    )
    tarjetas_extremos = _tarjetas_extremos(edificio, unidades)
    if tarjetas_extremos:
        seccion.agregar(fila_tarjetas(*tarjetas_extremos))
    seccion.agregar_estiramiento()
    return pagina(seccion)


def _pagina_datos(edificio: Edificio) -> QtWidgets.QWidget:
    """La página con el reglamento y los datos de entrada.

    Args:
        edificio: El edificio calculado.

    Returns:
        La página armada.
    """
    seccion_reglamento = Seccion("Reglamento")
    seccion_reglamento.agregar(
        TablaDatos(
            (
                (
                    "Método de cálculo",
                    "Método 2 (Analítico) - Procedimiento "
                    f"{edificio.metodo_sprfv.value.capitalize()}",
                ),
            )
        )
    )

    filas: list[tuple[str, str]] = [
        ("Elevación sobre terreno", f"{edificio.elevacion:.2f} m"),
        ("Ancho", f"{edificio.ancho:.2f} m"),
        ("Longitud", f"{edificio.longitud:.2f} m"),
        ("Altura de alero", f"{edificio.altura_alero:.2f} m"),
    ]
    if edificio.tipo_cubierta != TipoCubierta.PLANA:
        filas.append(("Altura de cumbrera", f"{edificio.altura_cumbrera:.2f} m"))
    if edificio.alero:
        filas.append(("Alero", f"{edificio.alero:.2f} m"))
    if edificio.parapeto:
        filas.append(("Parapeto", f"{edificio.parapeto:.2f} m"))
    filas += [
        ("Tipo de cubierta", edificio.geometria.tipo_cubierta.value.capitalize()),
        ("Clasificación de cerramiento", edificio.cerramiento.value.capitalize()),
    ]
    seccion_edificio = Seccion("Edificio")
    seccion_edificio.agregar(TablaDatos(filas))

    return pagina(
        seccion_reglamento,
        seccion_edificio,
        seccion_viento(edificio),
        seccion_rafaga(edificio, TEXTO_RAFAGA_SIMPLIFICADA),
        seccion_topografia(edificio),
    )


def _pagina_parametros(edificio: Edificio) -> QtWidgets.QWidget:
    """La página con los parámetros intermedios del cálculo.

    Args:
        edificio: El edificio calculado.

    Returns:
        La página armada.
    """
    sprfv = edificio.presiones.cubierta.sprfv
    filas: list[tuple[str, str]] = [
        ("Ángulo de cubierta", f"{edificio.geometria.cubierta.angulo:.2f}°"),
        (
            "Altura media de cubierta",
            f"{edificio.geometria.cubierta.altura_media:.2f} m",
        ),
    ]
    if edificio.reducir_gcpi:
        filas.append(
            (
                "Factor de reducción de GCpi",
                f"{sprfv.factor_reduccion_gcpi:.2f}",
            )
        )
    filas += [
        ("Coeficiente de presión interna, GCpi", f"±{sprfv.gcpi:.2f}"),
        ("Factor de direccionalidad, Kd", f"{sprfv.factor_direccionalidad:.2f}"),
    ]
    subseccion_cubierta = Subseccion("Cubierta")
    subseccion_cubierta.agregar(TablaDatos(filas))

    seccion = Seccion("Parámetros de cálculo")
    seccion.agregar(subseccion_cubierta)
    seccion.agregar(
        subseccion_constantes_terreno(
            edificio.rafaga[DireccionVientoMetodoDireccionalSprfv.PARALELO]
        )
    )
    seccion.agregar(
        subseccion_factor_rafaga(
            edificio.rafaga, edificio.flexibilidad, TEXTO_RAFAGA_SIMPLIFICADA
        )
    )
    seccion.agregar(
        subseccion_factor_topografico(
            edificio,
            edificio.topografia.k3_en(edificio.geometria.cubierta.altura_media),
            [NOTA_K3],
        )
    )
    seccion.agregar_estiramiento()
    return pagina(seccion)


def _titulo_superficie(base: str, clave: tuple, sin_posicion: str | None = None) -> str:
    """El título de una superficie de cubierta o alero.

    Es el port del macro ``titulo_superficie``: cuando la superficie no
    está dividida por posición, igualmente nombra el caso de presión si la
    fila lo trae (el caso positivo del nuevo Reglamento con ángulo < 10°).

    Args:
        base: El nombre de la superficie ("Cubierta", "Alero").
        clave: El par posición, caso con el que se agruparon las filas.
        sin_posicion: El rótulo a usar cuando no hay posición.

    Returns:
        El título armado.
    """
    posicion, caso = clave
    if posicion is None:
        titulo = sin_posicion or base
    else:
        titulo = f"{base} {posicion.value.capitalize()}"
    if caso:
        titulo = f"{titulo} - {caso.value.capitalize()}"
    return titulo


def _secciones_direccion(
    edificio: Edificio,
    direccion: DireccionVientoMetodoDireccionalSprfv,
    unidades: dict[str, Unidad],
) -> QtWidgets.QWidget:
    """Las subsecciones de presiones de una dirección de viento.

    Args:
        edificio: El edificio calculado.
        direccion: La dirección del viento.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        El widget con las subsecciones de paredes, cubierta y alero.
    """
    filas_direccion = edificio.resultados_sprfv.filtrar(direccion=direccion)
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    # El margen separa las tarjetas del pane de la pestaña, que es el borde
    # que dibuja el QTabWidget a su alrededor.
    layout.setContentsMargins(9, 9, 9, 9)
    layout.setSpacing(12)

    for pared, filas in filas_direccion.filtrar(zona=ZonaEdificio.PAREDES).agrupar(
        "pared"
    ):
        subseccion = Subseccion(
            f"Pared {pared.value.capitalize()}" if pared else "Paredes",
            referencia=filas[0].referencia,
        )
        subseccion.agregar(tablas.tabla_presiones(filas, unidades))
        layout.addWidget(subseccion)

    for clave, filas in filas_direccion.filtrar(zona=ZonaEdificio.CUBIERTA).agrupar(
        "posicion", "caso"
    ):
        subseccion = Subseccion(
            _titulo_superficie("Cubierta", clave), referencia=filas[0].referencia
        )
        subseccion.agregar(tablas.tabla_presiones(filas, unidades))
        layout.addWidget(subseccion)

    for clave, filas in filas_direccion.filtrar(zona=ZonaEdificio.ALERO).agrupar(
        "posicion", "caso"
    ):
        subseccion = Subseccion(
            _titulo_superficie("Alero", clave, "Aleros"),
            referencia=filas[0].referencia,
        )
        subseccion.agregar(tablas.tabla_presiones(filas, unidades))
        layout.addWidget(subseccion)

    layout.addStretch(1)
    return widget


def _pagina_sprfv(edificio: Edificio, unidades: dict[str, Unidad]) -> QtWidgets.QWidget:
    """La página con las presiones del SPRFV.

    Args:
        edificio: El edificio calculado.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La página armada, con una pestaña por dirección de viento, el
        parapeto cuando lo hay y las notas del Reglamento.
    """
    seccion = Seccion("Presiones - SPRFV")

    pestañas = QtWidgets.QTabWidget()
    for direccion in DireccionVientoMetodoDireccionalSprfv:
        pestañas.addTab(
            _secciones_direccion(edificio, direccion, unidades),
            f"{direccion.value.capitalize()} a la cumbrera",
        )
    seccion.agregar(pestañas)

    parapeto = edificio.resultados_sprfv.filtrar(zona=ZonaEdificio.PARAPETO)
    if parapeto:
        subseccion = Subseccion("Parapeto", referencia=parapeto[0].referencia)
        subseccion.agregar(tablas.tabla_parapeto_sprfv(parapeto, unidades))
        subseccion.agregar(Nota(NOTA_PARAPETO_SPRFV, "Parapeto (Art. 2.4.5)"))
        seccion.agregar(subseccion)

    seccion.agregar(
        Nota(NOTA_MINIMAS_SPRFV, "Cargas de viento de diseño mínimas (Art. 2.1.5)")
    )
    seccion.agregar_estiramiento()
    return pagina(seccion)


def _pagina_componentes(
    edificio: Edificio, unidades: dict[str, Unidad]
) -> QtWidgets.QWidget | None:
    """La página con las presiones de componentes y revestimientos.

    Args:
        edificio: El edificio calculado.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La página armada, o ``None`` cuando el edificio no tiene
        componentes cargados.

    Raises:
        ErrorLineamientos: Cuando el Reglamento no da lineamientos para
            la geometría del edificio.
    """
    componentes = edificio.resultados_componentes
    if not componentes:
        return None

    seccion = Seccion("Componentes y Revestimientos")
    for zona, filas_zona in componentes.agrupar("zona"):
        if zona == ZonaEdificio.PARAPETO:
            subseccion = Subseccion(
                f"Parapeto (área efectiva: {edificio.area_parapeto:g} m²)",
                referencia=filas_zona[0].referencia,
            )
            subseccion.agregar(tablas.tabla_parapeto_componentes(filas_zona, unidades))
            subseccion.agregar(Nota(NOTA_PARAPETO_COMPONENTES, "Parapeto (Art. 5.6)"))
            seccion.agregar(subseccion)
            continue

        areas = (
            edificio.componentes_paredes
            if zona == ZonaEdificio.PAREDES
            else edificio.componentes_cubierta
        ) or {}
        for clave, filas in filas_zona.agrupar("pared", "componente"):
            pared, nombre = clave
            titulo_pared = f"Pared {pared.value.capitalize()} — " if pared else ""
            por_altura = len({fila.q.altura for fila in filas}) > 1
            if por_altura:
                # Con la Figura 5.4-1 (h > 20 m) las paredes se evalúan a
                # cada altura y el Reglamento distingue zonas de área
                # efectiva: la tabla se parte por zona.
                for zona_componente, filas_zona_componente in filas.agrupar(
                    "zona_componente"
                ):
                    subseccion = Subseccion(
                        f"{titulo_pared}Componente: {nombre} "
                        f"({areas[nombre]:g} m²) "
                        f"(Zona: {zona_componente.value.capitalize()})",
                        referencia=filas_zona_componente[0].referencia,
                    )
                    subseccion.agregar(
                        tablas.tabla_presiones(filas_zona_componente, unidades)
                    )
                    seccion.agregar(subseccion)
            else:
                subseccion = Subseccion(
                    f"{titulo_pared}Componente: {nombre} ({areas[nombre]:g} m²)",
                    referencia=filas[0].referencia,
                )
                subseccion.agregar(tablas.tabla_presiones(filas, unidades))
                seccion.agregar(subseccion)

    seccion.agregar(
        Nota(
            NOTA_MINIMAS_COMPONENTES,
            "Presiones de viento de diseño mínimas (Art. 5.2.2)",
        )
    )
    seccion.agregar_estiramiento()
    return pagina(seccion)
