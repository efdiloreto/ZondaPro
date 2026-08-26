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


class PresionesMixin:
    """Comportamiento común de las escenas de presiones.

    No hace falta pedir un redibujado: los actores son objetos de Qt con
    propiedades y la vista se suscribe a ellas.
    """

    def aumentar_escala_flechas(self):
        """Aumentar la escala de las flechas para todos los actores de presón."""
        for actor in self._actores_presion:
            actor.flecha.aumentar_escala()

    def disminuir_escala_flechas(self):
        """Disminuye la escala de las flechas para todos los actores de presón."""
        for actor in self._actores_presion:
            actor.flecha.disminuir_escala()

    def aumentar_tamanio_label_presion(self):
        """Aumenta los tamaños de textos en los actores de presión."""
        for actor in self._actores_presion:
            actor.flecha.aumentar_tamanio_texto()

    def disminuir_tamanio_label_presion(self):
        """Disminuye los tamaños de textos en los actores de presión."""
        for actor in self._actores_presion:
            actor.flecha.disminuir_tamanio_texto()

    def ocultar_actores_presion(self):
        """Oculta los actores de presión de la escena."""
        for actor in self._actores_presion:
            actor.ocultar()
