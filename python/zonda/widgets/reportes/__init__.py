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

La vista en pantalla y el PDF (`zonda.pdf`) consumen el mismo documento
modelo (`documento.Documento`), armado por cada tipología en su módulo;
los bloques compartidos viven en `secciones.py`, `tablas.py` y
`comunes.py`. El diálogo de exportación
(`exportacion.DialogoExportacion`) deja elegir el papel y pide el PDF.
"""

from zonda.widgets.reportes.navegacion import VistaReporte

__all__ = ("VistaReporte",)
