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

"""Herramientas de cálculo del servidor MCP.

Cada función calcula una tipología con los parámetros de
``zonda.cirsoc.estructuras`` y devuelve la respuesta completa: las filas de
resultados, las referencias del Reglamento, las coordenadas de las zonas y la
metadata (unidades y sistema de coordenadas). Los enums llegan como strings
por su nombre y se convierten acá, con error claro si el valor no existe.
"""

from __future__ import annotations

import enum
from typing import Annotated, Any, Literal

from pydantic import Field

from zonda.cirsoc import estructuras
from zonda.enums import (
    CategoriaEstructura,
    CategoriaExposicion,
    Cerramiento,
    DireccionTopografia,
    Estructura,
    Flexibilidad,
    MetodoSprfv,
    TipoCubierta,
    TipoTerrenoTopografia,
)
from zonda.excepciones import ErrorLineamientos
from zonda.mcp import geometria
from zonda.mcp.serializacion import (
    SISTEMA_COORDENADAS,
    UNIDADES,
    referencias,
    serializar_tabla,
    serializar_valor,
)

Positivo = Annotated[float, Field(gt=0)]
"""Un número mayor que cero."""
NoNegativo = Annotated[float, Field(ge=0)]
"""Un número mayor o igual que cero."""
Porcentaje = Annotated[float, Field(ge=0, le=100)]
"""Un porcentaje entre 0 y 100."""
Proporcion = Annotated[float, Field(ge=0, le=1)]
"""Una proporción entre 0 y 1."""
AreasEfectivas = dict[str, Annotated[float, Field(gt=0)]]
"""Los componentes de una tipología, como nombre y área efectiva de viento en m2."""
AlturasPersonalizadas = list[Annotated[float, Field(gt=0)]]
"""Las alturas de cálculo de la presión de velocidad, en m."""
Aberturas = list[Annotated[float, Field(ge=0, le=100)]]
"""Los porcentajes de abertura de paredes y cubierta."""

TipoCubiertaMcp = Literal["PLANA", "UN_AGUA", "DOS_AGUAS"]
CerramientoMcp = Literal["CERRADO", "PARCIALMENTE_CERRADO", "ABIERTO"]
CategoriaExposicionMcp = Literal["B", "C", "D"]
FlexibilidadMcp = Literal["RIGIDA", "FLEXIBLE"]
TipoTerrenoMcp = Literal[
    "LOMA_BIDIMENSIONAL", "ESCARPA_BIDIMENSIONAL", "COLINA_TRIDIMENSIONAL"
]
DireccionTopografiaMcp = Literal["BARLOVENTO", "SOTAVENTO"]
CategoriaEstructuraMcp = Literal["I", "II", "III", "IV"]


def _enum[EnumT: enum.Enum](
    clase: type[EnumT], valor: str | None, campo: str
) -> EnumT | None:
    """Convierte el nombre de un enum al miembro de la clase.

    Args:
        clase: La clase del enum.
        valor: El nombre del miembro, o None.
        campo: El nombre del campo, para el mensaje de error.

    Returns:
        El miembro del enum, o None.

    Raises:
        ValueError: Cuando el nombre no existe en la clase.
    """
    if valor is None:
        return None
    try:
        return clase[valor]
    except KeyError:
        opciones = ", ".join(miembro.name for miembro in clase)
        raise ValueError(
            f"Valor de '{campo}' inválido: '{valor}'. Los valores posibles son: {opciones}."
        ) from None


def _respuesta(estructura: Estructura, entrada: dict) -> dict:
    """La base de la respuesta de una herramienta.

    Args:
        estructura: La tipología calculada.
        entrada: Los parámetros usados, ya convertidos.

    Returns:
        El diccionario con la metadata de la respuesta.
    """
    return {
        "estructura": estructura.name,
        "entrada": {clave: serializar_valor(valor) for clave, valor in entrada.items()},
        "sistema_coordenadas": SISTEMA_COORDENADAS,
        "unidades": UNIDADES,
    }


