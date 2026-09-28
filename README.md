# mylox

Intérprete de Lox en Python — Trabajo Práctico de Lenguajes y Compiladores I (FIUBA).

Aún en construcción. Estructura e implementación propias (independiente del código de la cátedra).

## Integrantes

Camilo Sassone Irrazabal - 111135
Ulises Distefano - 111883

## Requisitos

- Python 3.12 o superior.
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias y entornos).

## Instalación

Con uv se descargan las dependencias y se crea el entorno virtual:

```sh
uv sync
```

## Uso

Desde el entorno se puede invocar la CLI:

```sh
uv run mylox
```

## Tests

La suite usa pytest y cubre el lexer, el parser, el intérprete, los ámbitos,
el impresor del árbol y la CLI:

```sh
# correr todos los tests
uv run pytest

# correr solo un archivo
uv run pytest tests/test_parser.py

# correr un test específico
uv run pytest tests/test_parser.py::test_multiplicacion_antes_que_suma

# ver detalle de cada test (verbose)
uv run pytest -v
```

Para verificar los programas de la cátedra con comparación exacta de stdout,
stderr y código de salida:

```sh
uv run python tests/strict_real_tests.py --case 1-flow.lox
uv run python tests/strict_real_tests.py
```

El verificador busca `plox/real-tests/` como repositorio hermano; se puede
indicar otra ubicación con `--test-dir`.

La integración de statements, variables, flujo, funciones y closures pasa los
cinco programas con stdout exacto, stderr vacío y código de salida 0. El script
de la cátedra también pasa; por sí solo sólo comprueba que stdout no tenga
la palabra `ERROR`.

## Decisiones de diseño

- **Hecho desde cero**. Mismo lenguaje, otra estructura, basandonos en el libro de Lox.
- Arquitectura por responsabilidad (`lexer`, `parser`, `interpreter`, `resolver`, `env`) y usamos un Visitor con `accept()` para recorrer el AST, en vez del `@singledispatchmethod` que usa el plox.
- Nodos con `@dataclass(frozen=True, slots=True)`: el AST solo guarda estructura, no datos ni ambientes.
- `nil` = `None`, `true`/`false` = `True`/`False`. Solo `nil` y `false` son falsos.
- Números siempre `float`, pero imprimen sin `.0` (`7`, no `7.0`).
- `and`/`or` que devuelven los operandos, como el libro: `true and nil` es `nil`.
- Se agregó `%` porque el fizzbuzz de la cátedra lo necesita.
- `for` se transforma en `while` + bloque: nada de nodo extra.
- Las llamadas evalúan los argumentos antes de validar la aridad, para no perder efectos.
- Los closures guardan el entorno real de la definición; un resolver (`BindingResolver`) ata cada variable a su ámbito antes de ejecutar (un `return` fuera de función falla en parseo, no en runtime).
- Errores como jerarquía propia (`ScanError`, `ParseError`, `LoxRuntimeError`); el `return` es una excepción interna, NO un error.
- CLI con códigos de salida estándar (0, 65, 70), errores en `stderr` con línea/columna, y modos `--tokens` y `--tree` para debug.
- Tests propios que comparan stdout, stderr vacío y exit 0.

## Guías del código

- [Recorrido del intérprete y Visitor](docs/interpreter.md).
- [Statements y print](docs/statements.md).
- [Variables y ámbitos](docs/variables.md).
- [Control de flujo](docs/control-de-flujo.md).
- [Funciones, retornos y closures](docs/funciones-y-closures.md).

## Integración con funciones

La rama `functions-and-closures` incorpora el trabajo de `statements-flow`.
`visit_function_decl()` guarda `interpreter.environment` en una `Function`.
`Function.call()` ejecuta el cuerpo mediante
`interpreter.execute_block(body, Env(enclosing=closure))`.
`Env.define(name: str, value)`, `Env.get(name: Token)` y
`Env.assign(name: Token, value)` son las operaciones de ámbito disponibles.
`FunctionDecl` expone `name: Token`, `parameters: list[Token]` y `body: list[Node]`,
que son los campos consumidos por `Function.call`. `BindingResolver` conserva
los vínculos léxicos de las referencias; el intérprete usa `get_local()` y
`assign_local()` para acceder al ámbito elegido.

## Benchmark

```sh
uv run python benchmarks/bench.py benchmarks/programas/suma.lox -n 20
```

El benchmark usa el mismo parseo, resolución y ejecución de programas que
la CLI. Los programas medidos deben incluir los puntos y coma de Lox.
