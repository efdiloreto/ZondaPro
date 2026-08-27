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

from collections.abc import Callable
from typing import Any


def aplicar_func_recursivamente(ob: Any, func: Callable, iterable: bool = True) -> Any:
    """Aplica una función recursivamente sobre los elementos de un objeto.

    Cualquier secuencia que contenga el objeto es convertida a tuple.

    Args:
        ob: El objeto a recorrer.
        func: La función a aplicar.
        iterable: Indica si hay que recorrer un iterable si esta presente.

    Returns:
        El objecto con sus valores modificados por la función.
    """
    if isinstance(ob, dict):
        return {
            k: aplicar_func_recursivamente(v, func, iterable) for k, v in ob.items()
        }
    if not iterable:
        return func(ob)
    try:
        return tuple(func(x) for x in ob)
    except TypeError:
        return func(ob)
