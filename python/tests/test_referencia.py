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

"""Verifica que los resultados del núcleo no hayan cambiado.

Compara todos los números que produce la matriz de `tests.referencia` contra
los archivos guardados en ``tests/referencia/``. No verifica que los valores
sean correctos según el Reglamento, sino que sigan siendo los mismos: cualquier
cambio inadvertido al tocar el cálculo falla acá y aparece en el diff de git.
"""

import pytest

from tests import referencia


def _mensaje(nombre: str, obtenido: list[str], esperado: list[str]) -> str:
    """Arma un mensaje que ubique la primera diferencia.

    Args:
        nombre: El nombre del archivo de referencia.
        obtenido: Las líneas que produce el programa ahora.
        esperado: Las líneas guardadas en el archivo.

    Returns:
        El mensaje de error.
    """
    lineas = [
        f"Los resultados cambiaron respecto de tests/referencia/{nombre}.tsv.",
    ]
    if len(obtenido) != len(esperado):
        lineas.append(
            f"Cantidad de filas: {len(esperado) - 1} en la referencia,"
            f" {len(obtenido) - 1} ahora."
        )
    for numero, (ahora, antes) in enumerate(zip(obtenido, esperado), start=1):
        if ahora != antes:
            lineas += [
                f"Primera diferencia en la línea {numero}:",
                f"  referencia: {antes}",
                f"  ahora:      {ahora}",
            ]
            break
    lineas.append(
        "Si el cambio es deliberado, regenerar con: uv run python -m tests.referencia"
    )
    return "\n".join(lineas)


@pytest.mark.parametrize("nombre", sorted(referencia.ARCHIVOS))
def test_los_resultados_no_cambiaron(nombre: str):
    esperado = referencia.leer(nombre)
    obtenido = referencia.generar(nombre)
    assert obtenido == esperado, _mensaje(nombre, obtenido, esperado)
