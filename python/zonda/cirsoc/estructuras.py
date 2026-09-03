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

from __future__ import annotations

from collections.abc import Sequence
from functools import cached_property
from typing import TYPE_CHECKING

from zonda.cirsoc import cp, factores, geometria, presiones, resultados
from zonda.cirsoc.factores import Rafaga, Topografia
from zonda.enums import (
    DireccionTopografia,
    Flexibilidad,
    MetodoSprfv,
    TipoCubierta,
    TipoTerrenoTopografia,
)

if TYPE_CHECKING:
    from zonda.cirsoc.resultados import (
        FilaCartel,
        FilaCubiertaAislada,
        FilaEdificio,
        Tabla,
    )
    from zonda.enums import (
        CategoriaEstructura,
        CategoriaExposicion,
        Cerramiento,
        PosicionBloqueoCubierta,
    )


class Cartel:
    """Cartel.

    Calcula las presiones sobre un cartel y todos sus respectivos parámetros de acuerdo a los lineamiento del
    Reglamento CIRSOC 102-2025.
    """

    def __init__(
        self,
        profundidad: float,
        ancho: float,
        altura_inferior: float,
        altura_superior: float,
        velocidad: float,
        categoria: CategoriaEstructura,
        factor_g_simplificado: bool,
        categoria_exp: CategoriaExposicion,
        considerar_topografia: bool,
        es_parapeto: bool = False,
        epsilon: float = 1.0,
        doble_cara: bool = False,
        esquina_retorno: float = 0.0,
        frecuencia: float = 1,
        beta: float = 0.02,
        flexibilidad: Flexibilidad = Flexibilidad.RIGIDA,
        tipo_terreno: TipoTerrenoTopografia = TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno: float = 50,
        distancia_cresta: float = 50,
        distancia_barlovento_sotavento: float = 50,
        direccion: DireccionTopografia = DireccionTopografia.BARLOVENTO,
        altitud: float = 0,
        factor_altitud: float | None = None,
    ) -> None:
        """

        Args:
            profundidad: La profundidad del cartel.
            ancho: El ancho del cartel.
            altura_inferior: La altura desde el suelo desde donde se consideran las presiones del viento sobre el cartel.
            altura_superior: La altura superior del cartel.
            velocidad: La velocidad del viento en m/s.
            categoria: La categoría de la estructura.
            factor_g_simplificado: Indica si se debe usar 0.85 como valor del factor de ráfaga.
            categoria_exp: La categoría de exposición al viento de la estructura.
            considerar_topografia: indica si se tiene que calcular la topografia.
            es_parapeto: Si es True, se considera que el cartel actua como parapeto de edificio.
            epsilon: La relación entre el área sólida y el área bruta del cartel (Nota 1
                de la Figura 4.4-1). El valor 1.0 es un cartel sin aberturas.
            doble_cara: Si es True, el cartel es de doble cara con todos los lados
                cerrados y aplican las reducciones de Rmin y Rmax de la Nota 2.
            esquina_retorno: La dimensión horizontal Lr de la esquina de retorno, en
                metros. El valor 0 indica que no hay.
            frecuencia: La frecuencia natural de la estructura en hz.
            beta: La relación de amortiguamiento crítico.
            flexibilidad: La flexibilidad de la estructura.
            tipo_terreno: El tipo de terreno.
            altura_terreno: La altura de la colina o escarpa.
            distancia_cresta: La distancia en la dirección de barlovento, medida desde la cresta de la colina o escarpa.
            distancia_barlovento_sotavento: Distancia tomada desde la cima, en la dirección de barlovento o de sotavento.
            direccion: La direccion para la el parámetro `distancia_barlovento_sotavento`.
            altitud: Altitud del terreno sobre el nivel del mar en metros.
            factor_altitud: Factor de altitud Ke explícito. Si es None, se calcula a partir de altitud.
        """
        self.profundidad = profundidad
        self.ancho = ancho
        self.altura_inferior = altura_inferior
        self.altura_superior = altura_superior
        self.velocidad = velocidad
        self.categoria = categoria
        self.factor_g_simplificado = factor_g_simplificado
        self.considerar_topografia = considerar_topografia
        self.categoria_exp = categoria_exp
        self.es_parapeto = es_parapeto
        self.epsilon = epsilon
        self.doble_cara = doble_cara
        self.esquina_retorno = esquina_retorno
        self.frecuencia = frecuencia
        self.beta = beta
        self.flexibilidad = flexibilidad
        self.tipo_terreno = tipo_terreno
        self.altura_terreno = altura_terreno
        self.distancia_cresta = distancia_cresta
        self.distancia_barlovento_sotavento = distancia_barlovento_sotavento
        self.direccion = direccion
        self.altitud = altitud
        self.factor_altitud = (
            factores.factor_altitud(altitud)
            if factor_altitud is None
            else factor_altitud
        )

        self.geometria = geometria.Cartel(
            profundidad, ancho, altura_inferior, altura_superior
        )
        self.cf = cp.Cartel.desde_cartel(
            self.geometria,
            es_parapeto,
            epsilon,
            doble_cara,
            esquina_retorno,
        )
        self.rafaga = Rafaga(
            ancho,
            profundidad,
            altura_superior,
            self.geometria.altura_media,
            velocidad,
            frecuencia,
            beta,
            flexibilidad,
            factor_g_simplificado,
            categoria_exp,
        )
        self.topografia = Topografia(
            categoria_exp,
            considerar_topografia,
            tipo_terreno,
            altura_terreno,
            distancia_cresta,
            distancia_barlovento_sotavento,
            direccion,
            self.geometria.alturas,
        )
        self.presiones = presiones.Cartel.desde_cartel(
            self.geometria,
            categoria,
            velocidad,
            self.rafaga,
            self.topografia.factor[0],
            self.cf,
            categoria_exp,
            factor_altitud=self.factor_altitud,
        )

    @cached_property
    def resultados(self) -> Tabla[FilaCartel]:
        """La tabla de resultados del cartel.

        Returns:
            Una fila por cada caso de la Figura 4.4-1 y, para el Caso C, una
            fila por región.
        """
        return resultados.Tabla(self.presiones.filas)


