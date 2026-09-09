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

"""El documento de reporte del edificio.

Arma las páginas del modelo: el resumen con los valores clave, los datos
de entrada, los parámetros de cálculo, las presiones del SPRFV por
dirección de viento y las de componentes y revestimientos. Todo se lee de
``estructura.resultados_sprfv`` y ``estructura.resultados_componentes``
filtrando y agrupando la tabla plana. La vista y el PDF lo consumen sin
conocerse entre sí.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

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
    grupo_constantes_terreno,
    grupo_factor_rafaga,
    grupo_factor_topografico,
    grupo_rafaga,
    grupo_topografia,
    grupo_viento,
)
from zonda.widgets.reportes.documento import (
    Bloque,
    Datos,
    Documento,
    Grupo,
    Nota,
    Pagina,
    Pestanas,
    SelectorComponentes,
    Superficie,
    Tarjeta,
    Tarjetas,
)
from zonda.widgets.reportes.navegacion import VistaReporte
from zonda.widgets.reportes.secciones import unidades_desde_settings

if TYPE_CHECKING:
    from zonda.cirsoc import Edificio
    from zonda.cirsoc.resultados import FilaEdificio
    from zonda.cirsoc.resultados import Tabla as TablaNucleo

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

ETIQUETAS_SUPERFICIES = {
    ZonaEdificio.PAREDES: "PARED",
    ZonaEdificio.CUBIERTA: "CUBIERTA",
}


def vista(edificio: Edificio) -> VistaReporte:
    """Arma la vista de reporte del edificio.

    Args:
        edificio: El edificio calculado.

    Returns:
        La vista con sus páginas.
    """
    return VistaReporte(documento(edificio))


def documento(edificio: Edificio) -> Documento:
    """Arma el documento de reporte del edificio.

    Args:
        edificio: El edificio calculado.

    Returns:
        El documento con sus páginas.
    """
    unidades = unidades_desde_settings()
    paginas = [
        Pagina("Resumen", _bloques_resumen(edificio, unidades), exportable=False),
        Pagina("Datos de entrada", _bloques_datos(edificio)),
        Pagina("Parámetros de cálculo", _bloques_parametros(edificio)),
        Pagina("Presiones - SPRFV", _bloques_sprfv(edificio, unidades)),
    ]
    with contextlib.suppress(ErrorLineamientos):
        # Sin lineamientos para componentes, el reporte del SPRFV sigue
        # siendo válido y la página simplemente no aparece.
        bloques_componentes = _bloques_componentes(edificio, unidades)
        if bloques_componentes is not None:
            # En el índice la página va con el nombre corto que usan las
            # pestañas del panel; la sección de adentro lleva el completo.
            paginas.append(Pagina("Componentes (C&R)", bloques_componentes))
    return Documento("PRESIONES DE VIENTO — EDIFICIO", paginas)


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


def _bloques_resumen(edificio: Edificio, unidades: dict[str, Unidad]) -> list[Bloque]:
    """Los bloques con los valores que gobiernan el diseño.

    Args:
        edificio: El edificio calculado.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        Los bloques de la página de resumen.
    """
    sprfv = edificio.presiones.cubierta.sprfv
    kzt = (
        max(edificio.topografia.factor)
        if edificio.topografia.topografia_considerada()
        else 1.0
    )
    bloques: list[Bloque] = [
        Tarjetas(
            [
                Tarjeta("Velocidad básica", f"{edificio.velocidad:.2f} m/s"),
                Tarjeta("Coeficiente de presión interna", f"±{sprfv.gcpi:.2f}"),
                Tarjeta(
                    "Factor topográfico, Kzt",
                    f"{kzt:.2f}",
                    detalle="máximo entre las alturas" if kzt != 1.0 else None,
                ),
            ]
        )
    ]
    tarjetas_extremos = _tarjetas_extremos(edificio, unidades)
    if tarjetas_extremos:
        bloques.append(Tarjetas(tarjetas_extremos))
    return bloques


def _bloques_datos(edificio: Edificio) -> list[Bloque]:
    """Los bloques con el reglamento y los datos de entrada.

    Args:
        edificio: El edificio calculado.

    Returns:
        Los bloques de la página de datos.
    """
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
    return [
        Grupo(
            "Método de cálculo",
            [
                Datos(
                    (
                        (
                            "Método",
                            "2 (Analítico) - Procedimiento "
                            f"{edificio.metodo_sprfv.value.capitalize()}",
                        ),
                    )
                )
            ],
        ),
        Grupo("Edificio", [Datos(filas)]),
        grupo_viento(edificio),
        grupo_rafaga(edificio, TEXTO_RAFAGA_SIMPLIFICADA),
        grupo_topografia(edificio),
    ]


def _bloques_parametros(edificio: Edificio) -> list[Bloque]:
    """Los bloques con los parámetros intermedios del cálculo.

    Args:
        edificio: El edificio calculado.

    Returns:
        Los bloques de la página de parámetros.
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
    return [
        Grupo("Cubierta", [Datos(filas)]),
        grupo_constantes_terreno(
            edificio.rafaga[DireccionVientoMetodoDireccionalSprfv.PARALELO]
        ),
        grupo_factor_rafaga(
            edificio.rafaga, edificio.flexibilidad, TEXTO_RAFAGA_SIMPLIFICADA
        ),
        grupo_factor_topografico(
            edificio,
            edificio.topografia.k3_en(edificio.geometria.cubierta.altura_media),
            [NOTA_K3],
        ),
    ]


