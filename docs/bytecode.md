# Backend bytecode de mylox

## Qué es

El backend bytecode es la segunda implementación de Lox en mylox, agregada para
la Entrega Final del TP. Reutiliza el lexer y las reglas de precedencia del
parser, y agrega un compilador single-pass y una máquina virtual con pila.

## Cómo usarlo

```sh
# Ejecutar un programa con el backend bytecode
uv run mylox programa.lox --backend bytecode

# Modo de depuración: muestra RAW BYTES, COMPILETIME y RUNTIME
uv run mylox programa.lox --backend bytecode --debug
```

## Arquitectura

```
src/mylox/bytecode/
    opcodes.py       # enum OpCode + tabla de stack effects
    chunk.py         # Chunk: bytes + constantes + líneas (encapsulado)
    compiler.py      # Compiler: tokens → Chunk (single-pass, recursive descent)
    vm.py            # VM: ip + stack + dispatch loop
    disassembler.py  # RAW BYTES, COMPILETIME, RUNTIME
    function.py      # Function, Closure, CallFrame, Upvalue
    values.py        # (en src/mylox/) stringify, is_truthy, is_number, is_string, is_equal
```

## Diferencias con plox (cátedra)

- **Parser**: recursive descent (ploxb usa Pratt parser con tabla de precedencias).
- **Chunk**: encapsulado con `_bytes`/`_lines`/`_constants` privados, tabla de líneas para errores con posición, dedup de constantes con clave type-aware (`1.0 != True`).
- **VM**: `VM(chunk)` constructor, `VMRuntimeError` con línea, `values.py` compartido con el tree-walk.
- **Disassembler**: módulo aparte, retorna strings, 3 vistas. Sin color (ploxb usa termcolor).
- **Validaciones**: `CompileError` si un byte sale de rango, si falta/sobra operando, o si el pool supera 256 entradas.
- **OpCodes propios**: `OP_MODULO` (ploxb también lo tiene, pero mylox lo usa como "cosa extra"), `OP_SUBTRACT` (ploxb tiene el typo `OP_SUBSTRACT`).

## OpCodes implementados

### Expresiones (Tema 10)
`OP_CONSTANT`, `OP_TRUE`, `OP_FALSE`, `OP_NIL`, `OP_POP`, `OP_PRINT`, `OP_RETURN`,
`OP_EQUAL`, `OP_GREATER`, `OP_LESS`, `OP_ADD`, `OP_SUBTRACT`, `OP_MULTIPLY`,
`OP_DIVIDE`, `OP_MODULO`, `OP_NOT`, `OP_NEGATE`

### Variables (Tema 11)
`OP_DEFINE_GLOBAL`, `OP_GET_GLOBAL`, `OP_SET_GLOBAL`, `OP_GET_LOCAL`, `OP_SET_LOCAL`

### Control de flujo (Tema 11)
`OP_JUMP`, `OP_JUMP_IF_FALSE`, `OP_LOOP`

### Funciones (Tema 12)
`OP_CALL`, `OP_CLOSURE`

### Closures (Tema 13)
`OP_GET_UPVALUE`, `OP_SET_UPVALUE`, `OP_CLOSE_UPVALUE`

## Lo que NO tiene (pendiente)

- **Clases y herencia (OOP)**: requisito de la Entrega Final, no se ve en clase. Requiere OpCodes `OP_CLASS`, `OP_GET_PROPERTY`, `OP_SET_PROPERTY`, `OP_METHOD`, `OP_INHERIT`, `OP_GET_SUPER`, `OP_INVOKE`, `OP_SUPER_INVOKE`.
- **Variables, control de flujo y funciones** están implementados; faltan optimizaciones (Tema 12, diapo 189-202).
- **OP_PRINT_DEC**: extra de ploxb que no es Lox estándar; no se implementa.
