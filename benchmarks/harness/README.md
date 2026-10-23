# Harnesses de medición

Estos archivos son **nuestros**: son instrumentación de medición, no
implementaciones de Lox. Sirven para ejecutar un programa `.lox` dentro del
proceso de la implementación medida y reportar cuánto tardó, de modo que la
comparación con `mylox` y `plox` sea justa (sin incluir el arranque del
proceso ni de la JVM).

## Por qué hacen falta

`mylox` y `plox` se importan directamente desde Python, así que se miden en
proceso sin más. `jlox` (Java) y `clox` (C) son programas cerrados: para
medirlos sin el costo de arranque hay que llamar a su API desde un programa
propio.

- `jlox/Bench.java` — replica el flujo de `Lox.run()` (scan → parse → resolve →
  interpret). Tiene que vivir en el package `com.craftinginterpreters.lox`
  porque las clases del intérprete son *package-private*.
- `clox/cloxbench.c` — llama a `interpret(source)`, que compila la fuente a
  bytecode y la ejecuta en la VM. Se compila junto a las fuentes de clox pero
  **sin** `main.c` (ese archivo es la CLI y trae su propio `main`).

## Cómo se compilan

`../setup.sh` se encarga: clona el repositorio del libro y compila ambos
harnesses en `../.cache/` (ignorado por git).

```sh
benchmarks/setup.sh
```

Para compilar a mano:

```sh
# jlox
javac -d benchmarks/.cache/jlox-build \
    benchmarks/.cache/craftinginterpreters/java/com/craftinginterpreters/lox/*.java \
    benchmarks/harness/jlox/Bench.java

# clox
C=benchmarks/.cache/craftinginterpreters/c
gcc -std=c99 -O2 -I"$C" -o benchmarks/.cache/cloxbench \
    benchmarks/harness/clox/cloxbench.c \
    "$C/vm.c" "$C/compiler.c" "$C/chunk.c" "$C/memory.c" "$C/object.c" \
    "$C/scanner.c" "$C/table.c" "$C/value.c" "$C/debug.c" -lm
```

## Formato de salida

Ambos harnesses reciben `<archivo.lox> <calentamiento> <repeticiones>`:

- el **calentamiento** son ejecuciones que se descartan, hechas dentro del
  mismo proceso para que el JIT de la JVM o el estado de la VM queden
  estables (igual que el warmup de Python);
- las **repeticiones** son las que se miden.

La salida del programa va por **stdout** (una sola vez, de la primera
ejecución) y los tiempos por **stderr**, para que no se mezclen:

```text
$ benchmarks/.cache/cloxbench benchmarks/programas/primos.lox 3 3
62
```

```text
$ benchmarks/.cache/cloxbench benchmarks/programas/primos.lox 3 3 2>&1 >/dev/null
BENCH_MS 1.104
BENCH_MS 1.136
BENCH_MS 1.162
```

El benchmark (`benchmarks/bench.py`) lee las líneas `BENCH_MS` del stderr para
armar las estadísticas y el stdout para verificar la equivalencia de salida.