def _titulo_superficie(base: str, clave: tuple, sin_posicion: str | None = None) -> str:
    """El título de una superficie de cubierta o alero.

    Cuando la superficie no está dividida por posición, igualmente nombra
    el caso de presión si la fila lo trae (el caso positivo del nuevo
    Reglamento con ángulo < 10°).

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


def _bloques_direccion(
    edificio: Edificio,
    direccion: DireccionVientoMetodoDireccionalSprfv,
    unidades: dict[str, Unidad],
) -> list[Bloque]:
    """Los grupos de presiones de una dirección de viento.

    Args:
        edificio: El edificio calculado.
        direccion: La dirección del viento.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        Los grupos de paredes, cubierta y alero, en orden.
    """
    filas_direccion = edificio.resultados_sprfv.filtrar(direccion=direccion)
    bloques: list[Bloque] = []
    for pared, filas in filas_direccion.filtrar(zona=ZonaEdificio.PAREDES).agrupar(
        "pared"
    ):
        bloques.append(
            Grupo(
                f"Pared {pared.value.capitalize()}" if pared else "Paredes",
                [tablas.tabla_presiones(filas, unidades)],
                referencia=filas[0].referencia,
            )
        )
    for clave, filas in filas_direccion.filtrar(zona=ZonaEdificio.CUBIERTA).agrupar(
        "posicion", "caso"
    ):
        bloques.append(
            Grupo(
                _titulo_superficie("Cubierta", clave),
                [tablas.tabla_presiones(filas, unidades)],
                referencia=filas[0].referencia,
            )
        )
    for clave, filas in filas_direccion.filtrar(zona=ZonaEdificio.ALERO).agrupar(
        "posicion", "caso"
    ):
        bloques.append(
            Grupo(
                _titulo_superficie("Alero", clave, "Aleros"),
                [tablas.tabla_presiones(filas, unidades)],
                referencia=filas[0].referencia,
            )
        )
    return bloques


def _bloques_sprfv(edificio: Edificio, unidades: dict[str, Unidad]) -> list[Bloque]:
    """Los bloques con las presiones del SPRFV.

    Args:
        edificio: El edificio calculado.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        Los bloques: una pestaña por dirección de viento, el parapeto
        cuando lo hay y las notas del Reglamento.
    """
    bloques: list[Bloque] = [
        Pestanas(
            [
                (
                    f"{direccion.value.capitalize()} a la cumbrera",
                    _bloques_direccion(edificio, direccion, unidades),
                )
                for direccion in DireccionVientoMetodoDireccionalSprfv
            ]
        )
    ]

    parapeto = edificio.resultados_sprfv.filtrar(zona=ZonaEdificio.PARAPETO)
    if parapeto:
        bloques.append(
            Grupo(
                "Parapeto",
                [tablas.tabla_parapeto_sprfv(parapeto, unidades)],
                referencia=parapeto[0].referencia,
            )
        )
        bloques.append(Nota(NOTA_PARAPETO_SPRFV, "Parapeto (Art. 2.4.5)"))

    bloques.append(
        Nota(NOTA_MINIMAS_SPRFV, "Cargas de viento de diseño mínimas (Art. 2.1.5)")
    )
    return bloques


def _grupos_componente(
    filas_componente: TablaNucleo[FilaEdificio],
    areas: dict[str, float] | None,
    unidades: dict[str, Unidad],
) -> list[Grupo]:
    """Los grupos de un componente: su tabla de presiones.

    Con la Figura 5.4-1 (h > 20 m) las paredes se evalúan a cada altura y
    el Reglamento distingue zonas de área efectiva: la tabla se parte por
    zona, con un grupo por cada una.

    Args:
        filas_componente: Las filas del componente, de todas las paredes.
        areas: Las áreas efectivas de los componentes de la superficie.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        Los grupos del componente, uno por zona cuando corresponde.
    """
    areas = areas or {}
    nombre = filas_componente[0].componente or ""
    area = areas.get(nombre)
    area_texto = f" ({area:g} m²)" if area is not None else ""
    pared = filas_componente[0].pared
    titulo_pared = f"Pared {pared.value.capitalize()} — " if pared else ""
    referencia = filas_componente[0].referencia

    por_altura = len({fila.q.altura for fila in filas_componente}) > 1
    if not por_altura:
        return [
            Grupo(
                f"{titulo_pared}Componente: {nombre}{area_texto}",
                [tablas.tabla_presiones(filas_componente, unidades)],
                referencia=referencia,
            )
        ]

    return [
        Grupo(
            f"{titulo_pared}Componente: {nombre}{area_texto} "
            f"(Zona: {zona_componente.value.capitalize()})",
            [tablas.tabla_presiones(filas_zona, unidades)],
            referencia=filas_zona[0].referencia,
        )
        for zona_componente, filas_zona in filas_componente.agrupar("zona_componente")
    ]


def _bloques_componentes(
    edificio: Edificio, unidades: dict[str, Unidad]
) -> list[Bloque] | None:
    """Los bloques con las presiones de componentes y revestimientos.

    Args:
        edificio: El edificio calculado.
        unidades: Las unidades de fuerza y presión a mostrar.

    Returns:
        Los bloques, o ``None`` cuando el edificio no tiene componentes
        cargados.

    Raises:
        ErrorLineamientos: Cuando el Reglamento no da lineamientos para
            la geometría del edificio.
    """
    componentes = edificio.resultados_componentes
    if not componentes:
        return None

    superficies: list[Superficie] = []
    for zona, areas in (
        (ZonaEdificio.PAREDES, edificio.componentes_paredes),
        (ZonaEdificio.CUBIERTA, edificio.componentes_cubierta),
    ):
        filas_zona = componentes.filtrar(zona=zona)
        if not filas_zona:
            continue
        componentes_superficie: list[tuple[str, list[Bloque]]] = []
        for nombre, filas_componente in filas_zona.agrupar("componente"):
            componentes_superficie.append(
                (
                    nombre,
                    list(_grupos_componente(filas_componente, areas, unidades)),
                )
            )
        superficies.append(
            Superficie(ETIQUETAS_SUPERFICIES[zona], componentes_superficie)
        )

    filas_parapeto = componentes.filtrar(zona=ZonaEdificio.PARAPETO)
    if filas_parapeto:
        superficies.append(
            Superficie(
                "PARAPETO",
                [
                    (
                        "Parapeto",
                        [
                            Grupo(
                                f"Parapeto (área efectiva: "
                                f"{edificio.area_parapeto:g} m²)",
                                [
                                    tablas.tabla_parapeto_componentes(
                                        filas_parapeto, unidades
                                    )
                                ],
                                referencia=filas_parapeto[0].referencia,
                            ),
                            Nota(NOTA_PARAPETO_COMPONENTES, "Parapeto (Art. 5.6)"),
                        ],
                    )
                ],
            )
        )

    return [
        SelectorComponentes(superficies),
        Nota(
            NOTA_MINIMAS_COMPONENTES,
            "Presiones de viento de diseño mínimas (Art. 5.2.2)",
        ),
    ]
