from mylox.errors import LoxError
from mylox.function import Function, ReturnValue


class _Stub:
    """Objeto liviano para armar declaraciones y entornos sin Env real."""

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class _Param(_Stub):
    def __init__(self, lexeme: str) -> None:
        super().__init__(lexeme=lexeme)


def _function(nombre: str = "suma", parametros: list[str] | None = None) -> Function:
    parametros = parametros or []
    declaracion = _Stub(
        name=_Stub(lexeme=nombre),
        parameters=[_Param(p) for p in parametros],
        body=[],
    )
    return Function(declaration=declaracion, closure=_Stub())


def test_function_arity_cuenta_parametros():
    assert _function(parametros=["a", "b"]).arity == 2
    assert _function(parametros=[]).arity == 0


def test_function_str_muestra_nombre():
    assert str(_function("fib")) == "<fn fib>"


def test_return_value_guarda_valor():
    assert ReturnValue(42.0).value == 42.0
    assert ReturnValue(None).value is None


def test_return_value_no_es_un_error_de_lox():
    assert not issubclass(ReturnValue, LoxError)