def _error_lineamientos(error: ErrorLineamientos) -> dict:
    """La sección de error por falta de lineamientos.

    Args:
        error: La excepción lanzada por el núcleo.

    Returns:
        El diccionario con el tipo y el mensaje de la excepción.
    """
    return {"tipo": type(error).__name__, "mensaje": str(error)}


def calcular_edificio(
    ancho: Positivo,
    longitud: Positivo,
    altura_alero: Positivo,
    altura_cumbrera: Positivo,
    tipo_cubierta: TipoCubiertaMcp,
    cerramiento: CerramientoMcp,
    velocidad: Positivo,
    categoria_exp: CategoriaExposicionMcp,
    elevacion: NoNegativo = 0,
    factor_g_simplificado: bool = True,
    considerar_topografia: bool = False,
    parapeto: NoNegativo = 0,
    alero: NoNegativo = 0,
    reducir_gcpi: bool = False,
    alturas_personalizadas: AlturasPersonalizadas | None = None,
    aberturas: Aberturas | None = None,
    volumen_interno: Positivo | None = None,
    componentes_paredes: AreasEfectivas | None = None,
    componentes_cubierta: AreasEfectivas | None = None,
    area_parapeto: Positivo | None = None,
    frecuencia: Positivo = 1,
    beta: NoNegativo = 0.02,
    flexibilidad: FlexibilidadMcp = "RIGIDA",
    tipo_terreno: TipoTerrenoMcp = "LOMA_BIDIMENSIONAL",
    altura_terreno: Positivo = 50,
    distancia_cresta: NoNegativo = 50,
    distancia_barlovento_sotavento: NoNegativo = 50,
    direccion_topografia: DireccionTopografiaMcp = "BARLOVENTO",
    altitud: NoNegativo = 0,
    factor_altitud: Positivo | None = None,
) -> dict:
    """Calcula las presiones de viento sobre un edificio según el CIRSOC 102-2025.

    Devuelve las filas de resultados del SPRFV y de componentes y
    revestimientos, cada una con sus claves (zona, pared, dirección, ...), su
    presión positiva y negativa, su coeficiente y la referencia del
    Reglamento; junto con las coordenadas de cada zona en los mismos ejes de
    la vista 3D (ver ``sistema_coordenadas`` en la respuesta). Los componentes
    y revestimientos no aparecen cuando el Reglamento no da lineamientos para
    la geometría.

    Args:
        ancho: El ancho del edificio, en m, perpendicular a la cumbrera.
        longitud: La longitud del edificio, en m, paralela a la cumbrera.
        altura_alero: La altura de alero, en m, medida desde el nivel 0.
        altura_cumbrera: La altura de cumbrera, en m, medida desde el nivel 0.
            Se ignora si la cubierta es plana.
        tipo_cubierta: El tipo de cubierta: PLANA, UN_AGUA o DOS_AGUAS.
        cerramiento: El cerramiento del edificio: CERRADO,
            PARCIALMENTE_CERRADO o ABIERTO.
        velocidad: La velocidad del viento, en m/s.
        categoria_exp: La categoría de exposición: B, C o D.
        elevacion: La elevación del edificio sobre el suelo, en m.
        factor_g_simplificado: Si se usa el factor de ráfaga simplificado
            G = 0,85. En False se calcula Gf para estructuras flexibles.
        considerar_topografia: Si se calcula el factor topográfico.
        parapeto: La altura del parapeto, en m. 0 indica que no hay.
        alero: La dimensión del alero, en m. 0 indica que no hay.
        reducir_gcpi: Si se reduce el coeficiente de presión interna.
        alturas_personalizadas: Las alturas en m en que se calcula la presión
            de velocidad. None usa las del Reglamento.
        aberturas: Los porcentajes de abertura de paredes y cubierta para
            determinar el cerramiento. None usa el Reglamento.
        volumen_interno: El volumen interno del edificio, en m3. None usa el
            calculado de la geometría.
        componentes_paredes: Los componentes de paredes, como nombre y área
            efectiva de viento en m2, para C&R.
        componentes_cubierta: Los componentes de cubierta, como nombre y área
            efectiva de viento en m2, para C&R.
        area_parapeto: El área efectiva de viento del parapeto, en m2.
        frecuencia: La frecuencia natural, en Hz.
        beta: La relación de amortiguamiento crítico.
        flexibilidad: La flexibilidad: RIGIDA o FLEXIBLE.
        tipo_terreno: El tipo de terreno: LOMA_BIDIMENSIONAL,
            ESCARPA_BIDIMENSIONAL o COLINA_TRIDIMENSIONAL.
        altura_terreno: La altura de la colina o escarpa, en m.
        distancia_cresta: La distancia desde la cresta, en m.
        distancia_barlovento_sotavento: La distancia desde la cima en
            barlovento o sotavento, en m.
        direccion_topografia: La dirección de la distancia: BARLOVENTO o
            SOTAVENTO.
        altitud: La altitud del terreno, en m.
        factor_altitud: El factor de altitud Ke explícito. None lo calcula
            de la altitud.

    Returns:
        La respuesta con ``estructura``, ``entrada``, ``sistema_coordenadas``,
        ``unidades``, ``resultados_sprfv``, ``referencias_sprfv``,
        ``resultados_componentes``, ``referencias_componentes``, ``zonas`` y,
        si el Reglamento no da lineamientos para componentes,
        ``error_componentes``.
    """
    parametros: dict[str, Any] = {
        "ancho": ancho,
        "longitud": longitud,
        "elevacion": elevacion,
        "altura_alero": altura_alero,
        "altura_cumbrera": altura_cumbrera,
        "tipo_cubierta": _enum(TipoCubierta, tipo_cubierta, "tipo_cubierta"),
        "cerramiento": _enum(Cerramiento, cerramiento, "cerramiento"),
        "velocidad": velocidad,
        "factor_g_simplificado": factor_g_simplificado,
        "categoria_exp": _enum(CategoriaExposicion, categoria_exp, "categoria_exp"),
        "considerar_topografia": considerar_topografia,
        "parapeto": parapeto,
        "alero": alero,
        "reducir_gcpi": reducir_gcpi,
        # El método envolvente no está implementado: la app sólo usa el
        # direccional y el núcleo rechaza cualquier otro valor.
        "metodo_sprfv": MetodoSprfv.DIRECCIONAL,
        "alturas_personalizadas": alturas_personalizadas,
        "aberturas": tuple(aberturas) if aberturas is not None else None,
        "volumen_interno": volumen_interno,
        "componentes_paredes": componentes_paredes,
        "componentes_cubierta": componentes_cubierta,
        "area_parapeto": area_parapeto,
        "frecuencia": frecuencia,
        "beta": beta,
        "flexibilidad": _enum(Flexibilidad, flexibilidad, "flexibilidad"),
        "tipo_terreno": _enum(TipoTerrenoTopografia, tipo_terreno, "tipo_terreno"),
        "altura_terreno": altura_terreno,
        "distancia_cresta": distancia_cresta,
        "distancia_barlovento_sotavento": distancia_barlovento_sotavento,
        "direccion": _enum(
            DireccionTopografia, direccion_topografia, "direccion_topografia"
        ),
        "altitud": altitud,
        "factor_altitud": factor_altitud,
    }
    estructura = estructuras.Edificio(**parametros)
    respuesta = _respuesta(Estructura.EDIFICIO, parametros)
    respuesta["resultados_sprfv"] = serializar_tabla(estructura.resultados_sprfv)
    respuesta["referencias_sprfv"] = referencias(estructura.resultados_sprfv)
    respuesta["zonas"] = geometria.zonas_edificio(estructura)
    try:
        respuesta["resultados_componentes"] = serializar_tabla(
            estructura.resultados_componentes
        )
        respuesta["referencias_componentes"] = referencias(
            estructura.resultados_componentes
        )
    except ErrorLineamientos as error:
        respuesta["error_componentes"] = _error_lineamientos(error)
    return respuesta


