from pathlib import Path

import pytest
from mylox.bytecode.compiler import Compiler
from mylox.bytecode.disassembler import disassemble
from mylox.bytecode.opcodes import OpCode, stack_effect
from mylox.bytecode.vm import VM
from mylox.cli import run_actions, run_tree
from mylox.pipeline.lexer import Lexer












def test_ast_de_lectura_y_escritura(capsys):
    assert run_tree("var a = [1]; a[0] = a[0] + 1;") == 0
    tree = capsys.readouterr().out
    assert "List([Literal(1.0)])" in tree
    assert "IndexSet(" in tree
    assert "Index(" in tree






