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

La suite de tests usa pytest y cubre el lexer, el parser y el impresor del árbol:

```sh
# correr todos los tests
uv run pytest

# correr solo un archivo
uv run pytest tests/test_parser.py

# correr un test específico
uv run pytest tests/test_parser.py::test_precedencia_multiplicacion_antes_que_suma

# ver detalle de cada test (verbose)
uv run pytest -v
```
