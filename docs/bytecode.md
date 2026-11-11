# Compilador y VM

El backend bytecode reutiliza el lexer y compila los tokens directamente,
en una pasada. Usa descenso recursivo; el compilador de la cátedra usa Pratt.
Conservamos el tree-walk para comparar las dos implementaciones.

```sh
uv run mylox programa.lox --backend bytecode
uv run mylox programa.lox --backend bytecode --debug
```

## Módulos

Dentro de `src/mylox/bytecode/`:

| Archivo | Función |
| --- | --- |
| `compiler.py` | Lee tokens y emite instrucciones |
| `chunk.py` | Guarda bytes, constantes y líneas de origen |
| `opcodes.py` | Define instrucciones, operandos y efectos sobre la pila |
| `vm.py` | Ejecuta instrucciones y administra la pila y los frames |
| `function.py` | Representa funciones, closures, frames y upvalues |
| `disassembler.py` | Muestra bytes, instrucciones y traza de ejecución |

`src/mylox/values.py` se comparte con el tree-walk: conversiones a texto,
igualdad, valor de verdad y comprobaciones de tipos. También se comparten
los objetos de clases y listas.

## Compilación

El compilador lee la gramática sin construir un AST. Comparte el parseo de
funciones y métodos, y el recorrido que encadena llamadas, propiedades e
índices. `can_assign` habilita asignaciones donde la precedencia las permite.
Mantener este recorrido y el parser del tree-walk exige pruebas de paridad.

Las variables locales ocupan slots. Un `var` nuevo se registra después de
compilar el inicializador, para permitir leer el nombre exterior. Una
redeclaración reutiliza el slot existente. Las funciones se registran antes
de compilar su cuerpo para permitir recursión. Los parámetros conservan los
slots de sus argumentos; ante un nombre repetido se usa el último.

`Chunk` deduplica constantes usando tipo y valor como clave: `1.0` y `True`
quedan separados. Conserva la línea de cada byte para informar errores.
Rechaza bytes fuera de rango, operandos incorrectos y exceso de constantes.

## Instrucciones

| Grupo | Opcodes |
| --- | --- |
| Valores y sentencias | `OP_CONSTANT`, `OP_TRUE`, `OP_FALSE`, `OP_NIL`, `OP_POP`, `OP_PRINT`, `OP_RETURN` |
| Operadores | `OP_EQUAL`, `OP_GREATER`, `OP_LESS`, `OP_GREATER_EQUAL`, `OP_LESS_EQUAL`, `OP_ADD`, `OP_SUBTRACT`, `OP_MULTIPLY`, `OP_DIVIDE`, `OP_MODULO`, `OP_NOT`, `OP_NEGATE` |
| Variables | `OP_DEFINE_GLOBAL`, `OP_GET_GLOBAL`, `OP_SET_GLOBAL`, `OP_GET_LOCAL`, `OP_SET_LOCAL` |
| Saltos | `OP_JUMP`, `OP_JUMP_IF_FALSE`, `OP_LOOP` |
| Funciones y capturas | `OP_CALL`, `OP_CLOSURE`, `OP_GET_UPVALUE`, `OP_SET_UPVALUE`, `OP_CLOSE_UPVALUE` |
| Clases | `OP_CLASS`, `OP_GET_PROPERTY`, `OP_SET_PROPERTY`, `OP_METHOD`, `OP_INHERIT`, `OP_GET_SUPER` |
| Listas | `OP_LIST`, `OP_GET_INDEX`, `OP_SET_INDEX` |

`>=` y `<=` necesitan instrucciones propias: con `NaN`, negar `<` o `>`
produce otro resultado. Conservamos los valores IEEE de Python: un
desbordamiento puede producir infinito, e infinito menos infinito produce
`NaN`. Las comparaciones de orden con `NaN` son falsas.

## Ejecución y capturas

La VM administra sus propios frames. Al retornar, cierra las capturas del
frame que termina y elimina su tramo de la pila. Los upvalues abiertos se
indexan por posición; las capturas del llamador permanecen abiertas.

Ante un error, cierra las capturas pendientes y descarta los frames. Esto
permite continuar en el REPL con los mismos globales y funciones. La siguiente
entrada empieza con la pila vacía. La memoria de objetos y ciclos queda a
cargo de Python.

Después de perfilar, guardamos una `memoryview` de solo lectura y el pool de
constantes en cada closure; los frames reutilizan esas referencias. El bucle
lee bytes directamente, evitando llamadas a `Chunk.read()`, `constant()` y
`__len__()` por instrucción. El chunk se termina antes de crear los closures
y no cambia durante la ejecución.

El frame, el código y las operaciones frecuentes de pila se guardan en
variables locales del bucle. `push` usa `list.append`; `pop` y `peek` validan
que haya elementos. Los opcodes son `IntEnum`, comparables con el byte leído.
Los resultados están en [benchmarks](benchmarks.md).

## Límites

- Hasta 256 constantes por chunk y operandos de un byte para locales, upvalues y argumentos.
- Saltos de hasta 65535 bytes; superar el límite da error de compilación.
- Hasta 255 elementos por literal de lista; `push` permite seguir agregando.
- Hasta 1024 frames, incluido el script; superar el límite da error de Lox.

El tree-walk y ambos frontends siguen sujetos a la recursión de Python. La
CLI captura ese límite y lo informa sin traceback.

`OP_INVOKE` y `OP_SUPER_INVOKE` están reservados: las llamadas a métodos usan
acceso a propiedad y `OP_CALL`. `OP_PRINT_DEC` no está implementado.
