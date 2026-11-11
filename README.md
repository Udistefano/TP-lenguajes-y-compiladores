# mylox

Lox en Python para Lenguajes y Compiladores I (FIUBA). Incluye el intérprete
tree-walk del parcial y un compilador a bytecode con VM, clases con herencia
y listas mutables.

- Camilo Sassone Irrazabal — 111135
- Ulises Distefano — 111883

## Instalación y uso

Requiere Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run mylox programa.lox
uv run mylox programa.lox --backend bytecode
```

Sin archivo abre el REPL. Conserva variables y funciones entre entradas;
cada entrada debe ser una sentencia o declaración completa. Después de un
error se puede seguir usando el estado anterior, incluidos los efectos que
ocurrieron antes del error.

`--tokens` muestra los tokens, `--tree` el AST y `--backend bytecode --debug`
el código generado y su ejecución. Los errores salen por stderr: código 65
para errores de sintaxis o compilación y 70 para errores de ejecución.

## Pruebas

```sh
uv run pytest
uv run pytest tests/test_lists.py
uv run python tests/strict_real_tests.py
```

El verificador estricto ejecuta los cinco programas de la cátedra en ambos
backends y comprueba stdout exacto, stderr vacío y código de salida 0. Busca
`../plox/real-tests/`; acepta otra ruta con `--test-dir` y permite filtrar con
`--backend bytecode` o `--case 1-flow.lox`.

Para preparar esa referencia en un checkout nuevo:

```sh
git clone https://github.com/FdelMazo/plox.git ../plox
git -C ../plox checkout --detach 734f4d2adaf708c503dc5d17e88315e273c2f0ab
```

La última [verificación](benchmarks/results/review-verification.txt) tiene
469 tests aprobados, los 10 casos de la cátedra y las tres demos con la misma
salida en ambos backends.

## Del parcial al bytecode

Conservamos el tree-walk y compartimos lexer, operaciones sobre valores,
clases y listas. El tree-walk construye un AST con dataclasses y lo recorre
con Visitor y `accept()`, mientras que plox usa `singledispatchmethod`.
El compilador lee tokens por descenso recursivo y emite bytecode en una
pasada; el de la cátedra usa Pratt.

El tree-walk guarda variables en ambientes enlazados. La VM usa slots y
upvalues para las capturas, además de frames propios para las llamadas.
Python administra la memoria en ambos casos. Al mantener dos lectores de
la gramática, necesitamos pruebas que comparen su comportamiento.

Los valores de Python requieren algunas adaptaciones: en Lox solo `nil` y
`false` son falsos, y los booleanos no se aceptan como números. Usamos `float`
para los números y omitimos `.0` al imprimir enteros. `and` y `or` devuelven
operandos; división y módulo por cero producen errores de Lox.

Conservamos las reglas del parcial para inicializadores y redeclaraciones:
el inicializador puede leer el nombre exterior y una redeclaración reemplaza
la variable del mismo ámbito. Estas diferencias con el libro se explican en
[variables](docs/variables.md).

## Extensiones y ejemplos

Las clases tienen herencia, `this`, `super`, constructores y métodos ligados.
Las [listas](docs/listas.md) son el extra de la final: permiten indexar,
modificar, agregar y extraer elementos.

```lox
var equipo = ["Ada", "Luz"];
equipo.push("Sol");
equipo[0] = "Ana";
print equipo.length;
print equipo.pop();
```

[combate.lox](examples/combate.lox) usa una lista de personajes, herencia y
ataques polimórficos. Elimina a los derrotados y termina con `Ganador: Ada`.
También hay ejemplos de Fibonacci con memoización y primos hasta 100.

```sh
uv run mylox examples/combate.lox
uv run mylox examples/combate.lox --backend bytecode
uv run mylox examples/fibonacci_memo.lox
uv run mylox examples/primos_hasta_100.lox
```

## Benchmarks

El [informe](docs/benchmarks.md) compara el parcial, los dos backends, la VM
antes y después de optimizar, plox, clox y los mismos algoritmos en Python y
JavaScript. Incluye gráficos, datos y comandos para reproducir cada medición.

Para comparar rápidamente los backends del checkout actual:

```sh
uv run python benchmarks/bench.py --implementaciones mylox,mylox-bytecode -n 20
```

Los gráficos usan el grupo opcional de dependencias `bench`:

```sh
uv sync --group bench
```

## Documentación

- [Lexer, parser y Visitor](docs/interpreter.md).
- [Sentencias y print](docs/statements.md).
- [Variables y ámbitos](docs/variables.md).
- [Control de flujo](docs/control-de-flujo.md).
- [Funciones y closures](docs/funciones-y-closures.md).
- [Compilador y VM](docs/bytecode.md).
- [Clases y herencia](docs/oop.md).
- [Listas](docs/listas.md).
