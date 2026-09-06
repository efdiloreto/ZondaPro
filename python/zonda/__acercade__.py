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

__version__ = "1.1.1"
__compania__ = "Eduardo Di Loreto"
__web_compania__ = "https://github.com/efdiloreto"
__web__ = "https://github.com/efdiloreto/ZondaPro"
__ayuda__ = "https://github.com/efdiloreto/ZondaPro/issues"
__contacto__ = "mailto:efdiloreto@gmail.com"
__nombre__ = "Zonda"
__anio_inicio__ = "2018"


def anios_copyright() -> str:
    """El período que cubre el copyright, hasta el año en curso.

    Se calcula en vez de escribirse para no tener que acordarse de subirlo cada
    primero de enero. Sale del reloj del sistema: si alguien lo tiene atrasado
    verá un año viejo, que es un problema de nadie.

    Returns: El año de inicio, o el rango si ya pasó más de un año.
    """
    from datetime import date

    actual = date.today().year
    return (
        __anio_inicio__
        if actual <= int(__anio_inicio__)
        else f"{__anio_inicio__}-{actual}"
    )


__descripcion__ = "Cálculo de cargas de viento según CIRSOC 102-2025"
__reglamento__ = "CIRSOC 102-2025"
__autor__ = "Eduardo Di Loreto, Natalia Alvarado"
# Nombre y perfil de cada uno, para que la interfaz pueda enlazarlos. El de
# arriba se conserva porque el aviso de copyright los nombra en una sola línea.
__autores__ = (
    ("Eduardo Di Loreto", "https://www.linkedin.com/in/ediloreto/"),
    ("Natalia Alvarado", "https://www.linkedin.com/in/mnaa85/"),
)
__autor_email__ = "efdiloreto@gmail.com, mnaa85@gmail.com"
__autor_web__ = "https://github.com/efdiloreto"
# Adónde lleva el enlace de la columna de patrocinadores. Los niveles, los
# montos y las condiciones viven en el repositorio y no en el programa:
# cambiarlos no puede obligar a publicar una versión nueva.
__apoyo__ = "https://github.com/efdiloreto/ZondaPro/blob/master/PATROCINIO.md"
__licencia__ = "GPLv3"
__licencia_url__ = "https://www.gnu.org/licenses/gpl-3.0-standalone.html"
