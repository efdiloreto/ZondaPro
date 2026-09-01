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

"""Contiene clases destinadas a representar las escenas para las diferentes configuraciones de un edificio. Estas escenas
interactuan con los directores para actualizar su vista dependiendo de diferentes factores.

Las presiones se leen de la tabla de resultados del núcleo: cada actor busca su
fila por clave, en vez de recorrer una estructura anidada cuya forma dependía de
las condicionales del Reglamento.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from zonda.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    ParedEdificioSprfv,
    PosicionCubiertaAleroSprfv,
    TipoCubierta,
    TipoPresionComponentesParedesCubierta,
    TipoPresionCubiertaBarloventoSprfv,
    ZonaComponenteCubiertaEdificio,
    ZonaComponenteParedEdificio,
    ZonaEdificio,
)
from zonda.graficos.actores import ActorBarraEscala, ActorTexto2D
from zonda.graficos.colores import TablaColores
from zonda.graficos.directores import edificio as directores_edificio
from zonda.graficos.directores.utils_iter import aplicar_func_recursivamente
from zonda.graficos.escenas.base import PresionesMixin
from zonda.unidades import convertir_unidad

if TYPE_CHECKING:
    from zonda.cirsoc import Edificio
    from zonda.cirsoc.resultados import FilaEdificio
    from zonda.enums import Unidad
    from zonda.graficos.escena import Escena3D


class PresionesSprfvMetodoDireccional(PresionesMixin):
    """PresionesSprfvMetodoDireccional.

    Representa la escena de la visualización de presiones del viento sobre el SPRFV un edificio utilizando el método
    direccional.
    """

    def __init__(
        self,
        escena: Escena3D,
        edificio: Edificio,
        unidad: Unidad,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores y los publica a la vista.
            edificio: Una instancia de Edificio.
            unidad: La unidad en las que se muestran las presiones.
        """
        self.escena = escena
        self.unidad = unidad

        self.alturas_presiones_frente = edificio.geometria.alturas.tolist()
        self.alturas_presiones_lateral = edificio.geometria.alturas_alero.tolist()

        resultados = edificio.resultados_sprfv

        self._paredes = resultados.filtrar(zona=ZonaEdificio.PAREDES).indexar(
            "direccion", "pared"
        )
        self._cubierta = resultados.filtrar(zona=ZonaEdificio.CUBIERTA).indexar(
            "direccion", "posicion", "caso"
        )
        self._alero = resultados.filtrar(zona=ZonaEdificio.ALERO).indexar(
            "direccion", "posicion", "caso"
        )

        # La pared a barlovento tiene una presión por altura.
        self._barlovento_por_altura = {
            direccion: {fila.q.altura: fila for fila in filas}
            for (direccion, pared), filas in self._paredes.items()
            if pared is ParedEdificioSprfv.BARLOVENTO
        }

        tabla_colores = TablaColores(
            *(
                convertir_unidad(presion, self.unidad)
                for presion in resultados.min_max()
            )
        )

        self._barra_escala = ActorBarraEscala(self.escena, tabla_colores, self.unidad)

        self._titulo = ActorTexto2D(self.escena)

        self.director = directores_edificio.PresionesSprfvMetodoDireccional(
            self.escena, tabla_colores, edificio
        )

        # Preseteo de alturas barlovento iniciales. Como todos los parametros son definidos inicialmente por el metodo
        # "cambiar_direccion_viento" es necesario esten asignadas estas alturas para poder actualizar la pared barlovento.

        self.alturas_presion_barlovento = {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: self.alturas_presiones_frente[
                -1
            ]
        }
        posicion_cubierta_un_agua = getattr(
            self.director, "posicion_cubierta_un_agua", None
        )
        if posicion_cubierta_un_agua is not None:
            self._posicion_cubierta_un_agua_actual = posicion_cubierta_un_agua
            self.alturas_presion_barlovento[
                DireccionVientoMetodoDireccionalSprfv.NORMAL
            ] = {
                PosicionCubiertaAleroSprfv.SOTAVENTO: self.alturas_presiones_frente[-1],
                PosicionCubiertaAleroSprfv.BARLOVENTO: self.alturas_presiones_lateral[
                    -1
                ],
            }
        else:
            self.alturas_presion_barlovento[
                DireccionVientoMetodoDireccionalSprfv.NORMAL
            ] = self.alturas_presiones_lateral[-1]

        # Preseteo del indice de la presión interna actual (0 es positivo y 1 es negativo)
        self._gcpi_actual = 0
        self._textos_presion_interna = ("+", "-")

        # Preseteo del caso a cubierta barlovento con angulo > 10°.
        self._tipo_presion_cubierta_barlovento = (
            TipoPresionCubiertaBarloventoSprfv.NEGATIVA
        )

        if hasattr(self.director, "posicion_cubierta_un_agua"):
            self._posicion_cubierta_un_agua_actual = (
                self.director.posicion_cubierta_un_agua
            )

        # Inicialización de variables internas que serán actualizadas cuando los métodos correspondientes sean llamados.
        self._actores_actuales_paredes = self._actores_actuales_cubierta = None
        self._direccion_actual = None
        if self._alero:
            self._actores_actuales_alero = None
        self._alturas_actuales_presion_barlovento = None

        self._actores_presion = self.escena.actores_presion

    def actualizar_gcpi(self, indice_gcpi: int) -> None:
        """Actualiza el factor de presión interna actual para todos los actores.

        Args:
            indice_gcpi: 0 es presión interna positiva y 1 es presión interna negativa.
        """
        self._gcpi_actual = indice_gcpi
        self._actualizar_paredes_sotavento_lateral()
        self._actualizar_cubierta()
        self._actualizar_titulo()

    def actualizar_direccion_viento(
        self, direccion: DireccionVientoMetodoDireccionalSprfv
    ) -> None:
        """Actualiza la dirección del viento actual y los actores de la escena para esa dirección.

        Args:
            direccion: La dirección a la que se actualiza la escena.
        """
        self._direccion_actual = direccion
        self.director.direccion = direccion
        self._alturas_actuales_presion_barlovento = self.alturas_presion_barlovento[
            direccion
        ]
        self._actualizar_paredes_sotavento_lateral(regenerar_actores=True)
        self._actualizar_cubierta(regenerar_actores=True)
        if self._alero:
            self._actualizar_alero(regenerar_actores=True)
        self._actualizar_titulo()

    def actualizar_posicion_cubierta_un_agua(
        self, posicion: PosicionCubiertaAleroSprfv
    ) -> None:
        """Actualiza las presiones de la cubierta a un agua respecto para la nueva posición respecto al viento.

        Se debe utilizar cuando el tipo de cubierta es a un agua y la dirección del viento es normal a la cumbrera.

        Args:
            posicion: La posición de la cubierta respecto al viento para la que se actualizan las presiones.
        """
        self.director.posicion_cubierta_un_agua = (
            self._posicion_cubierta_un_agua_actual
        ) = posicion
        self._actualizar_paredes_sotavento_lateral(regenerar_actores=True)

        # Si la cubierta con viento normal se comporta como paralelo (angulo < 10°), se tienen que regenerar los actores
        # de cubierta ya que cambian las zonas.
        self._actualizar_cubierta(
            regenerar_actores=self._esta_zonificada(self._cubierta)
        )
        if self._alero:
            self._actualizar_alero()
        self._actualizar_titulo()

    def actualizar_presion_cubierta_inclinada(
        self, presion: TipoPresionCubiertaBarloventoSprfv
    ) -> None:
        """Actualiza las presiones del faldón de cubierta que corresponde a la posición de barlovento respecto al viento.

        Se debe utilizar cuando el tipo de cubierta es a un agua o dos aguas, el angulo de la misma es >=10° y
        la dirección del viento es normal a la cumbrera.

        Args:
            presion: La presión al que se actualiza la presión de la cubierta a barlovento.
        """
        self._tipo_presion_cubierta_barlovento = presion
        self._actualizar_cubierta()
        if self._alero:
            self._actualizar_alero()
        self._actualizar_titulo()

    def actualizar_altura_pared_barlovento(self, altura) -> None:
        """Actualiza la altura a la que se calcula la presión sobre la pared a barlovento.

        Args:
            altura: La altura a la que actualizar la presión.
        """
        actor = self._actores_actuales_paredes[ParedEdificioSprfv.BARLOVENTO]
        if (
            self._direccion_actual == DireccionVientoMetodoDireccionalSprfv.NORMAL
            and hasattr(self, "_posicion_cubierta_un_agua_actual")
        ):
            self.alturas_presion_barlovento[self._direccion_actual][
                self._posicion_cubierta_un_agua_actual
            ] = altura
        else:
            self.alturas_presion_barlovento[self._direccion_actual] = altura
        fila = self._barlovento_por_altura[self._direccion_actual][altura]
        actor.asignar_presion(
            fila.presion(self._gcpi_actual),
            str_extra=f"({altura:.2f} m)",
            unidad=self.unidad,
        )

    def _esta_zonificada(self, indice: dict) -> bool:
        """Indica si la superficie está dividida en zonas para la dirección actual.

        Es lo que antes se preguntaba al cálculo con ``normal_como_paralelo``:
        ahora se desprende de las claves de las propias filas.

        Args:
            indice: El índice de filas de la superficie.

        Returns:
            True si hay filas por zona en vez de por posición.
        """
        return (self._direccion_actual, None, None) in indice

    def _fila_superficie(
        self, indice: dict, posicion: PosicionCubiertaAleroSprfv
    ) -> FilaEdificio:
        """La fila de una posición de cubierta o alero para la dirección actual.

        Args:
            indice: El índice de filas de la superficie.
            posicion: La posición respecto al viento.

        Returns:
            La fila correspondiente. Si la superficie a barlovento tiene dos
            casos de presión, se devuelve la del caso actual.
        """
        clave = (self._direccion_actual, posicion, None)
        if clave not in indice:
            clave = (
                self._direccion_actual,
                posicion,
                self._tipo_presion_cubierta_barlovento,
            )
        return indice[clave].unica()

    def _actualizar_paredes_sotavento_lateral(self, regenerar_actores=False) -> None:
        """Actualiza los actores y presiones para las paredes sotavento y laterales.

        Args:
            regenerar_actores: Indica si los actores deben ser regenerados. Si es False, los actores no se cambian pero
            se actualiza la presión sobre los mismos.
        """
        if regenerar_actores:
            if self._actores_actuales_paredes is not None:
                aplicar_func_recursivamente(
                    self._actores_actuales_paredes, lambda _actor: _actor.ocultar()
                )
            self._actores_actuales_paredes = self.director.obtener_paredes()
        for pared, actores in self._actores_actuales_paredes.items():
            if pared == ParedEdificioSprfv.BARLOVENTO:
                if regenerar_actores:
                    actores.mostrar()
                continue
            fila = self._paredes[(self._direccion_actual, pared)].unica()
            presion = fila.presion(self._gcpi_actual)
            if pared == ParedEdificioSprfv.LATERAL:
                for actor in actores:
                    actor.asignar_presion(presion, unidad=self.unidad)
            else:
                actores.asignar_presion(presion, unidad=self.unidad)

    def _actualizar_cubierta(self, regenerar_actores=False) -> None:
        """Actualiza los actores y presiones para la cubierta.

        Args:
            regenerar_actores: Indica si los actores deben ser regenerados. Si es False, los actores no se cambian pero
            se actualiza la presión sobre los mismos.
        """
        if regenerar_actores:
            if self._actores_actuales_cubierta is not None:
                aplicar_func_recursivamente(
                    self._actores_actuales_cubierta, lambda actor: actor.ocultar()
                )
            self._actores_actuales_cubierta = self.director.obtener_cubierta()
        if self._esta_zonificada(self._cubierta):
            filas = self._cubierta[(self._direccion_actual, None, None)]
            for i, fila in enumerate(filas):
                presion = fila.presion(self._gcpi_actual)
                try:
                    # Cubierta a dos aguas: cada zona tiene barlovento y sotavento.
                    for actores in self._actores_actuales_cubierta.values():
                        actores[i].asignar_presion(presion, unidad=self.unidad)
                except AttributeError:
                    self._actores_actuales_cubierta[i].asignar_presion(
                        presion, unidad=self.unidad
                    )
            return
        if self.director.tipo_cubierta == TipoCubierta.UN_AGUA:
            fila = self._fila_superficie(
                self._cubierta, self._posicion_cubierta_un_agua_actual
            )
            self._actores_actuales_cubierta.asignar_presion(
                fila.presion(self._gcpi_actual), unidad=self.unidad
            )
            return
        for posicion, actor in self._actores_actuales_cubierta.items():
            fila = self._fila_superficie(self._cubierta, posicion)
            actor.asignar_presion(fila.presion(self._gcpi_actual), unidad=self.unidad)

    def _actualizar_alero(self, regenerar_actores=False) -> None:
        """Actualiza los actores y presiones para los aleros.

        El alero es una superficie abierta: no lleva presión interna, así que la
        presión no depende del GC~pi~ actual.

        Args:
            regenerar_actores: Indica si los actores deben ser regenerados. Si es False, los actores no se cambian pero
            se actualiza la presión sobre los mismos.
        """
        if regenerar_actores:
            if self._actores_actuales_alero is not None:
                aplicar_func_recursivamente(
                    self._actores_actuales_alero, lambda x: x.ocultar()
                )
            self._actores_actuales_alero = self.director.obtener_alero()
        if self._esta_zonificada(self._alero):
            filas = self._alero[(self._direccion_actual, None, None)]
            for i, fila in enumerate(filas):
                for alero in self._actores_actuales_alero.values():
                    alero[i].asignar_presion(fila.pos, unidad=self.unidad)
            return
        if self.director.tipo_cubierta == TipoCubierta.UN_AGUA:
            fila = self._fila_superficie(
                self._alero, self._posicion_cubierta_un_agua_actual
            )
            self._actores_actuales_alero.asignar_presion(fila.pos, unidad=self.unidad)
            return
        for posicion, actor in self._actores_actuales_alero.items():
            fila = self._fila_superficie(self._alero, posicion)
            actor.asignar_presion(fila.pos, unidad=self.unidad)

    def _actualizar_titulo(self) -> None:
        """Actualiza el título de la escena."""
        texto = f"Viento {self._direccion_actual.value.capitalize()} a la Cumbrera"
        texto += f" ({self._textos_presion_interna[self._gcpi_actual]}GCpi)"
        if self._direccion_actual == DireccionVientoMetodoDireccionalSprfv.NORMAL:
            posicion_cubierta_un_agua = getattr(
                self, "_posicion_cubierta_un_agua_actual", None
            )
            if posicion_cubierta_un_agua is not None:
                texto += f" - Cubierta a {posicion_cubierta_un_agua.value.capitalize()}"
            if posicion_cubierta_un_agua != PosicionCubiertaAleroSprfv.SOTAVENTO:
                caso_cubierta_barlovento = getattr(
                    self, "_caso_cubierta_barlovento", None
                )
                if caso_cubierta_barlovento is not None:
                    texto += f" - Caso {self._tipo_presion_cubierta_barlovento.value}"

        self._titulo.setear_texto(texto)


