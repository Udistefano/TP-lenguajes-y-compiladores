import pytest

from mylox.errors import ParseError
from mylox.pipeline.lexer import Lexer
from mylox.bytecode.compiler import Compiler
from mylox.bytecode.opcodes import OpCode
from mylox.bytecode.chunk import Chunk


def compilar(source: str) -> Chunk:
    return Compiler(Lexer(source).run()).compile()

def test_literal_emite_constante_y_return():
    chunk = compilar("6")
    assert len(chunk) == 3
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.constant(0) == 6.0
    assert chunk.read(2) == OpCode.OP_RETURN.value

def test_expresion():
    chunk = compilar("6 / 3 - 1")

    assert len(chunk) == 9
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_CONSTANT.value
    assert chunk.read(4) == OpCode.OP_DIVIDE.value
    assert chunk.read(5) == OpCode.OP_CONSTANT.value
    assert chunk.read(7) == OpCode.OP_SUBTRACT.value
    assert chunk.read(8) == OpCode.OP_RETURN.value

def test_agrupacion_cambia_orden():
    # (1 + 2) * 3: las dos constantes internas se suman antes de multiplicar.
    chunk = compilar("(1 + 2) * 3")
    assert chunk.read(0) == OpCode.OP_CONSTANT.value  # 1
    assert chunk.read(2) == OpCode.OP_CONSTANT.value  # 2
    assert chunk.read(4) == OpCode.OP_ADD.value
    assert chunk.read(5) == OpCode.OP_CONSTANT.value  # 3
    assert chunk.read(7) == OpCode.OP_MULTIPLY.value

def test_op_negate_y_op_not():
    chunk = compilar("-7")
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_NEGATE.value

    chunk = compilar("!true")
    assert chunk.read(0) == OpCode.OP_TRUE.value
    assert chunk.read(1) == OpCode.OP_NOT.value

def test_desigualdad_en_equal_y_not():
    # a != b  ⇔  !(a == b)
    chunk = compilar("1 != 2")
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_CONSTANT.value
    assert chunk.read(4) == OpCode.OP_EQUAL.value
    assert chunk.read(5) == OpCode.OP_NOT.value


def test_menor_o_igual_en_greater_y_not():
    # a <= b  ⇔  !(a > b)
    chunk = compilar("1 <= 2")
    assert chunk.read(4) == OpCode.OP_GREATER.value
    assert chunk.read(5) == OpCode.OP_NOT.value


def test_mayor_o_igual_en_less_y_not():
    # a >= b  ⇔  !(a < b)
    chunk = compilar("1 >= 2")
    assert chunk.read(4) == OpCode.OP_LESS.value
    assert chunk.read(5) == OpCode.OP_NOT.value


def test_op_modulo():
    chunk = compilar("5 % 2")
    assert chunk.read(4) == OpCode.OP_MODULO.value


def test_cadenas_pool():
    chunk = compilar('"abc"')
    assert chunk.constant(0) == "abc"
    assert chunk.read(0) == OpCode.OP_CONSTANT.value


def test_fuente_vacia_parse_error():
    with pytest.raises(ParseError):
        compilar("")

def test_error_conserva_posicion():
    with pytest.raises(ParseError) as excinfo:
        compilar("1 +")
    assert "línea 1" in str(excinfo.value)
