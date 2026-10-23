"""Semántica de valores de Lox, compartida por el tree-walk y la VM"""
from __future__ import annotations


def stringify(value: object) -> str:
    """Convierte un valor ya evaluado a su representación textual en Lox.

    None se escribe ``nil`` y los booleanos en minúscula. Los números enteros
    almacenados como float se muestran sin ``.0`` y las cadenas sin comillas.
    Devuelve texto, sin imprimir ni agregar el salto de línea.
    """
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def is_truthy(value: object) -> bool:
    """Indica si el valor cuenta como verdadero en una condición de Lox.

    Solamente None (``nil``) y False son falsos; el cero y la cadena vacía son
    verdaderos. Esta regla evita las diferencias con ``bool()`` de Python.
    """
    return not (value is None or value is False)