def calcular_cartel(
    ancho: Positivo,
    altura_inferior: NoNegativo,
    altura_superior: Positivo,
    profundidad: Positivo,
    velocidad: Positivo,
    categoria_exp: CategoriaExposicionMcp,
    factor_g_simplificado: bool = True,
    considerar_topografia: bool = False,
    epsilon: Proporcion = 1.0,
    doble_cara: bool = False,
    esquina_retorno: NoNegativo = 0,
    frecuencia: Positivo = 1,
    beta: NoNegativo = 0.02,
    flexibilidad: FlexibilidadMcp = "RIGIDA",
    tipo_terreno: TipoTerrenoMcp = "LOMA_BIDIMENSIONAL",
    altura_terreno: Positivo = 50,
    distancia_cresta: NoNegativo = 50,
    distancia_barlovento_sotavento: NoNegativo = 50,
    direccion_topografia: DireccionTopografiaMcp = "BARLOVENTO",
    altitud: NoNegativo = 0,
    factor_altitud: Positivo | None = None,
) -> dict:
    """Calcula las fuerzas de viento sobre un cartel según el CIRSOC 102-2025.

    Devuelve una fila por caso de la Figura 4.4-1 (A, B y una por región del
    C), con la fuerza resultante, el coeficiente Cf y la referencia del
    Reglamento; junto con las coordenadas de las caras y de las regiones del
    Caso C (ver ``sistema_coordenadas`` en la respuesta).

    Args:
        ancho: El ancho del cartel, en m.
        altura_inferior: La altura del borde inferior, en m.
        altura_superior: La altura del borde superior, en m.
        profundidad: La profundidad del cartel, en m.
        velocidad: La velocidad del viento, en m/s.
        categoria_exp: La categoría de exposición: B, C o D.
        factor_g_simplificado: Si se usa el factor de ráfaga simplificado
            G = 0,85. En False se calcula Gf para estructuras flexibles.
        considerar_topografia: Si se calcula el factor topográfico.
        epsilon: La relación entre el área sólida y el área bruta. 1.0 es un
            cartel sin aberturas.
        doble_cara: Si el cartel es de doble cara con todos los lados
            cerrados; aplica las reducciones de Rmin y Rmax.
        esquina_retorno: La dimensión horizontal de la esquina de retorno,
            en m. 0 indica que no hay.
        frecuencia: La frecuencia natural, en Hz.
        beta: La relación de amortiguamiento crítico.
        flexibilidad: La flexibilidad: RIGIDA o FLEXIBLE.
        tipo_terreno: El tipo de terreno: LOMA_BIDIMENSIONAL,
            ESCARPA_BIDIMENSIONAL o COLINA_TRIDIMENSIONAL.
        altura_terreno: La altura de la colina o escarpa, en m.
        distancia_cresta: La distancia desde la cresta, en m.
        distancia_barlovento_sotavento: La distancia desde la cima en
            barlovento o sotavento, en m.
        direccion_topografia: La dirección de la distancia: BARLOVENTO o
            SOTAVENTO.
        altitud: La altitud del terreno, en m.
        factor_altitud: El factor de altitud Ke explícito. None lo calcula
            de la altitud.

    Returns:
        La respuesta con ``estructura``, ``entrada``, ``sistema_coordenadas``,
        ``unidades``, ``resultados``, ``referencias`` y ``zonas``.
    """
    parametros: dict[str, Any] = {
        "profundidad": profundidad,
        "ancho": ancho,
        "altura_inferior": altura_inferior,
        "altura_superior": altura_superior,
        "velocidad": velocidad,
        "factor_g_simplificado": factor_g_simplificado,
        "categoria_exp": _enum(CategoriaExposicion, categoria_exp, "categoria_exp"),
        "considerar_topografia": considerar_topografia,
        "epsilon": epsilon,
        "doble_cara": doble_cara,
        "esquina_retorno": esquina_retorno,
        "frecuencia": frecuencia,
        "beta": beta,
        "flexibilidad": _enum(Flexibilidad, flexibilidad, "flexibilidad"),
        "tipo_terreno": _enum(TipoTerrenoTopografia, tipo_terreno, "tipo_terreno"),
        "altura_terreno": altura_terreno,
        "distancia_cresta": distancia_cresta,
        "distancia_barlovento_sotavento": distancia_barlovento_sotavento,
        "direccion": _enum(
            DireccionTopografia, direccion_topografia, "direccion_topografia"
        ),
        "altitud": altitud,
        "factor_altitud": factor_altitud,
    }
    estructura = estructuras.Cartel(**parametros)
    respuesta = _respuesta(Estructura.CARTEL, parametros)
    respuesta["resultados"] = serializar_tabla(estructura.resultados)
    respuesta["referencias"] = referencias(estructura.resultados)
    respuesta["zonas"] = geometria.zonas_cartel(estructura)
    return respuesta


