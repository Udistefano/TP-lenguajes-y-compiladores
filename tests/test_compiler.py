import pytest

from mylox.errors import ParseError
from mylox.pipeline.lexer import Lexer
from mylox.bytecode.compiler import Compiler
from mylox.bytecode.opcodes import OpCode
from mylox.bytecode.chunk import Chunk


def compilar(source: str) -> Chunk:
    return Compiler(Lexer(source).run()).compile()


def test_un_literal_numero_es_una_sentencia_de_expresion():
    chunk = compilar("6;")
    assert len(chunk) == 4
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_POP.value
    assert chunk.read(3) == OpCode.OP_RETURN.value


def test_la_expresion_seis_sobre_tres_menos_uno_coincide_con_la_diapositiva():
    chunk = compilar("6 / 3 - 1;")

    assert len(chunk) == 10
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_CONSTANT.value
    assert chunk.read(4) == OpCode.OP_DIVIDE.value
    assert chunk.read(5) == OpCode.OP_CONSTANT.value
    assert chunk.read(7) == OpCode.OP_SUBTRACT.value
    assert chunk.read(8) == OpCode.OP_POP.value
    assert chunk.read(9) == OpCode.OP_RETURN.value


def test_print_emite_op_print_despues_de_la_expresion():
    chunk = compilar("print 2;")

    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_PRINT.value
    assert chunk.read(3) == OpCode.OP_RETURN.value


def test_un_programa_con_varias_sentencias_compila_todas():
    chunk = compilar("print 2; 3 + 4;")

    assert len(chunk) == 10
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_PRINT.value
    assert chunk.read(3) == OpCode.OP_CONSTANT.value
    assert chunk.read(5) == OpCode.OP_CONSTANT.value
    assert chunk.read(7) == OpCode.OP_ADD.value
    assert chunk.read(8) == OpCode.OP_POP.value
    assert chunk.read(9) == OpCode.OP_RETURN.value


def test_la_agrupacion_cambia_el_orden_de_evaluacion():
    chunk = compilar("(1 + 2) * 3;")
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_CONSTANT.value
    assert chunk.read(4) == OpCode.OP_ADD.value
    assert chunk.read(5) == OpCode.OP_CONSTANT.value
    assert chunk.read(7) == OpCode.OP_MULTIPLY.value


def test_la_negacion_y_el_menos_prefijo_emiten_op_negate_y_op_not():
    chunk = compilar("-7;")
    assert chunk.read(0) == OpCode.OP_CONSTANT.value
    assert chunk.read(2) == OpCode.OP_NEGATE.value

    chunk = compilar("!true;")
    assert chunk.read(0) == OpCode.OP_TRUE.value
    assert chunk.read(1) == OpCode.OP_NOT.value


def test_la_desigualdad_se_descompone_en_equal_y_not():
    chunk = compilar("1 != 2;")
    assert chunk.read(4) == OpCode.OP_EQUAL.value
    assert chunk.read(5) == OpCode.OP_NOT.value


def test_menor_o_igual_se_descompone_en_greater_y_not():
    chunk = compilar("1 <= 2;")
    assert chunk.read(4) == OpCode.OP_GREATER.value
    assert chunk.read(5) == OpCode.OP_NOT.value


def test_mayor_o_igual_se_descompone_en_less_y_not():
    chunk = compilar("1 >= 2;")
    assert chunk.read(4) == OpCode.OP_LESS.value
    assert chunk.read(5) == OpCode.OP_NOT.value


def test_el_modulo_emite_op_modulo():
    chunk = compilar("5 % 2;")
    assert chunk.read(4) == OpCode.OP_MODULO.value


def test_los_literales_booleanos_y_nil_tienen_instrucciones_propias():
    chunk = compilar("true;")
    assert chunk.read(0) == OpCode.OP_TRUE.value
    chunk = compilar("false;")
    assert chunk.read(0) == OpCode.OP_FALSE.value
    chunk = compilar("nil;")
    assert chunk.read(0) == OpCode.OP_NIL.value


def test_las_cadenas_se_guardan_en_el_pool_de_constantes():
    chunk = compilar('"abc";')
    assert chunk.constant(0) == "abc"
    assert chunk.read(0) == OpCode.OP_CONSTANT.value


def test_un_token_inesperado_produce_parse_error():
    with pytest.raises(ParseError):
        compilar("1 2;")


def test_un_parentesis_sin_cierre_produce_parse_error():
    with pytest.raises(ParseError):
        compilar("(1 + 2;")


def test_falta_el_punto_y_coma_produce_parse_error():
    with pytest.raises(ParseError):
        compilar("1 + 2")


def test_el_error_de_sintaxis_conserva_la_posicion():
    with pytest.raises(ParseError) as excinfo:
        compilar("1 +")
    assert "línea 1" in str(excinfo.value)


def test_un_programa_vacio_emite_solo_return():
    chunk = compilar("")
    assert len(chunk) == 1
    assert chunk.read(0) == OpCode.OP_RETURN.value
