#!/bin/sh
# Copyright (c) 2018-2026, Eduardo Di Loreto <efdiloreto@gmail.com>
#
# This file is part of Zonda.
#
# Zonda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Zonda is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Zonda.  If not, see <https://www.gnu.org/licenses/>.
#
# Lanzador de Zonda adentro del Flatpak. No se usa el lanzador nativo de
# launcher/: adentro del contenedor la ubicacion de todo es fija, asi que no
# hace falta que nadie salga a adivinar donde quedo el interprete.

# pandoc viaja en el bundle y es lo que exporta los reportes a PDF, DOCX y ODT.
PATH="/app/zonda/tools/pandoc:${PATH}"
export PATH

# Se agrega el paquete al path de imports en vez de hacer un cd: el .desktop
# pasa la ruta del proyecto con %f y un cd romperia las rutas relativas.
PYTHONPATH="/app/zonda/app${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONPATH

exec /app/zonda/python/bin/python3 -m zonda.main "$@"