def calcular_cubierta_aislada(
    ancho: Positivo,
    longitud: Positivo,
    altura_alero: Positivo,
    altura_cumbrera: Positivo,
    tipo_cubierta: TipoCubiertaMcp,
    velocidad: Positivo,
    categoria_exp: CategoriaExposicionMcp,
    bloqueo: Porcentaje = 0,
    coeficiente_friccion: NoNegativo = 0.01,
    factor_g_simplificado: bool = True,
    considerar_topografia: bool = False,
    componentes: AreasEfectivas | None = None,
    frecuencia: Positivo = 1,
    beta: NoNegativo = 0.02,
    flexibilidad: FlexibilidadMcp = "RIGIDA",
    tipo_terreno: TipoTerrenoMcp = "LOMA_BIDIMENSIONAL",
    altura_terreno: Positivo = 50,
    distancia_cresta: NoNegativo = 50,
    distancia_barlovento_sotavento: NoNegativo = 50,
    direccion_topografia: DireccionTopografiaMcp = "BARLOVENTO",
    altitud: NoNegativo = 0,
    factor_altitud: Positivo | None = None,
    categoria: CategoriaEstructuraMcp = "II",
) -> dict:
    """Calcula las presiones de viento sobre una cubierta aislada según el CIRSOC 102-2025.

    Devuelve una fila por cada combinación de dirección de viento, caso de
    carga y zona de las Figuras 2.4-4 a 2.4-7, con la presión neta, la fricción
    y la referencia del Reglamento; junto con las coordenadas de las zonas
    (ver ``sistema_coordenadas`` en la respuesta). Si se pasan componentes,
    agrega sus filas de C&R y las coordenadas de sus zonas.

    Args:
        ancho: El ancho de la cubierta, en m, perpendicular a la cumbrera.
        longitud: La longitud de la cubierta, en m, paralela a la cumbrera.
        altura_alero: La altura de alero, en m, medida desde el suelo.
        altura_cumbrera: La altura de cumbrera, en m, medida desde el suelo.
        tipo_cubierta: El tipo de cubierta: PLANA, UN_AGUA o DOS_AGUAS.
        velocidad: La velocidad del viento, en m/s.
        categoria_exp: La categoría de exposición: B, C o D.
        bloqueo: El porcentaje de bloqueo del flujo bajo la cubierta, en %.
            Mayor al 50 % aplica los casos con bloqueo.
        coeficiente_friccion: El coeficiente de fricción de la Tabla 2.4-1
            (0,01 lisa, 0,02 ondulaciones transversales, 0,04 nervaduras
            transversales).
        factor_g_simplificado: Si se usa el factor de ráfaga simplificado
            G = 0,85. En False se calcula Gf para estructuras flexibles.
        considerar_topografia: Si se calcula el factor topográfico.
        componentes: Los componentes de la cubierta, como nombre y área
            efectiva de viento en m2, para calcular sus C_N.
        frecuencia: La frecuencia natural, en Hz.
        beta: La relación de amortiguamiento crítico.
        flexibilidad: La flexibilidad: RIGIDA o FLEXIBLE.
        tipo_terreno: El tipo de terreno: LOMA_BIDIMENSIONAL,
            ESCARPA_BIDIMENSIONAL o COLINA_TRIDIMENSIONAL.
        altura_terreno: La altura de la colina o escarpa, en m.
        distancia_cresta: La distancia desde la cresta, en m.
        distancia_barlovento_sotavento: La distancia desde la cima en
            barlovento o sotavento, en m.
        direccion_topografia: La dirección de la distancia: BARLOVENTO o
            SOTAVENTO.
        altitud: La altitud del terreno, en m.
        factor_altitud: El factor de altitud Ke explícito. None lo calcula
            de la altitud.
        categoria: La categoría de la estructura: I, II, III o IV. Quedó como
            dato del modelo: el CIRSOC 102-2025 no la usa para calcular.

    Returns:
        La respuesta con ``estructura``, ``entrada``, ``sistema_coordenadas``,
        ``unidades``, ``resultados``, ``referencias`` y ``zonas``; con
        ``resultados_componentes``, ``referencias_componentes`` y
        ``zonas.componentes`` si hay componentes. ``error_componentes`` cuando
        el Reglamento no da lineamientos para la geometría.
    """
    parametros: dict[str, Any] = {
        "ancho": ancho,
        "longitud": longitud,
        "altura_alero": altura_alero,
        "altura_cumbrera": altura_cumbrera,
        "bloqueo": bloqueo,
        "tipo_cubierta": _enum(TipoCubierta, tipo_cubierta, "tipo_cubierta"),
        "coeficiente_friccion": coeficiente_friccion,
        "velocidad": velocidad,
        "categoria_exp": _enum(CategoriaExposicion, categoria_exp, "categoria_exp"),
        "considerar_topografia": considerar_topografia,
        "factor_g_simplificado": factor_g_simplificado,
        "componentes": componentes,
        "categoria": _enum(CategoriaEstructura, categoria, "categoria"),
        "frecuencia": frecuencia,
        "beta": beta,
        "flexibilidad": _enum(Flexibilidad, flexibilidad, "flexibilidad"),
        "tipo_terreno": _enum(TipoTerrenoTopografia, tipo_terreno, "tipo_terreno"),
        "altura_terreno": altura_terreno,
        "distancia_cresta": distancia_cresta,
        "distancia_barlovento_sotavento": distancia_barlovento_sotavento,
        "direccion": _enum(
            DireccionTopografia, direccion_topografia, "direccion_topografia"
        ),
        "altitud": altitud,
        "factor_altitud": factor_altitud,
    }
    estructura = estructuras.CubiertaAislada(**parametros)
    respuesta = _respuesta(Estructura.CUBIERTA_AISLADA, parametros)
    respuesta["resultados"] = serializar_tabla(estructura.resultados)
    respuesta["referencias"] = referencias(estructura.resultados)
    respuesta["zonas"] = geometria.zonas_cubierta_aislada(estructura)
    if estructura.componentes:
        try:
            respuesta["resultados_componentes"] = serializar_tabla(
                estructura.resultados_componentes
            )
            respuesta["referencias_componentes"] = referencias(
                estructura.resultados_componentes
            )
        except ErrorLineamientos as error:
            respuesta["error_componentes"] = _error_lineamientos(error)
    return respuesta
