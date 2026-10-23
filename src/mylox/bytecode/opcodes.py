"""Instrucciones de bytecode"""
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

    # Unarias
    OP_NOT = auto()
    OP_NEGATE = auto()


@dataclass(frozen=True, slots=True)
class Instruction:

    stack_effect: int
    has_operand: bool


INSTRUCTIONS: dict[OpCode, Instruction] = {
    # Las cuatro cargas empujan un valor y no consumen ninguno.
    OpCode.OP_CONSTANT: Instruction(stack_effect=+1, has_operand=True),
    OpCode.OP_TRUE: Instruction(stack_effect=+1, has_operand=False),
    OpCode.OP_FALSE: Instruction(stack_effect=+1, has_operand=False),
    OpCode.OP_NIL: Instruction(stack_effect=+1, has_operand=False),
    # Las sentencias retiran el valor que dejó la expresión que contienen.
    OpCode.OP_POP: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_PRINT: Instruction(stack_effect=-1, has_operand=False),
    # OP_RETURN termina la ejecución sin dejar la pila en un estado usable.
    OpCode.OP_RETURN: Instruction(stack_effect=0, has_operand=False),
    # Las binarias consumen dos operandos y empujan un resultado.
    OpCode.OP_EQUAL: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_GREATER: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_LESS: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_ADD: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_SUBTRACT: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_MULTIPLY: Instruction(stack_effect=-1, has_operand=False),
    OpCode.OP_DIVIDE: Instruction(stack_effect=-1, has_operand=False),
    # Las unarias reemplazan el operando por su resultado.
    OpCode.OP_NOT: Instruction(stack_effect=0, has_operand=False),
    OpCode.OP_NEGATE: Instruction(stack_effect=0, has_operand=False),
}


def takes_operand(opcode: OpCode) -> bool:
    """Indica si opcode lleva un byte de operando después del código."""
    return INSTRUCTIONS[opcode].has_operand


def stack_effect(opcode: OpCode) -> int:
    """Devuelve cuánto cambia el tamaño de la pila al ejecutar opcode"""
    return INSTRUCTIONS[opcode].stack_effect
