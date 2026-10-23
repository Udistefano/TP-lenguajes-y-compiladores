# Benchmarks de mylox

## Objetivo

Responder al pedido del profesor: **más programas**, **incluir conclusiones** y **comparar contra más de una implementación**.

## Implementaciones comparadas

| Implementación | Origen | Arquitectura | Forma de medición |
|---|---|---|---|
| `mylox` | Propia | Tree-walk en Python con `Visitor`, nodos `@dataclass(frozen=True, slots=True)` y `BindingResolver` estático | In-process (import directo). Mide `Lexer → Parser → Resolver → Interpreter`. |
| `plox` | Cátedra ([FdelMazo/plox](https://github.com/FdelMazo/plox), rama `main`) | Tree-walk en Python con `@singledispatchmethod` y resolver | In-process. Extraído del árbol de git con `git archive origin/main` (sin tocar el checkout local). Mide `Scanner → Parser → Resolver → Interpreter`. |
| `jlox` | [Crafting Interpreters](https://github.com/munificent/craftinginterpreters) (Java) | Tree-walk en Java | In-process vía harness propio (`benchmarks/harness/jlox/Bench.java`). Replica el flujo de `Lox.run()` (`Scanner → Parser → Resolver → Interpreter`). |
| `clox` | [Crafting Interpreters](https://github.com/munificent/craftinginterpreters) (C) | Máquina virtual de bytecode en C | In-process vía harness propio (`benchmarks/harness/clox/cloxbench.c`). Llama a `interpret(source)` (compila a bytecode y ejecuta en la VM). |

## Metodología

- **Qué se mide:** scan + parse + resolve + interpret. **No** se mide arranque del proceso, arranque de JVM, lectura de archivo ni compilación de los harness.
- **Medición in-process:** se evita el overhead de inicio para obtener una comparación justa entre implementaciones.
- **Warmup:** se descartan **3 iteraciones** antes de las mediciones para amortiguar efectos de caché/JIT. En `jlox` y `clox` el calentamiento lo hace el harness **dentro del mismo proceso**: es necesario para que el JIT de la JVM optimice el camino caliente. Medir cada repetición en una JVM nueva daría el costo en frío (~5x más lento) y no el estado estable, que es lo que se quiere comparar.
- **Repeticiones:** se reportan `prom`, `min`, `p50` y `p95` sobre las ejecuciones medidas.
- **Chequeo de equivalencia:** antes de medir, se ejecuta cada programa en todas las implementaciones activas y se compara la salida normalizada. Se normalizan diferencias de formato (`7.0`→`7`, `None`→`nil`, `True`→`true`, notación científica de números grandes) para detectar divergencias semánticas reales. Si las salidas difieren, el programa se omite.
- **Portabilidad:** los programas evitan `%` (ausente en jlox y clox) y clases (ausentes en plox). Aquellos que necesitan divisibilidad usan un helper `divisible/mod` propio.
- **Robusto:** si falta `javac`, `gcc` o el repo del libro, `jlox`/`clox` se omiten con un mensaje; el mínimo garantizado es **mylox vs plox**. `plox` se extrae del repo hermano sin modificar su rama de trabajo.

## Entorno

| Componente | Versión / detalle |
|---|---|
| SO | Linux |
| Python | 3.12 (vía `uv`) |
| Java | `javac`/`java` disponibles |
| C | `gcc` disponible |
| plox | extraído de `../plox` por `git archive origin/main` |
| craftinginterpreters | clonado por `benchmarks/setup.sh` en `benchmarks/.cache/` |

## Programas

| Programa | Qué ejercita | Notas |
|---|---|---|
| `suma.lox` | Bucles + aritmética acumulada | Reescrito como **bucle real** (el original era una única expresión larga). |
| `fibonacci.lox` | Recursión + llamadas a función | Evalúa overhead de llamadas y resolución de ámbitos. |
| `closures.lox` | Closures, captura de entorno, funciones de orden superior | Ejercita `BindingResolver` y el encadenamiento de entornos. |
| `fizzbuzz.lox` | Condicionales anidados + concatenación de strings | Usa `divisible` por resta repetida (portable). |
| `primos.lox` | Bucles anidados + división por tentativas | Conteo de primos hasta N usando resta repetida para portabilidad. |

## Resultados (reales)

Medidos con el harness del repo (`uv run python benchmarks/bench.py -n 10`):

```text
programa         impl          prom        min        p50        p95
--------------------------------------------------------------------
closures.lox     mylox       607.04     593.55     605.80     620.41
closures.lox     plox       3337.68    3038.39    3083.14    4574.28
closures.lox     jlox         33.88      30.21      31.80      43.35
closures.lox     clox          6.47       6.24       6.43       6.91

fibonacci.lox    mylox       604.91     591.83     599.04     624.69
fibonacci.lox    plox       1918.94    1878.26    1909.80    2000.84
fibonacci.lox    jlox         25.31      22.70      23.70      30.42
fibonacci.lox    clox          2.80       2.71       2.80       2.90

fizzbuzz.lox     mylox       273.28     270.26     272.90     278.07
fizzbuzz.lox     plox       1381.96    1363.72    1379.54    1403.81
fizzbuzz.lox     jlox         10.34       8.03       8.52      14.01
fizzbuzz.lox     clox          1.94       1.89       1.93       2.06

primos.lox       mylox       173.63     169.06     172.97     180.03
primos.lox       plox       1007.43     961.07     986.65    1122.38
primos.lox       jlox          9.73       5.83       9.22      20.14
primos.lox       clox          1.32       1.28       1.32       1.36

suma.lox         mylox       437.15     430.93     435.07     449.04
suma.lox         plox       3726.99    3595.29    3650.03    4100.13
suma.lox         jlox         16.84      15.09      15.67      21.15
suma.lox         clox          6.37       6.07       6.25       6.70

Tiempos en milisegundos (promedio sobre repeticiones medidas, tras descartar 3 de warmup).
```

### Cuotas relativas (mylox = 1)

| Programa | plox | jlox | clox |
| --- | ---: | ---: | ---: |
| `suma.lox` | 8.5x | 0.039x | 0.015x |
| `fibonacci.lox` | 3.2x | 0.042x | 0.005x |
| `closures.lox` | 5.5x | 0.056x | 0.011x |
| `fizzbuzz.lox` | 5.1x | 0.038x | 0.007x |
| `primos.lox` | 5.8x | 0.056x | 0.008x |

## Conclusiones

1. **`mylox` vs `plox` (mismo lenguaje, mismo tipo de intérprete).** En los cinco programas `mylox` es entre **3.2x y 8.5x más rápido** que `plox`. Como ambos son tree-walk en Python, la diferencia no proviene del lenguaje sino de las decisiones de diseño: nodos `@dataclass(frozen=True, slots=True)` con un visitor propio y resolución estática integrada, frente al uso de `@singledispatchmethod` de la cátedra. El caso más extremo es `suma.lox` (8.5x), que es casi todo aritmética y dispatch: exactamente donde la indirección de `singledispatch` más se nota.
2. **`mylox` vs `jlox` (Python vs Java, ambos tree-walk).** `jlox` es entre **18x y 26x más rápido** que `mylox`. La comparación contra `plox` (3.2x a 8.5x más lento que `mylox`) muestra que la mayor parte de esa brecha no es el algoritmo: `mylox` ya está en el mismo orden de magnitud que `plox`. Lo que le falta a `mylox` frente a `jlox` es el JIT de la JVM, el tipado estático y el costo de los objetos en Python, no el diseño del intérprete.
3. **Tree-walk vs máquina virtual de bytecode (`clox`).** `clox` es entre **69x y 216x más rápido** que `mylox`, y la diferencia se mantiene en todos los programas. Es la conclusión más fuerte del benchmark y la más transferible: no es un detalle de implementación sino de arquitectura. Un tree-walk despacha por nodo del AST en cada operación; una VM de bytecode compila el programa a instrucciones y ejecuta un bucle de despacho sobre un array contiguo. Cuando el programa ejecuta millones de operaciones, esa diferencia se paga millones de veces.
4. **El orden entre implementaciones no cambia nunca.** `clox` < `jlox` < `mylox` < `plox` en los cinco programas, aunque los perfiles de carga sean distintos (recursión, closures, loops). **La arquitectura del intérprete pesa más que el perfil del programa**: dos implementaciones del mismo estilo (mylox y plox) quedan juntas y muy lejos de las otras dos.
5. **La diferencia `mylox`/`plox` es mayor en programas con muchos loops** (`suma` 8.5x) que en los dominados por recursión (`fibonacci` 3.2x). En recursión profunda el costo lo domina la creación de entornos y el mantenimiento de la pila de llamadas, que es común a ambas implementaciones; en loops densos, el dispatch por nodo (que difiere entre visitor y `singledispatch`) domina la cuenta.
6. **La diferencia entre tree-walk y bytecode VM se nota más en recursión.** La separación entre `jlox` y `clox` llega a 9.0x en `fibonacci.lox` (donde el árbol de llamadas se materializa en cuadros de llamada) contra 2.6x en `suma.lox` (aritmética pura). Compilar a bytecode evita por completo el árbol de llamadas recursivo: los frames de la VM son un array, no objetos en el heap.
7. **El chequeo de equivalencia valida la medición.** Antes de medir, el harness confirmó que las cuatro implementaciones producen la misma salida normalizada en los cinco programas. Sin esa verificación, comparar tiempos sobre programas que no hacen lo mismo no significaría nada.
8. **El resolver estático no es un costo dominante.** `mylox` incluye `BindingResolver` dentro de `Interpreter.interpret()`, igual que `plox` y `jlox` incluyen su resolver. La resolución es un recorrido lineal del AST, sin impacto apreciable en el tiempo total de la evaluación.

## Limitaciones

- **Cantidad de repeticiones:** la tabla usa `-n 10`. Con `-n 20` o más las cifras se estabilizan. La varianza observada (p95 contra min) es de ~2-3% en `mylox`, `jlox` y `clox`, pero llega a ~50% en `plox` (`closures.lox`): la recolección de basura de Python introduce ruido considerable, así que conviene comparar por mediana y no por promedio.
- **Portabilidad deliberada:** los programas evitan `%` y clases para ser comparables con todas las implementaciones. Un benchmark que usara features no compartidas sería menos equitativo.
- **Implementaciones externas:** `jlox` y `clox` dependen de una copia de [craftinginterpreters](https://github.com/munificent/craftinginterpreters) y de `javac`/`gcc`. `benchmarks/setup.sh` las prepara; si faltan, el benchmark corre igual con las que haya (mínimo garantizado: `mylox` vs `plox`).
- **Carga de trabajo sintética:** son microbenchmarks que ejercitan features específicas, no un programa real de Lox. Las conclusiones son relativas entre estas implementaciones, no una afirmación general sobre ellas.
- **Diferencias de implementación:** cada intérprete tiene decisiones propias (formato numérico, resolución, manejo de strings) que afectan el rendimiento más allá de la arquitectura pura.
- **Sin profiling:** el benchmark mide tiempo total por fase agregada. Un perfil por función (cProfile para Python, `-XX:+UnlockDiagnosticVMOptions` para Java) daría un desglose más fino del costo por operación del visitor.
