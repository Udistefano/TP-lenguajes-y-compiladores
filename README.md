# mylox

Intérprete de Lox en Python — Trabajo Práctico de Lenguajes y Compiladores I (FIUBA).

Aún en construcción. Estructura e implementación propias (independiente del código de la cátedra).

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

Estado de esta rama: `1-flow.lox` pasa la verificación estricta. Los otros cuatro
programas requieren completar e integrar funciones y closures. Que el script
de la cátedra muestre «Todo OK» no confirma salida ni código de salida correctos.

## Guías del código

- [Recorrido del intérprete y Visitor](docs/interpreter.md).
- [Statements y print](docs/statements.md).
- [Variables y ámbitos](docs/variables.md).
- [Control de flujo](docs/control-de-flujo.md).

## Integración con funciones

La rama `statements-flow` implementa sentencias, variables y control de flujo.
Para ejecutar una función, la rama de funciones puede guardar
`interpreter.environment` al declararla y llamar a
`interpreter.execute_block(body, Env(enclosing=closure))` al invocarla.
`Env.define(name: str, value)`, `Env.get(name: Token)` y
`Env.assign(name: Token, value)` son las operaciones de ámbito disponibles.
La declaración de función debe exponer `name: Token`, `parameters: list[Token]`
y `body: list[Node]`, que son los campos consumidos por `Function.call` en la
rama `origin/functions-and-closures` examinada. La resolución léxica de
referencias dentro de closures deberá conservar el vínculo con el ámbito
visible en el punto de declaración.
