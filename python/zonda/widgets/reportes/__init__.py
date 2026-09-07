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

"""El reporte de resultados con widgets nativos.

La vista en pantalla (`navegacion.VistaReporte`) muestra el mismo detalle
que el reporte exportado —secciones, tablas y notas— pero con widgets de
Qt: Jinja2 y pandoc quedan sólo para la exportación
(`exportacion.DialogoExportacion`). Cada tipología arma sus páginas en su
propio módulo y los bloques compartidos viven en `secciones.py`,
`tablas.py` y `comunes.py`.
"""

from zonda.widgets.reportes.navegacion import VistaReporte

__all__ = ("VistaReporte",)
