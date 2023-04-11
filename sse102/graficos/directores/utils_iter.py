from __future__ import annotations

from typing import Sequence, Dict, Callable, Any, Generator, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sse102.tipos import ParNumerico


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
        return {k: aplicar_func_recursivamente(v, func, iterable) for k, v in ob.items()}
    if not iterable:
        return func(ob)
    try:
        return tuple(func(x) for x in ob)
    except TypeError:
        return func(ob)


def aplanar_dict(d: Dict) -> Dict:
    """Aplana un diccionario anidado.

    Args:
        d: El diccionario a aplanar.

    Returns:
        El diccionario aplanado.
    """
    out = {}
    for key, val in d.items():
        if isinstance(val, dict):
            val = [val]
        if isinstance(val, list):
            for subdict in val:
                deeper = aplanar_dict(subdict).items()
                try:
                    out.update({key + "_" + key2: val2 for key2, val2 in deeper})
                except TypeError:
                    out.update({str(key) + "_" + str(key2): val2 for key2, val2 in deeper})
        else:
            out[key] = val
    return out


def aplanar_secuencia(secuencia) -> Generator:
    """Aplana una secuencia. Por ejemplo una lista de listas.

    Args:
        secuencia: La secuencia a aplanar.

    Returns:
        Un generator con la secuencia aplanada.
    """
    for el in secuencia:
        if isinstance(el, (Sequence, np.ndarray)) and not isinstance(el, (str, bytes)):
            yield from aplanar_secuencia(el)
        else:
            yield el


def min_max_valores(**kwargs: Dict[str, float]) -> ParNumerico:
    """Aplana la estructura de los valores ingresados y obtiene el mínimo y máximo valor de entre todos los valores.

    Args:
        **kwargs: Diccionarios contiene valores numericos.

    Returns:
        Valor mínimo y máximo.
    """
    d = {key: value for key, value in kwargs.items() if value}
    d_aplanado = aplanar_dict(d)
    iter_aplanado = tuple(aplanar_secuencia(d_aplanado.values()))
    return min(iter_aplanado), max(iter_aplanado)
