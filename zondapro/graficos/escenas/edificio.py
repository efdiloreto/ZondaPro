"""Contiene clases destinadas a representar las escenas para las diferentes configuraciones de un edificio. Estas escenas
interactuan con los directores para actualizar su vista dependiendo de diferentes factores.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple

from vtkmodules import all as vtk

from zondapro.enums import (
    DireccionVientoMetodoDireccionalSprfv,
    TipoCubierta,
    TipoPresionCubiertaBarloventoSprfv,
    ParedEdificioSprfv,
    PosicionCubiertaAleroSprfv,
    TipoPresionComponentesParedesCubierta,
    ZonaComponenteParedEdificio,
    ZonaComponenteCubiertaEdificio,
)
from zondapro.graficos.actores import ActorBarraEscala, ActorTexto2D, ActorPresion
from zondapro.graficos.directores import edificio as directores_edificio
from zondapro.graficos.directores.utils_iter import min_max_valores, aplicar_func_recursivamente
from zondapro.graficos.escenas.base import PresionesMixin
from zondapro.unidades import convertir_unidad

if TYPE_CHECKING:
    from zondapro.cirsoc import Edificio
    from zondapro.cirsoc.presiones.edificio import PresionesEdificio
    from zondapro.enums import Unidad


def obtener_actores_presion_en_renderer(renderer: vtk.vtkRenderer) -> Tuple[ActorPresion, ...]:
    """Obtiene todos los actores de presión presentes en el renderer."""
    return tuple(
        actor for actor in renderer.GetActors() if isinstance(actor, ActorPresion) and hasattr(actor, "flecha")
    )


class PresionesSprfvMetodoDireccional(PresionesMixin):
    """PresionesSprfvMetodoDireccional.

    Representa la escena de la visualización de presiones del viento sobre el SPRFV un edificio utilizando el método
    direccional.
    """

    def __init__(
        self, interactor: vtk.vtkRenderWindowInteractor, renderer: vtk.vtkRenderer, edificio: Edificio, unidad: Unidad
    ) -> None:
        """

        Args:
            interactor: El interactor de la ventana de visualización.
            renderer: El renderer utilizado para renderizar los actores en la escena.
            edificio: Una instancia de Edificio.
            unidad: La unidad en las que se muestran las presiones.
        """
        self.interactor = interactor
        self.renderer = renderer
        self.unidad = unidad

        self.alturas_presiones_frente = edificio.geometria.alturas.tolist()
        self.alturas_presiones_lateral = edificio.geometria.alturas_alero.tolist()

        self._presiones_paredes = edificio.presiones.paredes.sprfv()
        self._presiones_cubierta = edificio.presiones.cubierta.sprfv()
        if hasattr(edificio.presiones, "alero"):
            self._presiones_alero = edificio.presiones.alero.sprfv()
        else:
            self._presiones_alero = None

        presiones = {}
        for i, presion in enumerate((self._presiones_paredes, self._presiones_cubierta, self._presiones_alero)):
            if presion is not None:
                presiones[str(i)] = presion

        min_max_presiones = (convertir_unidad(p, self.unidad) for p in min_max_valores(**presiones))

        tabla_colores = vtk.vtkLookupTable()
        tabla_colores.SetTableRange(*min_max_presiones)
        tabla_colores.SetHueRange(0.66, 0)
        tabla_colores.Build()

        self._barra_escala = ActorBarraEscala(self.renderer, tabla_colores, self.unidad)

        self._titulo = ActorTexto2D(self.renderer)

        self.director = directores_edificio.PresionesSprfvMetodoDireccional(self.renderer, tabla_colores, edificio)

        # Preseteo de alturas barlovento iniciales. Como todos los parametros son definidos inicialmente por el metodo
        # "cambiar_direccion_viento" es necesario esten asignadas estas alturas para poder actualizar la pared barlovento.

        self.alturas_presion_barlovento = {
            DireccionVientoMetodoDireccionalSprfv.PARALELO: self.alturas_presiones_frente[-1]
        }
        posicion_cubierta_un_agua = getattr(self.director, "posicion_cubierta_un_agua", None)
        if posicion_cubierta_un_agua is not None:
            self._posicion_cubierta_un_agua_actual = posicion_cubierta_un_agua
            self.alturas_presion_barlovento[DireccionVientoMetodoDireccionalSprfv.NORMAL] = {
                PosicionCubiertaAleroSprfv.SOTAVENTO: self.alturas_presiones_frente[-1],
                PosicionCubiertaAleroSprfv.BARLOVENTO: self.alturas_presiones_lateral[-1],
            }
        else:
            self.alturas_presion_barlovento[
                DireccionVientoMetodoDireccionalSprfv.NORMAL
            ] = self.alturas_presiones_lateral[-1]

        # Preseteo del indice de la presión interna actual (0 es positivo y 1 es negativo)
        self._gcpi_actual = 0
        self._textos_presion_interna = ("+", "-")

        # Preseteo del caso a cubierta barlovento con angulo > 10°.
        if not self.director.normal_como_paralelo and self.director.tipo_cubierta in (
            TipoCubierta.UN_AGUA,
            TipoCubierta.DOS_AGUAS,
        ):
            self._tipo_presion_cubierta_barlovento = TipoPresionCubiertaBarloventoSprfv.NEGATIVA

        if hasattr(self.director, "posicion_cubierta_un_agua"):
            self._posicion_cubierta_un_agua_actual = self.director.posicion_cubierta_un_agua

        # Inicialización de variables internas que serán actualizadas cuando los métodos correspondientes sean llamados.
        self._actores_actuales_paredes = self._actores_actuales_cubierta = None
        self._direccion_actual = None
        self._presiones_actuales_paredes = None
        self._presiones_actuales_cubierta = None
        if self._presiones_alero is not None:
            self._actores_actuales_alero = None
            self._presiones_actuales_alero = None
        self._alturas_actuales_presion_barlovento = None

        self._actores_presion = obtener_actores_presion_en_renderer(self.renderer)

    def actualizar_gcpi(self, indice_gcpi: int) -> None:
        """Actualiza el factor de presión interna actual para todos los actores.

        Args:
            indice_gcpi: 0 es presión interna positiva y 1 es presión interna negativa.
        """
        self._gcpi_actual = indice_gcpi
        self._actualizar_paredes_sotavento_lateral()
        self._actualizar_cubierta()
        self._actualizar_titulo()
        self.interactor.ReInitialize()

    def actualizar_direccion_viento(self, direccion: DireccionVientoMetodoDireccionalSprfv) -> None:
        """Actualiza la dirección del viento actual y los actores de la escena para esa dirección.

        Args:
            direccion: La dirección a la que se actualiza la escena.
        """
        self._direccion_actual = direccion
        self.director.direccion = direccion
        self._presiones_actuales_paredes = self._presiones_paredes[direccion]
        self._presiones_actuales_cubierta = self._presiones_cubierta[direccion]
        self._alturas_actuales_presion_barlovento = self.alturas_presion_barlovento[direccion]
        self._actualizar_paredes_sotavento_lateral(regenerar_actores=True)
        self._actualizar_cubierta(regenerar_actores=True)
        if self._presiones_alero is not None:
            self._presiones_actuales_alero = self._presiones_alero[direccion]
            self._actualizar_alero(regenerar_actores=True)
        self._actualizar_titulo()
        self.interactor.ReInitialize()

    def actualizar_posicion_cubierta_un_agua(self, posicion: PosicionCubiertaAleroSprfv) -> None:
        """Actualiza las presiones de la cubierta a un agua respecto para la nueva posición respecto al viento.

        Se debe utilizar cuando el tipo de cubierta es a un agua y la dirección del viento es normal a la cumbrera.

        Args:
            posicion: La posición de la cubierta respecto al viento para la que se actualizan las presiones.
        """
        self.director.posicion_cubierta_un_agua = self._posicion_cubierta_un_agua_actual = posicion
        self._actualizar_paredes_sotavento_lateral(regenerar_actores=True)

        # Si la cubierta con viento normal se comporta como paralelo (angulo < 10°), se tienen que regenerar los actores
        # de cubierta ya que cambian las zonas.
        self._actualizar_cubierta(regenerar_actores=self.director.normal_como_paralelo)
        if self._presiones_alero is not None:
            self._actualizar_alero()
        self._actualizar_titulo()
        self.interactor.ReInitialize()

    def actualizar_presion_cubierta_inclinada(self, presion: TipoPresionCubiertaBarloventoSprfv) -> None:
        """Actualiza las presiones del faldón de cubierta que corresponde a la posición de barlovento respecto al viento.

        Se debe utilizar cuando el tipo de cubierta es a un agua o dos aguas, el angulo de la misma es >=10° y
        la dirección del viento es normal a la cumbrera.

        Args:
            presion: La presión al que se actualiza la presión de la cubierta a barlovento.

        Returns:

        """
        self._tipo_presion_cubierta_barlovento = presion
        self._actualizar_cubierta()
        if self._presiones_alero is not None:
            self._actualizar_alero()
        self._actualizar_titulo()
        self.interactor.ReInitialize()

    def actualizar_altura_pared_barlovento(self, altura, reiniciar_interactor=True) -> None:
        """Actualiza la altura a la que se calcula la presión sobre la pared a barlovento.

        Args:
            altura: La altura a la que actualizar la presión.
            reiniciar_interactor: Indica si hay que reiniciar el intercator.
        """
        actor = self._actores_actuales_paredes[ParedEdificioSprfv.BARLOVENTO]
        if self._direccion_actual == DireccionVientoMetodoDireccionalSprfv.NORMAL and hasattr(
            self, "_posicion_cubierta_un_agua_actual"
        ):
            self.alturas_presion_barlovento[self._direccion_actual][self._posicion_cubierta_un_agua_actual] = altura
        else:
            self.alturas_presion_barlovento[self._direccion_actual] = altura
        array_presiones = self._presiones_actuales_paredes[ParedEdificioSprfv.BARLOVENTO][self._gcpi_actual]

        # Se usa las alturas del frente ya que contiene todas las de lateral también con los mismo indices.
        presion = array_presiones[self.alturas_presiones_frente.index(altura)]
        actor.asignar_presion(presion, str_extra=f"({altura:.2f} m)", unidad=self.unidad)
        if reiniciar_interactor:
            self.interactor.ReInitialize()

    def _actualizar_paredes_sotavento_lateral(self, regenerar_actores=False) -> None:
        """Actualiza los actores y presiones para las paredes sotavento y laterales.

        Args:
            regenerar_actores: Indica si los actores deben ser regenerados. Si es False, los actores no se cambian pero
            se actualiza la presión sobre los mismos.
        """
        if regenerar_actores:
            if self._actores_actuales_paredes is not None:
                aplicar_func_recursivamente(self._actores_actuales_paredes, lambda _actor: _actor.ocultar())
            self._actores_actuales_paredes = self.director.obtener_paredes()
        for pared, actores in self._actores_actuales_paredes.items():
            presion = self._presiones_actuales_paredes[pared][self._gcpi_actual]
            if pared == ParedEdificioSprfv.BARLOVENTO:
                if regenerar_actores:
                    actores.mostrar()
            elif pared == ParedEdificioSprfv.LATERAL:
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
                aplicar_func_recursivamente(self._actores_actuales_cubierta, lambda actor: actor.ocultar())
            self._actores_actuales_cubierta = self.director.obtener_cubierta()
        if self._direccion_actual == DireccionVientoMetodoDireccionalSprfv.PARALELO or (
            self._direccion_actual == DireccionVientoMetodoDireccionalSprfv.NORMAL
            and self.director.normal_como_paralelo
        ):
            for i, presion in enumerate(self._presiones_actuales_cubierta[self._gcpi_actual]):
                try:
                    # Caso de cubierta a dos aguas que tiene barlovento y sotavento como actores en cada zona
                    for actores in self._actores_actuales_cubierta.values():
                        actores[i].asignar_presion(presion, unidad=self.unidad)
                except AttributeError:
                    self._actores_actuales_cubierta[i].asignar_presion(presion, unidad=self.unidad)
        else:
            presiones = self._presiones_actuales_cubierta.copy()
            presiones[PosicionCubiertaAleroSprfv.BARLOVENTO] = presiones[PosicionCubiertaAleroSprfv.BARLOVENTO][
                self._tipo_presion_cubierta_barlovento
            ]
            if self.director.tipo_cubierta == TipoCubierta.UN_AGUA:
                presion = presiones[self._posicion_cubierta_un_agua_actual]
                self._actores_actuales_cubierta.asignar_presion(presion[self._gcpi_actual], unidad=self.unidad)
            else:
                for zona, presion in presiones.items():
                    self._actores_actuales_cubierta[zona].asignar_presion(
                        presion[self._gcpi_actual], unidad=self.unidad
                    )

    def _actualizar_alero(self, regenerar_actores=False) -> None:
        """Actualiza los actores y presiones para los aleros.

        Args:
            regenerar_actores: Indica si los actores deben ser regenerados. Si es False, los actores no se cambian pero
            se actualiza la presión sobre los mismos.
        """
        if regenerar_actores:
            if self._actores_actuales_alero is not None:
                aplicar_func_recursivamente(self._actores_actuales_alero, lambda x: x.ocultar())
            self._actores_actuales_alero = self.director.obtener_alero()
        if self._direccion_actual == DireccionVientoMetodoDireccionalSprfv.PARALELO:
            for i, presion in enumerate(self._presiones_actuales_alero):
                for alero in self._actores_actuales_alero.values():
                    alero[i].asignar_presion(presion, unidad=self.unidad)
        else:
            presiones = self._presiones_actuales_alero.copy()
            if not self.director.normal_como_paralelo:
                presiones[PosicionCubiertaAleroSprfv.BARLOVENTO] = presiones[PosicionCubiertaAleroSprfv.BARLOVENTO][
                    self._tipo_presion_cubierta_barlovento
                ]
            if self.director.tipo_cubierta != TipoCubierta.UN_AGUA:
                for posicion, actor in self._actores_actuales_alero.items():
                    actor.asignar_presion(presiones[posicion], unidad=self.unidad)
            else:
                presion = presiones[self._posicion_cubierta_un_agua_actual]
                self._actores_actuales_alero.asignar_presion(presion, unidad=self.unidad)

    def _actualizar_titulo(self) -> None:
        """Actualiza el título de la escena."""
        texto = f"Viento {self._direccion_actual.value.capitalize()} a la Cumbrera"
        texto += f" ({self._textos_presion_interna[self._gcpi_actual]}GCpi)"
        if self._direccion_actual == DireccionVientoMetodoDireccionalSprfv.NORMAL:
            posicion_cubierta_un_agua = getattr(self, "_posicion_cubierta_un_agua_actual", None)
            if posicion_cubierta_un_agua is not None:
                texto += f" - Cubierta a {posicion_cubierta_un_agua.value.capitalize()}"
            if posicion_cubierta_un_agua != PosicionCubiertaAleroSprfv.SOTAVENTO:
                caso_cubierta_barlovento = getattr(self, "_caso_cubierta_barlovento", None)
                if caso_cubierta_barlovento is not None:
                    texto += f" - Caso {self._tipo_presion_cubierta_barlovento.value}"

        self._titulo.setear_texto(texto)


class PresionesComponentes(PresionesMixin):
    """PresionesComponentes.

    Representa la escena de la visualización de presiones del viento sobre el SPRFV un edificio utilizando el método
    direccional.
    """

    def __init__(
        self, interactor: vtk.vtkRenderWindowInteractor, renderer: vtk.vtkRenderer, edificio: Edificio, unidad: Unidad
    ) -> None:
        """

        Args:
            interactor: El interactor de la ventana de visualización.
            renderer: El renderer utilizado para renderizar los actores en la escena.
            edificio: Una instancia de Edificio.
        """
        self.interactor = interactor
        self.renderer = renderer
        self.unidad = unidad

        self._componentes_paredes = edificio.componentes_paredes
        self._componentes_cubierta = edificio.componentes_cubierta

        self._presiones_paredes = edificio.presiones.paredes.componentes()

        self._presiones_cubierta = edificio.presiones.cubierta.componentes()

        if hasattr(edificio.presiones, "alero") and self._presiones_cubierta is not None:
            self._presiones_alero = edificio.presiones.alero.componentes()
        else:
            self._presiones_alero = None

        presiones = {}
        for i, presion in enumerate((self._presiones_paredes, self._presiones_cubierta, self._presiones_alero)):
            if presion is not None:
                presiones[str(i)] = presion

        min_max_presiones = (convertir_unidad(p, self.unidad) for p in min_max_valores(**presiones))

        tabla_colores = vtk.vtkLookupTable()
        tabla_colores.SetTableRange(*min_max_presiones)
        tabla_colores.SetHueRange(0.66, 0)
        tabla_colores.Build()

        # TODO - Importante!!!! Levantar la unidad desde configuración

        self._barra_escala = ActorBarraEscala(self.renderer, tabla_colores, self.unidad)

        self._titulo = ActorTexto2D(self.renderer)

        self.director = directores_edificio.PresionesComponentes(self.renderer, tabla_colores, edificio)

        self._actores_paredes = self.director.obtener_paredes()
        if self._presiones_paredes is None:
            aplicar_func_recursivamente(self._actores_paredes, lambda actor: actor.flecha.ocultar())

        self._actores_cubierta = self.director.obtener_cubierta()

        if self._presiones_cubierta is None:
            aplicar_func_recursivamente(self._actores_cubierta, lambda actor: actor.flecha.ocultar())

        self._actores_alero = self.director.obtener_alero()
        if self._presiones_alero is None and self._actores_alero is not None:
            aplicar_func_recursivamente(self._actores_alero, lambda actor: actor.flecha.ocultar())

        self._gcpi_actual = 0
        self._textos_presion_interna = ("+", "-")

        self._tipo_presion_componente_actual = TipoPresionComponentesParedesCubierta.NEGATIVA
        self._componente_actual_pared = self._componente_actual_cubierta = None

        self._es_figura_8_paredes = edificio.cp.paredes.componentes.referencia == "Figura 8"
        if self._es_figura_8_paredes:
            self._alturas_pared_barlovento = edificio.geometria.alturas.tolist()

        self._actores_presion = obtener_actores_presion_en_renderer(self.renderer)

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
        self.interactor.ReInitialize()

    def actualizar_tipo_presion(self, tipo_presion: TipoPresionComponentesParedesCubierta) -> None:
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
        self.interactor.ReInitialize()

    def actualizar_componente_pared(self, componente: str) -> None:
        """Actualiza el componente para las paredes.

        Args:
            componente: El nombre del componente.
        """
        self._componente_actual_pared = componente
        self._actualizar_paredes()
        self._actualizar_titulo()
        self.interactor.ReInitialize()

    def actualizar_componente_cubierta(self, componente: str) -> None:
        """Actualiza el componente para las paredes.

        Args:
            componente: El nombre del componente.
        """
        self._componente_actual_cubierta = componente
        self._actualizar_cubierta()
        if self._presiones_alero is not None:
            self._actualizar_alero()
        self._actualizar_titulo()
        self.interactor.ReInitialize()

    def actualizar_altura_pared_barlovento(self, altura, reiniciar_interactor=True) -> None:
        """Actualiza la altura a la que se calcula la presión sobre la pared a barlovento.

        Args:
            altura: La altura a la que actualizar la presión.
            reiniciar_interactor: Indica si hay que reiniciar el intercator.
        """
        pared = self._actores_paredes[ParedEdificioSprfv.BARLOVENTO]
        presiones = self._presiones_paredes[ParedEdificioSprfv.BARLOVENTO][self._componente_actual_pared]
        for zona, actores in pared.items():
            array_presiones = self._seleccionar_presion_pared_por_tipo(presiones, zona)
            presion = array_presiones[self._alturas_pared_barlovento.index(altura)]
            if zona == ZonaComponenteParedEdificio.CINCO:
                for actor in actores:
                    actor.asignar_presion(presion=presion, str_extra=f"({altura} m)", unidad=self.unidad)
            else:
                actores.asignar_presion(presion=presion, str_extra=f"({altura} m)", unidad=self.unidad)
        if reiniciar_interactor:
            self.interactor.ReInitialize()

    def _actualizar_paredes(self) -> None:
        if self._es_figura_8_paredes:
            # Podria ser Lateral tambien ya que el valor de cp es el mismo, la unica que cambia es la pared a barlovento.
            presiones_paredes = self._presiones_paredes[ParedEdificioSprfv.SOTAVENTO]
        else:
            presiones_paredes = self._presiones_paredes

        presiones = presiones_paredes[self._componente_actual_pared]
        for pared, zonas in self._actores_paredes.items():
            if self._es_figura_8_paredes and pared == ParedEdificioSprfv.BARLOVENTO:
                continue
            for zona, actores in zonas.items():
                if zona == ZonaComponenteParedEdificio.CINCO:
                    for actor in actores:
                        actor.asignar_presion(
                            presion=self._seleccionar_presion_pared_por_tipo(presiones, zona), unidad=self.unidad
                        )
                else:
                    actores.asignar_presion(
                        presion=self._seleccionar_presion_pared_por_tipo(presiones, zona), unidad=self.unidad
                    )

    def _actualizar_cubierta(self) -> None:
        presiones = self._presiones_cubierta[self._componente_actual_cubierta]
        for zona, actores in self._actores_cubierta.items():
            presion = self._seleccionar_presion_cubierta_por_tipo(presiones, zona)
            if presion is not None:
                try:
                    for actor in actores:
                        actor.asignar_presion(presion=presion, unidad=self.unidad)
                except TypeError:
                    actores.asignar_presion(presion=presion, unidad=self.unidad)

    def _actualizar_alero(self) -> None:
        presiones = self._presiones_alero[self._componente_actual_cubierta]
        for zona, actores in self._actores_alero.items():
            try:
                for actor in actores:
                    actor.asignar_presion(presiones[zona], unidad=self.unidad)
            except TypeError:
                actores.asignar_presion(presiones[zona], unidad=self.unidad)

    def _seleccionar_presion_pared_por_tipo(
        self, presiones: Dict[ZonaComponenteParedEdificio, PresionesEdificio], zona: ZonaComponenteParedEdificio
    ):
        if self._tipo_presion_componente_actual == TipoPresionComponentesParedesCubierta.POSITIVA:
            return presiones[ZonaComponenteParedEdificio.TODAS][self._gcpi_actual]
        return presiones[zona][self._gcpi_actual]

    def _seleccionar_presion_cubierta_por_tipo(
        self, presiones: Dict[ZonaComponenteCubiertaEdificio, PresionesEdificio], zona: ZonaComponenteCubiertaEdificio
    ):
        if self._tipo_presion_componente_actual == TipoPresionComponentesParedesCubierta.POSITIVA:
            try:
                return presiones[ZonaComponenteCubiertaEdificio.TODAS][self._gcpi_actual]
            except KeyError:
                return
        return presiones[zona][self._gcpi_actual]

    def _actualizar_titulo(self) -> None:
        """Actualiza el título de la escena."""
        texto = f"Presión {self._tipo_presion_componente_actual.value.capitalize()}"
        if (
            self._es_figura_8_paredes
            and self._tipo_presion_componente_actual == TipoPresionComponentesParedesCubierta.POSITIVA
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
