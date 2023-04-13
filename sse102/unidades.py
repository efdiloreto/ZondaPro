from zonda.enums import Unidad


def convertir_unidad(valor: float, unidad: Unidad) -> float:
    """Convierte un valor de N a la unidad especificada.

    Args:
        valor: El valor a convertir en Newtons.
        unidad: La unidad a la que se convierte.

    Returns:

    """
    if unidad == Unidad.N:
        return valor
    if unidad == Unidad.KN:
        return valor * 0.001
    if unidad == Unidad.KG:
        return valor * 0.1019716213
