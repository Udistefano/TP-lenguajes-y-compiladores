"""Instrucciones de bytecode de mylox y sus efectos sobre la pila"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

MAX_CONSTANT_INDEX = 255


class OpCode(Enum):
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

    # Saltos
    OP_JUMP = auto()
    OP_JUMP_IF_FALSE = auto()
    OP_LOOP = auto()


@dataclass(frozen=True, slots=True)
class Instruction:
    stack_effect: int
    has_operand: bool


INSTRUCTIONS: dict[OpCode, Instruction] = {
    OpCode.OP_CONSTANT: Instruction(stack_effect=+1, has_operand=True),
    OpCode.OP_TRUE: Instruction(stack_effect=+1, has_operand=False),
    OpCode.OP_FALSE: Instruction(stack_effect=+1, has_operand=False),
    OpCode.OP_NIL: Instruction(stack_effect=+1, has_operand=False),
    OpCode.OP_DEFINE_GLOBAL: Instruction(stack_effect=-1, has_operand=True),
    OpCode.OP_GET_GLOBAL: Instruction(stack_effect=+1, has_operand=True),
    OpCode.OP_SET_GLOBAL: Instruction(stack_effect=0, has_operand=True),
    OpCode.OP_GET_LOCAL: Instruction(stack_effect=+1, has_operand=True),
    OpCode.OP_SET_LOCAL: Instruction(stack_effect=0, has_operand=True),
    OpCode.OP_POP: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_PRINT: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_RETURN: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_EQUAL: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_GREATER: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_LESS: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_ADD: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_SUBTRACT: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_MULTIPLY: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_DIVIDE: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_MODULO: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_NOT: Instruction(stack_effect=0, has_operand=False),
    OpCode.OP_NEGATE: Instruction(stack_effect=0, has_operand=False),
    OpCode.OP_CALL: Instruction(stack_effect=-1, has_operand=True),
    OpCode.OP_CLOSURE: Instruction(stack_effect=+1, has_operand=True),
    OpCode.OP_GET_UPVALUE: Instruction(stack_effect=+1, has_operand=True),
    OpCode.OP_SET_UPVALUE: Instruction(stack_effect=0, has_operand=True),
    OpCode.OP_CLOSE_UPVALUE: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_JUMP: Instruction(stack_effect=0, has_operand=True),
    OpCode.OP_JUMP_IF_FALSE: Instruction(stack_effect=0, has_operand=True),
    OpCode.OP_LOOP: Instruction(stack_effect=0, has_operand=True),
}


def takes_operand(opcode: OpCode) -> bool:
    """Indica si opcode lleva un byte de operando después del código."""
    return INSTRUCTIONS[opcode].has_operand


def stack_effect(opcode: OpCode) -> int:
    """Devuelve cuánto cambia el tamaño de la pila al ejecutar opcode"""
    return INSTRUCTIONS[opcode].stack_effect