class PresionesComponentes(PresionesMixin):
    """PresionesComponentes.

    Representa la escena de la visualización de presiones del viento sobre los componentes y revestimientos de un
    edificio.
    """

    def __init__(
        self,
        escena: Escena3D,
        edificio: Edificio,
        unidad: Unidad,
    ) -> None:
        """

        Args:
            escena: La escena que junta los actores y los publica a la vista.
            edificio: Una instancia de Edificio.
            unidad: La unidad en las que se muestran las presiones.
        """
        self.escena = escena
        self.unidad = unidad

        self._componentes_paredes = edificio.componentes_paredes
        self._componentes_cubierta = edificio.componentes_cubierta

        resultados = edificio.resultados_componentes
        filas_paredes = resultados.filtrar(zona=ZonaEdificio.PAREDES)
        filas_cubierta = resultados.filtrar(zona=ZonaEdificio.CUBIERTA)
        filas_alero = resultados.filtrar(zona=ZonaEdificio.ALERO)

        # Con la Figura 8 del Reglamento los valores dependen además de la pared,
        # y los de la pared a barlovento varían con la altura.
        self._por_pared = any(fila.pared for fila in filas_paredes)

        self._paredes = filas_paredes.indexar("pared", "componente", "zona_componente")
        self._cubierta = filas_cubierta.indexar("componente", "zona_componente")
        self._alero = filas_alero.indexar("componente", "zona_componente")

        self._barlovento_por_altura = {
            (componente, zona_componente): {fila.q.altura: fila for fila in filas}
            for (pared, componente, zona_componente), filas in self._paredes.items()
            if pared is ParedEdificioSprfv.BARLOVENTO
        }

        tabla_colores = TablaColores(
            *(
                convertir_unidad(presion, self.unidad)
                for presion in resultados.min_max()
            )
        )

        self._barra_escala = ActorBarraEscala(self.escena, tabla_colores, self.unidad)

        self._titulo = ActorTexto2D(self.escena)

        self.director = directores_edificio.PresionesComponentes(
            self.escena, tabla_colores, edificio
        )

        self._actores_paredes = self.director.obtener_paredes()
        if not filas_paredes:
            aplicar_func_recursivamente(
                self._actores_paredes, lambda actor: actor.flecha.ocultar()
            )

        self._actores_cubierta = self.director.obtener_cubierta()
        if not filas_cubierta:
            aplicar_func_recursivamente(
                self._actores_cubierta, lambda actor: actor.flecha.ocultar()
            )

        self._actores_alero = self.director.obtener_alero()
        if not filas_alero and self._actores_alero is not None:
            aplicar_func_recursivamente(
                self._actores_alero, lambda actor: actor.flecha.ocultar()
            )

        self._gcpi_actual = 0
        self._textos_presion_interna = ("+", "-")

        self._tipo_presion_componente_actual = (
            TipoPresionComponentesParedesCubierta.NEGATIVA
        )
        self._componente_actual_pared = self._componente_actual_cubierta = None

        self._actores_presion = self.escena.actores_presion

    def actualizar_gcpi(self, indice_gcpi: int) -> None:
        """Actualiza el factor de presión interna actual para todos los actores.

        Args:
            indice_gcpi: 0 es presión interna positiva y 1 es presión interna negativa.
        """
        self._gcpi_actual = indice_gcpi
        if self._componentes_paredes is not None:
            self._actualizar_paredes()
        if self._componentes_cubierta is not None:
            self._actualizar_cubierta()
        self._actualizar_titulo()

    def actualizar_tipo_presion(
        self, tipo_presion: TipoPresionComponentesParedesCubierta
    ) -> None:
        """Actualiza el tipo de presión para los actores de paredes y cubierta.

        Args:
            tipo_presion: El tipo de presión a actualizar.
        """
        self._tipo_presion_componente_actual = tipo_presion
        if self._componentes_paredes is not None:
            self._actualizar_paredes()
        if self._componentes_cubierta is not None:
            self._actualizar_cubierta()
        self._actualizar_titulo()

    def actualizar_componente_pared(self, componente: str) -> None:
        """Actualiza el componente para las paredes.

        Args:
            componente: El nombre del componente.
        """
        self._componente_actual_pared = componente
        self._actualizar_paredes()
        self._actualizar_titulo()

    def actualizar_componente_cubierta(self, componente: str) -> None:
        """Actualiza el componente para la cubierta.

        Args:
            componente: El nombre del componente.
        """
        self._componente_actual_cubierta = componente
        self._actualizar_cubierta()
        if self._alero:
            self._actualizar_alero()
        self._actualizar_titulo()

    def actualizar_altura_pared_barlovento(self, altura) -> None:
        """Actualiza la altura a la que se calcula la presión sobre la pared a barlovento.

        Args:
            altura: La altura a la que actualizar la presión.
        """
        pared = self._actores_paredes[ParedEdificioSprfv.BARLOVENTO]
        for zona, actores in pared.items():
            filas = self._barlovento_por_altura.get(
                (self._componente_actual_pared, self._zona_pared(zona))
            )
            if filas is None:
                continue
            presion = filas[altura].presion(self._gcpi_actual)
            if zona == ZonaComponenteParedEdificio.CINCO:
                for actor in actores:
                    actor.asignar_presion(
                        presion=presion, str_extra=f"({altura} m)", unidad=self.unidad
                    )
            else:
                actores.asignar_presion(
                    presion=presion, str_extra=f"({altura} m)", unidad=self.unidad
                )

    @staticmethod
    def _pared_de_actores(clave: ParedEdificioSprfv | str) -> ParedEdificioSprfv:
        """La pared del Reglamento que corresponde a un grupo de actores.

        El director separa las dos paredes laterales para poder ubicarlas en la
        escena, pero el Reglamento les asigna un único valor.

        Args:
            clave: La clave con la que el director agrupa los actores.

        Returns:
            La pared del Reglamento.
        """
        if isinstance(clave, ParedEdificioSprfv):
            return clave
        return ParedEdificioSprfv.LATERAL

    def _zona_pared(
        self, zona: ZonaComponenteParedEdificio
    ) -> ZonaComponenteParedEdificio:
        """La zona de la que se toma el valor para el tipo de presión actual.

        La presión positiva es la misma para todas las zonas de la pared.

        Args:
            zona: La zona del actor.

        Returns:
            La zona de la que se lee el valor.
        """
        if (
            self._tipo_presion_componente_actual
            is TipoPresionComponentesParedesCubierta.POSITIVA
        ):
            return ZonaComponenteParedEdificio.TODAS
        return zona

    def _zona_cubierta(
        self, zona: ZonaComponenteCubiertaEdificio
    ) -> ZonaComponenteCubiertaEdificio:
        """La zona de la que se toma el valor para el tipo de presión actual.

        Args:
            zona: La zona del actor.

        Returns:
            La zona de la que se lee el valor.
        """
        if (
            self._tipo_presion_componente_actual
            is TipoPresionComponentesParedesCubierta.POSITIVA
        ):
            return ZonaComponenteCubiertaEdificio.TODAS
        return zona

    def _actualizar_paredes(self) -> None:
        """Actualiza las presiones de los actores de paredes."""
        for clave_actores, zonas in self._actores_paredes.items():
            pared = self._pared_de_actores(clave_actores)
            if self._por_pared and pared is ParedEdificioSprfv.BARLOVENTO:
                # Se actualiza por altura, desde actualizar_altura_pared_barlovento.
                continue
            for zona, actores in zonas.items():
                clave = (
                    pared if self._por_pared else None,
                    self._componente_actual_pared,
                    self._zona_pared(zona),
                )
                filas = self._paredes.get(clave)
                if filas is None:
                    continue
                presion = filas.unica().presion(self._gcpi_actual)
                if zona == ZonaComponenteParedEdificio.CINCO:
                    for actor in actores:
                        actor.asignar_presion(presion=presion, unidad=self.unidad)
                else:
                    actores.asignar_presion(presion=presion, unidad=self.unidad)

    def _actualizar_cubierta(self) -> None:
        """Actualiza las presiones de los actores de cubierta."""
        for zona, actores in self._actores_cubierta.items():
            filas = self._cubierta.get(
                (self._componente_actual_cubierta, self._zona_cubierta(zona))
            )
            if filas is None:
                continue
            presion = filas.unica().presion(self._gcpi_actual)
            try:
                for actor in actores:
                    actor.asignar_presion(presion=presion, unidad=self.unidad)
            except TypeError:
                actores.asignar_presion(presion=presion, unidad=self.unidad)

    def _actualizar_alero(self) -> None:
        """Actualiza las presiones de los actores del alero.

        El alero no lleva presión interna ni valor de presión positiva: cada
        zona muestra su propio valor.
        """
        for zona, actores in self._actores_alero.items():
            filas = self._alero.get((self._componente_actual_cubierta, zona))
            if filas is None:
                continue
            presion = filas.unica().pos
            try:
                for actor in actores:
                    actor.asignar_presion(presion, unidad=self.unidad)
            except TypeError:
                actores.asignar_presion(presion, unidad=self.unidad)

    def _actualizar_titulo(self) -> None:
        """Actualiza el título de la escena."""
        texto = f"Presión {self._tipo_presion_componente_actual.value.capitalize()}"
        if (
            self._por_pared
            and self._tipo_presion_componente_actual
            == TipoPresionComponentesParedesCubierta.POSITIVA
        ):
            texto = (
                "("
                + texto
                + f" Paredes / Presión {TipoPresionComponentesParedesCubierta.NEGATIVA.value.capitalize()} Cubierta)"
            )
        texto += f" ({self._textos_presion_interna[self._gcpi_actual]}GCpi)"
        if self._componente_actual_pared is not None:
            texto += f" - Componente Pared: {self._componente_actual_pared} ({self._componentes_paredes[self._componente_actual_pared]} m2)"
        if self._componente_actual_cubierta is not None:
            texto += f" - Componente Cubierta: {self._componente_actual_cubierta} ({self._componentes_cubierta[self._componente_actual_cubierta]} m2)"

        self._titulo.setear_texto(texto)