class CubiertaAislada:
    """CubiertaAislada.

    Calcula las presiones sobre una cubierta aislada y todos sus respectivos parámetros de acuerdo a los lineamiento del
    Reglamento CIRSOC 102-2025.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        altura_alero: float,
        altura_cumbrera: float,
        altura_bloqueo: float,
        posicion_bloqueo: PosicionBloqueoCubierta,
        tipo_cubierta: TipoCubierta,
        coeficiente_friccion: float,
        velocidad: float,
        categoria: CategoriaEstructura,
        categoria_exp: CategoriaExposicion,
        considerar_topografia: bool,
        frecuencia: float = 1,
        beta: float = 0.02,
        flexibilidad: Flexibilidad = Flexibilidad.RIGIDA,
        tipo_terreno: TipoTerrenoTopografia = TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno: float = 50,
        distancia_cresta: float = 50,
        distancia_barlovento_sotavento: float = 50,
        direccion: DireccionTopografia = DireccionTopografia.BARLOVENTO,
        altitud: float = 0,
        factor_altitud: float | None = None,
    ) -> None:
        """

        Args:
            ancho: El ancho de la cubierta.
            longitud: La longitud de la cubierta.
            altura_alero: La altura de alero de la cubierta, medida desde el nivel de suelo.
            altura_cumbrera: La altura de cumbrera de la cubierta, medida desde el nivel de suelo.
            altura_bloqueo: La altura de bloqueo. Se utiliza en el caso de cubiertas aisladas. Se necesita cuando se usa
                la cubierta para calcular los coeficientes de presión de cubiertas aisladas.
            posicion_bloqueo: La posicion de bloqueo. Se utiliza en el caso de cubiertas aisladas a un agua.
            tipo_cubierta: El tipo de cubierta.
            coeficiente_friccion: El coeficiente de friccion de la superficie de cubierta.
            velocidad: La velocidad del viento en m/s.
            categoria: La categoría de la estructura.
            categoria_exp: La categoría de exposición al viento de la estructura.
            considerar_topografia: indica si se tiene que calcular la topografia.
            frecuencia: La frecuencia natural de la estructura en hz.
            beta: La relación de amortiguamiento crítico.
            flexibilidad: La flexibilidad de la estructura.
            tipo_terreno: El tipo de terreno.
            altura_terreno: La altura de la colina o escarpa.
            distancia_cresta: La distancia en la dirección de barlovento, medida desde la cresta de la colina o escarpa.
            distancia_barlovento_sotavento: Distancia tomada desde la cima, en la dirección de barlovento o de sotavento.
            direccion: La direccion para la el parámetro `distancia_barlovento_sotavento`.
            altitud: Altitud del terreno sobre el nivel del mar en metros.
            factor_altitud: Factor de altitud Ke explícito. Si es None, se calcula a partir de altitud.
        """
        self.ancho = ancho
        self.longitud = longitud
        self.altura_alero = altura_alero
        self.altura_cumbrera = altura_cumbrera
        self.altura_bloqueo = altura_bloqueo
        self.posicion_bloqueo = posicion_bloqueo
        self.tipo_cubierta = tipo_cubierta
        self.coeficiente_friccion = coeficiente_friccion
        self.velocidad = velocidad
        self.categoria = categoria
        self.categoria_exp = categoria_exp
        self.considerar_topografia = considerar_topografia
        self.frecuencia = frecuencia
        self.beta = beta
        self.flexibilidad = flexibilidad
        self.tipo_terreno = tipo_terreno
        self.altura_terreno = altura_terreno
        self.distancia_cresta = distancia_cresta
        self.distancia_barlovento_sotavento = distancia_barlovento_sotavento
        self.direccion = direccion
        self.altitud = altitud
        self.factor_altitud = (
            factores.factor_altitud(altitud)
            if factor_altitud is None
            else factor_altitud
        )
        self.geometria = geometria.Cubierta(
            ancho,
            longitud,
            altura_alero,
            altura_cumbrera,
            tipo_cubierta,
            altura_bloqueo=altura_bloqueo,
            posicion_bloqueo=posicion_bloqueo,
        )
        self.cpn = cp.CubiertaAislada.desde_cubierta(self.geometria)
        self.rafaga = Rafaga(
            ancho,
            longitud,
            self.geometria.altura_media,
            self.geometria.altura_media,
            velocidad,
            frecuencia,
            beta,
            flexibilidad,
            True,
            categoria_exp,
        )
        self.topografia = Topografia(
            categoria_exp,
            considerar_topografia,
            tipo_terreno,
            altura_terreno,
            distancia_cresta,
            distancia_barlovento_sotavento,
            direccion,
            self.geometria.altura_media,
        )
        self.presiones = presiones.CubiertaAislada.desde_cubierta(
            self.geometria,
            categoria,
            velocidad,
            self.rafaga,
            self.topografia.factor,
            self.cpn,
            categoria_exp,
            coeficiente_friccion,
            factor_altitud=self.factor_altitud,
        )

    @cached_property
    def resultados(self) -> Tabla[FilaCubiertaAislada]:
        """La tabla de resultados de la cubierta aislada.

        Returns:
            Una fila por cada combinación de tipo de presión, zona y extremo.
        """
        return resultados.Tabla(self.presiones.filas)


class Edificio:
    """Edificio.

    Calcula las presiones sobre un edificio y todos sus respectivos parámetros de acuerdo a los lineamiento del
    Reglamento CIRSOC 102-2025.
    """

    def __init__(
        self,
        ancho: float,
        longitud: float,
        elevacion: float,
        altura_alero: float,
        altura_cumbrera: float,
        tipo_cubierta: TipoCubierta,
        cerramiento: Cerramiento,
        categoria: CategoriaEstructura,
        velocidad: float,
        factor_g_simplificado: bool,
        categoria_exp: CategoriaExposicion,
        considerar_topografia: bool,
        parapeto=0,
        alero=0,
        reducir_gcpi=False,
        metodo_sprfv: MetodoSprfv = MetodoSprfv.DIRECCIONAL,
        alturas_personalizadas: Sequence[float] | None = None,
        aberturas: tuple[float, float, float, float, float] | None = None,
        volumen_interno: float | None = None,
        frecuencia: float = 1,
        beta: float = 0.02,
        flexibilidad: Flexibilidad = Flexibilidad.RIGIDA,
        tipo_terreno: TipoTerrenoTopografia = TipoTerrenoTopografia.LOMA_BIDIMENSIONAL,
        altura_terreno: float = 50,
        distancia_cresta: float = 50,
        distancia_barlovento_sotavento: float = 50,
        direccion: DireccionTopografia = DireccionTopografia.BARLOVENTO,
        componentes_paredes: dict[str, float] | None = None,
        componentes_cubierta: dict[str, float] | None = None,
        altitud: float = 0,
        factor_altitud: float | None = None,
    ) -> None:
        self.ancho = ancho
        self.longitud = longitud
        self.elevacion = elevacion
        self.altura_alero = altura_alero
        self.altura_cumbrera = altura_cumbrera
        if tipo_cubierta == TipoCubierta.PLANA:
            altura_cumbrera = altura_alero
        self.tipo_cubierta = tipo_cubierta
        self.cerramiento = cerramiento
        self.categoria = categoria
        self.velocidad = velocidad
        self.factor_g_simplificado = factor_g_simplificado
        self.categoria_exp = categoria_exp
        self.considerar_topografia = considerar_topografia
        self.parapeto = parapeto
        self.alero = alero
        self.reducir_gcpi = reducir_gcpi
        self.metodo_sprfv = metodo_sprfv
        self.alturas_personalizadas = alturas_personalizadas
        self.aberturas = aberturas
        self.volumen_interno = volumen_interno
        self.frecuencia = frecuencia
        self.beta = beta
        self.flexibilidad = flexibilidad
        self.tipo_terreno = tipo_terreno
        self.altura_terreno = altura_terreno
        self.distancia_cresta = distancia_cresta
        self.distancia_barlovento_sotavento = distancia_barlovento_sotavento
        self.direccion = direccion
        self.componentes_paredes = componentes_paredes
        self.componentes_cubierta = componentes_cubierta
        self.altitud = altitud
        self.factor_altitud = (
            factores.factor_altitud(altitud)
            if factor_altitud is None
            else factor_altitud
        )

        self.geometria = geometria.Edificio(
            ancho,
            longitud,
            elevacion,
            altura_alero,
            altura_cumbrera,
            tipo_cubierta,
            parapeto,
            alero,
            alturas_personalizadas,
            volumen_interno,
            aberturas,
        )
        self.cp = cp.Edificio.desde_geometria_edifico(
            self.geometria,
            metodo_sprfv,
            componentes_paredes=componentes_paredes,
            componentes_cubierta=componentes_cubierta,
        )
        self.rafaga = Rafaga.desde_edificio_metodo_direccional(
            self.geometria,
            velocidad,
            frecuencia,
            beta,
            flexibilidad,
            factor_g_simplificado,
            categoria_exp,
        )
        self.topografia = Topografia(
            categoria_exp,
            considerar_topografia,
            tipo_terreno,
            altura_terreno,
            distancia_cresta,
            distancia_barlovento_sotavento,
            direccion,
            self.geometria.alturas,
        )
        self.presiones = presiones.Edificio.desde_edificio(
            self.geometria,
            self.cp,
            categoria,
            velocidad,
            self.rafaga,
            self.topografia.factor,
            cerramiento,
            categoria_exp,
            reducir_gcpi,
            metodo_sprfv,
            factor_altitud=self.factor_altitud,
        )

    @cached_property
    def resultados_sprfv(self) -> Tabla[FilaEdificio]:
        """La tabla de resultados del SPRFV.

        Returns:
            Las filas de paredes, cubierta y alero.
        """
        return resultados.Tabla(self.presiones.filas_sprfv)

    @cached_property
    def resultados_componentes(self) -> Tabla[FilaEdificio]:
        """La tabla de resultados de componentes y revestimientos.

        Se calcula por separado del SPRFV porque el Reglamento puede no proveer
        lineamientos para la geometría del edificio, y en ese caso los
        resultados del SPRFV siguen siendo válidos.

        Returns:
            Las filas de paredes, cubierta y alero.

        Raises:
            ErrorLineamientos: Cuando la geometría excede el alcance del
                Reglamento para componentes y revestimientos.
        """
        return resultados.Tabla(self.presiones.filas_componentes)

    @cached_property
    def resultados(self) -> Tabla[FilaEdificio]:
        """La tabla completa de resultados del edificio.

        Returns:
            Las filas del SPRFV seguidas por las de componentes.
        """
        return self.resultados_sprfv + self.resultados_componentes
