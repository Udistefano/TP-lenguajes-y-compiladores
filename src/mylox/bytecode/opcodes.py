"""Instrucciones de bytecode de mylox y sus efectos sobre la pila"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto

MAX_CONSTANT_INDEX = 255


class OpCode(IntEnum):
    """instrucciones que la máquina virtual sabe ejecutar."""

    # Carga de valores en la pila
    OP_CONSTANT = auto()
    OP_TRUE = auto()
    OP_FALSE = auto()
    OP_NIL = auto()

    # Variables globales
    OP_DEFINE_GLOBAL = auto()
    OP_GET_GLOBAL = auto()
    OP_SET_GLOBAL = auto()

    # Variables locales
    OP_GET_LOCAL = auto()
    OP_SET_LOCAL = auto()

    # Sentencias y fin de programa
    OP_POP = auto()
    OP_PRINT = auto()
    OP_RETURN = auto()

    # Comparaciones
    OP_EQUAL = auto()
    OP_GREATER = auto()
    OP_LESS = auto()

    # Aritmética
    OP_ADD = auto()
    OP_SUBTRACT = auto()
    OP_MULTIPLY = auto()
    OP_DIVIDE = auto()
    OP_MODULO = auto()

    # Unarias
    OP_NOT = auto()
    OP_NEGATE = auto()

    # Funciones
    OP_CALL = auto()
    OP_CLOSURE = auto()

    # Upvalues (closures)
    OP_GET_UPVALUE = auto()
    OP_SET_UPVALUE = auto()
    OP_CLOSE_UPVALUE = auto()

    # Clases y herencia (OOP)
    OP_CLASS = auto()
    OP_GET_PROPERTY = auto()
    OP_SET_PROPERTY = auto()
    OP_METHOD = auto()
    OP_INHERIT = auto()
    OP_GET_SUPER = auto()
    OP_INVOKE = auto()
    OP_SUPER_INVOKE = auto()

    # Saltos
    OP_JUMP = auto()
    OP_JUMP_IF_FALSE = auto()
    OP_LOOP = auto()

    OP_LIST = auto()
    OP_GET_INDEX = auto()
    OP_SET_INDEX = auto()
    OP_GREATER_EQUAL = auto()
    OP_LESS_EQUAL = auto()


@dataclass(frozen=True, slots=True)
class Instruction:
    stack_effect: int
    operand_size: int


INSTRUCTIONS: dict[OpCode, Instruction] = {
    OpCode.OP_CONSTANT: Instruction(stack_effect=+1, operand_size=1),
    OpCode.OP_TRUE: Instruction(stack_effect=+1, operand_size=0),
    OpCode.OP_FALSE: Instruction(stack_effect=+1, operand_size=0),
    OpCode.OP_NIL: Instruction(stack_effect=+1, operand_size=0),
    OpCode.OP_DEFINE_GLOBAL: Instruction(stack_effect=-1, operand_size=1),
    OpCode.OP_GET_GLOBAL: Instruction(stack_effect=+1, operand_size=1),
    OpCode.OP_SET_GLOBAL: Instruction(stack_effect=0, operand_size=1),
    OpCode.OP_GET_LOCAL: Instruction(stack_effect=+1, operand_size=1),
    OpCode.OP_SET_LOCAL: Instruction(stack_effect=0, operand_size=1),
    OpCode.OP_POP: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_PRINT: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_RETURN: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_EQUAL: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_GREATER: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_LESS: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_GREATER_EQUAL: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_LESS_EQUAL: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_ADD: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_SUBTRACT: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_MULTIPLY: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_DIVIDE: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_MODULO: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_NOT: Instruction(stack_effect=0, operand_size=0),
    OpCode.OP_NEGATE: Instruction(stack_effect=0, operand_size=0),
    OpCode.OP_CALL: Instruction(stack_effect=0, operand_size=1),
    OpCode.OP_CLOSURE: Instruction(stack_effect=+1, operand_size=1),
    OpCode.OP_GET_UPVALUE: Instruction(stack_effect=+1, operand_size=1),
    OpCode.OP_SET_UPVALUE: Instruction(stack_effect=0, operand_size=1),
    OpCode.OP_CLOSE_UPVALUE: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_CLASS: Instruction(stack_effect=+1, operand_size=1),
    OpCode.OP_GET_PROPERTY: Instruction(stack_effect=0, operand_size=1),
    OpCode.OP_SET_PROPERTY: Instruction(stack_effect=-1, operand_size=1),
    OpCode.OP_METHOD: Instruction(stack_effect=-1, operand_size=1),
    OpCode.OP_INHERIT: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_GET_SUPER: Instruction(stack_effect=-1, operand_size=1),
    OpCode.OP_INVOKE: Instruction(stack_effect=0, operand_size=2),
    OpCode.OP_SUPER_INVOKE: Instruction(stack_effect=0, operand_size=2),
    OpCode.OP_JUMP: Instruction(stack_effect=0, operand_size=2),
    OpCode.OP_JUMP_IF_FALSE: Instruction(stack_effect=0, operand_size=2),
    OpCode.OP_LOOP: Instruction(stack_effect=0, operand_size=2),
    OpCode.OP_LIST: Instruction(stack_effect=+1, operand_size=1),
    OpCode.OP_GET_INDEX: Instruction(stack_effect=-1, operand_size=0),
    OpCode.OP_SET_INDEX: Instruction(stack_effect=-2, operand_size=0),
}


def takes_operand(opcode: OpCode) -> bool:
    """Indica si ``opcode`` lleva al menos un byte de operando."""
    return INSTRUCTIONS[opcode].operand_size > 0


def operand_bytes(opcode: OpCode) -> int:
    """Devuelve cuántos bytes de operando lleva ``opcode``."""
    return INSTRUCTIONS[opcode].operand_size


def stack_effect(opcode: OpCode, operand: int = 0) -> int:
    """Devuelve cuánto cambia el tamaño de la pila al ejecutar ``opcode``."""
    if opcode == OpCode.OP_LIST:
        return 1 - operand
    if opcode == OpCode.OP_CALL:
        return -operand
    return INSTRUCTIONS[opcode].stack_effect
