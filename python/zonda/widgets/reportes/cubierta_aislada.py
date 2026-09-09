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

"""La página de reporte de la cubierta aislada.

Arma las secciones que la plantilla ``cubierta-aislada.md`` exporta: el
resumen, los datos de entrada, los parámetros de cálculo, las presiones
normales por dirección del viento, las presiones laterales de cenefas,
parapetos y tímpanos con las fuerzas de fricción, y los componentes y
revestimientos de las Figuras 5.5-1 a 5.5-3.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from PyQt6 import QtWidgets

from zonda.enums import DireccionVientoCubiertaAislada, Unidad
from zonda.excepciones import ErrorLineamientos
from zonda.unidades import convertir_unidad
from zonda.widgets.reportes import tablas
from zonda.widgets.reportes.comunes import (
    apilador_componentes,
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
    from zonda.cirsoc import CubiertaAislada
    from zonda.cirsoc.resultados import (
        FilaComponentesCubiertaAislada,
        FilaCubiertaAislada,
        Tabla,
    )

TEXTO_RAFAGA_SIMPLIFICADA = (
    "Se adopta el factor de efecto de ráfaga simplificado G = 0.85, según "
    "el artículo 1.9.4."
)
NOTA_MINIMAS_SPRFV = (
    "La fuerza de viento de diseño para edificios abiertos, como la "
    "cubierta aislada, no debe ser menor que 0,75 kN/m² multiplicada por "
    "el área proyectada Af."
)
NOTA_MINIMAS_COMPONENTES = (
    "La presión de viento de diseño para componentes y revestimientos de "
    "edificios y otras estructuras no debe ser menor que una presión neta "
    "de 0,80 kN/m² actuando en cualquier dirección normal a la superficie. "
    "Los valores de las tablas ya la tienen aplicada."
)
DESCRIPCION_NORMALES = (
    "Se deben investigar todos los casos de carga para cada ángulo de "
    "cubierta. Las fuerzas de fricción, incluidas en las tablas, se "
    "calculan sobre la superficie superior e inferior con flujo de viento "
    "libre, o sólo sobre la superior con flujo obstruido, y se combinan "
    "con las fuerzas debidas a la presión normal (art. 2.4.3.1)."
)
DESCRIPCION_CENEFAS = (
    "Según el artículo 2.4.5 se debe agregar la carga horizontal resultante "
    "de considerar las cenefas, parapetos o tímpanos con qp = qh (art. "
    "2.4.3.1), en caso de existir. Los coeficientes GCpn ya incluyen el "
    "factor de ráfaga: el signo positivo empuja hacia el lado frontal del "
    "parapeto y el negativo se aleja de él."
)
DESCRIPCION_FRICCION = (
    "Según el artículo 2.4.3.1, para viento paralelo a la cumbrera se debe "
    "agregar la mayor entre la carga de las cenefas, parapetos o tímpanos "
    "y la fuerza de fricción, calculada con los coeficientes de empuje por "
    "fricción de la Tabla 2.4-1 que correspondan al tipo de superficie "
    "según su orientación respecto de la dirección del viento."
)
DESCRIPCION_COMPONENTES = (
    "Los coeficientes de presión neta CN salen de la figura indicada en "
    "cada tabla, para edificios abiertos, según el área efectiva de viento "
    "de cada componente y la situación de bloqueo del flujo bajo la "
    "cubierta. La presión de cada zona es p = qh · G · CN (expresión "
    "5.5-1), con qh calculada a la altura media de la cubierta. Los "
    "coeficientes son presiones netas (contribuciones de las superficies "
    "superior e inferior) y no llevan presión interna. Los signos positivo "
    "y negativo indican presiones que actúan acercándose o alejándose de "
    "la superficie superior de la cubierta, respectivamente (nota 4), y "
    "para ángulos distintos de los tabulados se permite la interpolación "
    "lineal (nota 3). Las figuras cubren 0,25 ≤ h/L ≤ 1,0, con L medido a "
    "lo largo de la dirección del viento, normal a la cumbrera o a lo "
    "largo de la vertiente."
)


def vista(cubierta_aislada: CubiertaAislada) -> VistaReporte:
    """Arma la vista de reporte de la cubierta aislada.

    Args:
        cubierta_aislada: La cubierta aislada calculada.

    Returns:
        La vista con sus páginas.
    """
    unidades = unidades_desde_settings()
    paginas: list[tuple[str, QtWidgets.QWidget]] = [
        ("Resumen", _pagina_resumen(cubierta_aislada, unidades)),
        ("Datos de entrada", _pagina_datos(cubierta_aislada)),
        ("Parámetros de cálculo", _pagina_parametros(cubierta_aislada)),
        ("Presiones normales", _pagina_normales(cubierta_aislada, unidades)),
        ("Presiones laterales", _pagina_laterales(cubierta_aislada, unidades)),
    ]
    pagina_componentes = None
    with contextlib.suppress(ErrorLineamientos):
        # Sin lineamientos para componentes, el resto del reporte sigue
        # siendo válido y la página simplemente no aparece.
        pagina_componentes = _pagina_componentes(cubierta_aislada, unidades)
    if pagina_componentes is not None:
        paginas.append(("Componentes (C&R)", pagina_componentes))
    return VistaReporte(
        cubierta_aislada,
        "cubierta-aislada.md",
        "PRESIONES DE VIENTO — CUBIERTA AISLADA",
        paginas,
    )


def _ubicacion(fila: FilaCubiertaAislada) -> str:
    """Describe dónde se produce la presión de una fila.

    Args:
        fila: La fila de resultado.

    Returns:
        El texto con la dirección del viento, el caso y la zona.
    """
    partes = [fila.direccion.value]
    if fila.caso:
        partes.append(fila.caso.value)
    if fila.zona:
        partes.append(fila.zona.value)
    return ", ".join(partes)


def _pagina_resumen(
    cubierta_aislada: CubiertaAislada, unidades: dict[str, Unidad]
) -> QtWidgets.QWidget:
    """La página con los valores clave del cálculo.

    Args:
        cubierta_aislada: La cubierta aislada calculada.
        unidades: Las unidades a mostrar.

    Returns:
        La página armada.
    """
    unidad = f"{unidades['presion'].value}/m²"
    minimo, maximo = cubierta_aislada.resultados.min_max()
    seccion = Seccion("Resumen")
    seccion.agregar(
        fila_tarjetas(
            Tarjeta("Velocidad básica", f"{cubierta_aislada.velocidad:.2f} m/s"),
            Tarjeta(
                "Presión dinámica, qh",
                f"{convertir_unidad(cubierta_aislada.resultados[0].q.valor, unidades['presion']):.2f} {unidad}",
            ),
            Tarjeta("Factor de ráfaga, G", f"{cubierta_aislada.rafaga.factor:.2f}"),
            Tarjeta(
                "Bloqueo",
                f"{cubierta_aislada.geometria.bloqueo:.0f} %",
                detalle=(
                    "flujo de viento obstruido"
                    if cubierta_aislada.geometria.con_bloqueo
                    else "flujo de viento libre"
                ),
            ),
        )
    )
    tarjetas_extremos: list[Tarjeta] = []
    if maximo > 0:
        fila_max = next(
            fila for fila in cubierta_aislada.resultados if maximo in fila.presiones
        )
        tarjetas_extremos.append(
            Tarjeta(
                "Máxima presión",
                f"{convertir_unidad(maximo, unidades['presion']):+.2f} {unidad}",
                detalle=_ubicacion(fila_max),
                destacada=True,
            )
        )
    if minimo < 0:
        fila_min = next(
            fila for fila in cubierta_aislada.resultados if minimo in fila.presiones
        )
        tarjetas_extremos.append(
            Tarjeta(
                "Máxima succión",
                f"{convertir_unidad(minimo, unidades['presion']):+.2f} {unidad}",
                detalle=_ubicacion(fila_min),
                destacada=True,
            )
        )
    if tarjetas_extremos:
        seccion.agregar(fila_tarjetas(*tarjetas_extremos))
    seccion.agregar(
        Nota(NOTA_MINIMAS_SPRFV, "Cargas de viento de diseño mínimas (Art. 2.1.5)")
    )
    seccion.agregar_estiramiento()
    return pagina(seccion)


def _pagina_datos(cubierta_aislada: CubiertaAislada) -> QtWidgets.QWidget:
    """La página con el reglamento y los datos de entrada.

    Args:
        cubierta_aislada: La cubierta aislada calculada.

    Returns:
        La página armada.
    """
    seccion_reglamento = Seccion("Reglamento")
    seccion_reglamento.agregar(TablaDatos((("Referencia", "Cap. 2, Art. 2.4.3"),)))

    seccion_cubierta = Seccion("Cubierta Aislada")
    seccion_cubierta.agregar(
        TablaDatos(
            (
                ("Ancho", f"{cubierta_aislada.ancho:.2f} m"),
                ("Longitud", f"{cubierta_aislada.longitud:.2f} m"),
                ("Altura de alero", f"{cubierta_aislada.altura_alero:.2f} m"),
                ("Altura de cumbrera", f"{cubierta_aislada.altura_cumbrera:.2f} m"),
                (
                    "Tipo de cubierta",
                    cubierta_aislada.geometria.tipo_cubierta.value.capitalize(),
                ),
            )
        )
    )

    return pagina(
        seccion_reglamento,
        seccion_cubierta,
        seccion_viento(cubierta_aislada),
        seccion_rafaga(cubierta_aislada, TEXTO_RAFAGA_SIMPLIFICADA),
        seccion_topografia(cubierta_aislada),
    )


def _pagina_parametros(cubierta_aislada: CubiertaAislada) -> QtWidgets.QWidget:
    """La página con los parámetros intermedios del cálculo.

    Args:
        cubierta_aislada: La cubierta aislada calculada.

    Returns:
        La página armada.
    """
    subseccion_cubierta = Subseccion("Cubierta")
    subseccion_cubierta.agregar(
        TablaDatos(
            (
                ("Ángulo de cubierta", f"{cubierta_aislada.geometria.angulo:.2f}°"),
                (
                    "Altura media de cubierta",
                    f"{cubierta_aislada.geometria.altura_media:.2f} m",
                ),
                ("Bloqueo", f"{cubierta_aislada.geometria.bloqueo:.0f} %"),
                (
                    "Flujo de viento",
                    "obstruido" if cubierta_aislada.geometria.con_bloqueo else "libre",
                ),
                (
                    "Factor de direccionalidad, Kd",
                    f"{cubierta_aislada.presiones.factor_direccionalidad:.2f}",
                ),
            )
        )
    )

    seccion = Seccion("Parámetros de cálculo")
    seccion.agregar(subseccion_cubierta)
    seccion.agregar(subseccion_constantes_terreno(cubierta_aislada.rafaga))
    seccion.agregar(
        subseccion_factor_rafaga(
            cubierta_aislada.rafaga,
            cubierta_aislada.flexibilidad,
            TEXTO_RAFAGA_SIMPLIFICADA,
        )
    )
    seccion.agregar(
        subseccion_factor_topografico(
            cubierta_aislada,
            cubierta_aislada.topografia.parametros.k3[0],
            ["El valor de K3 es el correspondiente a la altura media."],
        )
    )
    seccion.agregar_estiramiento()
    return pagina(seccion)


def _pagina_normales(
    cubierta_aislada: CubiertaAislada, unidades: dict[str, Unidad]
) -> QtWidgets.QWidget:
    """La página con las presiones normales por dirección del viento.

    Args:
        cubierta_aislada: La cubierta aislada calculada.
        unidades: Las unidades a mostrar.

    Returns:
        La página armada, con una pestaña por dirección.
    """
    seccion = Seccion("Presiones Normales", descripcion=DESCRIPCION_NORMALES)

    pestañas = QtWidgets.QTabWidget()
    for direccion in DireccionVientoCubiertaAislada:
        filas = cubierta_aislada.resultados.filtrar(direccion=direccion)
        subseccion = Subseccion(
            f"Viento {direccion.value}", referencia=filas[0].referencia
        )
        subseccion.agregar(tablas.tabla_cubierta_aislada(filas, unidades))
        contenedor = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(contenedor)
        # El margen separa la tarjeta del pane de la pestaña.
        layout.setContentsMargins(9, 9, 9, 9)
        layout.addWidget(subseccion)
        layout.addStretch(1)
        pestañas.addTab(contenedor, direccion.value)
    seccion.agregar(pestañas)
    seccion.agregar_estiramiento()
    return pagina(seccion)


def _pagina_laterales(
    cubierta_aislada: CubiertaAislada, unidades: dict[str, Unidad]
) -> QtWidgets.QWidget:
    """La página con las presiones laterales de cenefas, parapetos y tímpanos.

    Args:
        cubierta_aislada: La cubierta aislada calculada.
        unidades: Las unidades a mostrar.

    Returns:
        La página armada.
    """
    unidad = f"{unidades['presion'].value}/m²"
    # La presión dinámica de la superficie, igual que la que usa la
    # plantilla: la de la primera fila, evaluada a la altura media.
    presion_velocidad = convertir_unidad(
        cubierta_aislada.resultados[0].q.valor, unidades["presion"]
    )

    subseccion_cenefas = Subseccion(
        "Cenefas, Parapetos y Tímpanos", referencia="Art. 2.4.5"
    )
    subseccion_cenefas.agregar(
        TablaDatos(
            (
                (
                    "A barlovento (GCpn = +1.5)",
                    f"{1.5 * presion_velocidad:.2f} {unidad}",
                ),
                (
                    "A sotavento (GCpn = -1.0)",
                    f"{-1.0 * presion_velocidad:.2f} {unidad}",
                ),
            )
        )
    )
    subseccion_cenefas.agregar(Nota(DESCRIPCION_CENEFAS, "Cargas laterales"))

    subseccion_friccion = Subseccion(
        "Fuerzas de fricción", referencia="Art. 2.4.3.1 - Tabla 2.4-1"
    )
    texto_friccion = QtWidgets.QLabel(DESCRIPCION_FRICCION)
    texto_friccion.setWordWrap(True)
    subseccion_friccion.agregar(texto_friccion)

    seccion = Seccion("Presiones Laterales")
    seccion.agregar(subseccion_cenefas)
    seccion.agregar(subseccion_friccion)
    seccion.agregar_estiramiento()
    return pagina(seccion)


def _contenido_componente(
    nombre: str,
    area: float,
    filas: Tabla[FilaComponentesCubiertaAislada],
    unidades: dict[str, Unidad],
) -> QtWidgets.QWidget:
    """La página de un componente: su tabla de presiones netas por zona.

    Args:
        nombre: El nombre del componente.
        area: Su área efectiva de viento.
        filas: Las filas del componente.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        El contenido de la página del componente.
    """
    contenedor = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(contenedor)
    layout.setContentsMargins(0, 0, 0, 0)
    subseccion = Subseccion(
        f"Componente: {nombre} ({area:g} m²)",
        referencia=(f"{filas[0].referencia}; a: {filas[0].distancia_a:.2f} m"),
    )
    subseccion.agregar(tablas.tabla_componentes_cubierta_aislada(filas, unidades))
    layout.addWidget(subseccion)
    layout.addStretch(1)
    return contenedor


def _pagina_componentes(
    cubierta_aislada: CubiertaAislada, unidades: dict[str, Unidad]
) -> QtWidgets.QWidget | None:
    """La página con los componentes y revestimientos.

    Muestra de a un componente por vez: un desplegable elige cuál.

    Args:
        cubierta_aislada: La cubierta aislada calculada.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        La página armada, o ``None`` cuando la cubierta no tiene
        componentes cargados.

    Raises:
        ErrorLineamientos: Cuando el Reglamento no da lineamientos para
            la geometría de la cubierta.
    """
    componentes = cubierta_aislada.resultados_componentes
    if not componentes or cubierta_aislada.componentes is None:
        return None

    nombres: list[str] = []
    páginas: list[QtWidgets.QWidget] = []
    for nombre, area in cubierta_aislada.componentes.items():
        nombres.append(nombre)
        páginas.append(
            _contenido_componente(
                nombre, area, componentes.filtrar(componente=nombre), unidades
            )
        )

    seccion = Seccion(
        "Componentes y Revestimientos", descripcion=DESCRIPCION_COMPONENTES
    )
    seccion.agregar(apilador_componentes([("Componentes", nombres, páginas)]))
    seccion.agregar(
        Nota(
            NOTA_MINIMAS_COMPONENTES,
            "Presiones de viento de diseño mínimas (Art. 5.2.2)",
        )
    )
    seccion.agregar_estiramiento()
    return pagina(seccion)
