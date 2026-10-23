import dataclasses

import pytest

from mylox.bytecode.opcodes import (
    INSTRUCTIONS,
    MAX_CONSTANT_INDEX,
    Instruction,
    OpCode,
    stack_effect,
    takes_operand,
)


def efectos(secuencia: tuple[OpCode, ...]) -> int:
    """Suma los efectos de pila de una secuencia de instrucciones."""
    return sum(stack_effect(opcode) for opcode in secuencia)


def test_las_instrucciones_tienen_codigos_distintos():
    valores = [opcode.value for opcode in OpCode]
    assert len(valores) == len(set(valores))


def test_solo_op_constant_lleva_operando():
    con_operando = {opcode for opcode in OpCode if takes_operand(opcode)}
    assert con_operando == {OpCode.OP_CONSTANT}


def test_toda_instruccion_tiene_su_descripcion():
    # Si se agrega un OpCode nuevo, este test obliga a declararle el efecto.
    assert set(INSTRUCTIONS) == set(OpCode)


def test_el_indice_maximo_de_constante_entra_en_un_byte():
    assert MAX_CONSTANT_INDEX == 255


def test_las_cargas_apilan_un_valor():
    for opcode in (OpCode.OP_CONSTANT, OpCode.OP_TRUE, OpCode.OP_FALSE, OpCode.OP_NIL):
        assert stack_effect(opcode) == 1


def test_las_unarias_reemplazan_su_operando():
    assert stack_effect(OpCode.OP_NOT) == 0
    assert stack_effect(OpCode.OP_NEGATE) == 0


def test_las_binarias_consumen_un_operando():
    binarias = (
        OpCode.OP_ADD,
        OpCode.OP_SUBTRACT,
        OpCode.OP_MULTIPLY,
        OpCode.OP_DIVIDE,
        OpCode.OP_EQUAL,
        OpCode.OP_GREATER,
        OpCode.OP_LESS,
    )
    for opcode in binarias:
        assert stack_effect(opcode) == -1


def test_las_sentencias_retiran_el_valor_de_su_expresion():
    assert stack_effect(OpCode.OP_POP) == -1
    assert stack_effect(OpCode.OP_PRINT) == -1
    assert stack_effect(OpCode.OP_RETURN) == 0


def test_una_expresion_deja_un_valor_en_la_pila():
    # 6 / 3: dos constantes y una operación binaria.
    assert efectos((OpCode.OP_CONSTANT, OpCode.OP_CONSTANT, OpCode.OP_DIVIDE)) == 1


def test_una_expresion_unaria_deja_un_valor_en_la_pila():
    # -7: una constante y la negación.
    assert efectos((OpCode.OP_CONSTANT, OpCode.OP_NEGATE)) == 1


def test_una_sentencia_deja_la_pila_como_estaba():
    # print 6 / 3;  y  6 / 3;
    assert efectos((OpCode.OP_CONSTANT, OpCode.OP_CONSTANT, OpCode.OP_DIVIDE, OpCode.OP_PRINT)) == 0
    assert efectos((OpCode.OP_CONSTANT, OpCode.OP_CONSTANT, OpCode.OP_DIVIDE, OpCode.OP_POP)) == 0


