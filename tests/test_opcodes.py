from mylox.bytecode.opcodes import INSTRUCTIONS, OpCode, stack_effect, takes_operand


def test_las_instrucciones_tienen_codigos_distintos():
    valores = [opcode.value for opcode in OpCode]
    assert len(valores) == len(set(valores))


def test_solo_op_constant_lleva_operando():
    con_operando = {opcode for opcode in OpCode if takes_operand(opcode)}
    assert con_operando == {OpCode.OP_CONSTANT}


def test_toda_instruccion_tiene_su_descripcion():
    # Si se agrega un OpCode nuevo, este test obliga a declararle el efecto.
    assert set(INSTRUCTIONS) == set(OpCode)


def test_una_expresion_deja_un_valor_en_la_pila():
    # 6 / 3: dos cargas y una binaria.
    secuencia = (OpCode.OP_CONSTANT, OpCode.OP_CONSTANT, OpCode.OP_DIVIDE)
    assert sum(stack_effect(op) for op in secuencia) == 1


def test_una_sentencia_deja_la_pila_como_estaba():
    # print 6 / 3; y 6 / 3;
    carga = (OpCode.OP_CONSTANT, OpCode.OP_CONSTANT, OpCode.OP_DIVIDE)
    assert sum(stack_effect(op) for op in (*carga, OpCode.OP_PRINT)) == 0
    assert sum(stack_effect(op) for op in (*carga, OpCode.OP_POP)) == 0
