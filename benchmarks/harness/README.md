# Harnesses de medición

Estos programas miden dentro del proceso del runtime, excluyendo la lectura
de archivos y el arranque del proceso.

## Corrida de la entrega final

`benchmarks/external.py` ejecuta los harnesses de C y JavaScript. Usa las mismas
repeticiones, calentamiento y afinidad de CPU que `benchmarks/compare.py`.

`clox/cloxbench.c` se compila junto con las fuentes oficiales de clox,
excluyendo `main.c`. Recibe `<archivo.lox> <calentamiento> <repeticiones>`.
Cada muestra incluye `initVM()`, `interpret(source)` y `freeVM()`, con un reloj
monótono de pared (`CLOCK_MONOTONIC`). El código Lox se compila nuevamente y
la VM comienza vacía en cada iteración.

La salida se captura en un `tmpfile()`. Una ejecución inicial establece la
salida de referencia; todas las demás deben coincidir. Se mide el formateo y
la escritura al buffer de stdio; el vaciado y la comparación quedan fuera del
cronómetro. Se emite la salida una vez por stdout y una línea
`BENCH_MS <milisegundos>` por muestra en stderr. Los errores del intérprete
producen un código de salida no nulo y detienen la comparación.

`native.js` recibe `<archivo.js> <calentamiento> <repeticiones>` y requiere
`node --expose-gc`. Crea un `vm.Script` y un contexto nuevo por muestra. Separa
compilación y ejecución; esta última incluye crear el contexto. Captura
`print` en memoria y verifica que la salida no cambie entre muestras. Devuelve
un JSON con tiempos y versiones de Node/V8. La recolección explícita queda
fuera del intervalo; no se desactiva el GC durante la ejecución.

`external.py` contrasta las salidas con resultados esperados, además de los
chequeos internos. Las fuentes de clox y el ejecutable se crean en un único
directorio temporal, cuyo nombre y eliminación se registran en el JSON de
resultados. El archivo anónimo de captura se cierra al terminar el harness.

## Harness del parcial

`jlox/Bench.java` conserva la medición en proceso del intérprete Java:
scanner, parser, resolver e intérprete. Vive en el package
`com.craftinginterpreters.lox` porque las clases son package-private.
Puede usarse con `benchmarks/setup.sh` y `benchmarks/bench.py` si hay un JDK.
No se incluyó en la corrida final porque el entorno Linux usado no tenía Java.

Tres iteraciones de calentamiento reducen algunos efectos iniciales, pero
no garantizan un estado estable del JIT de Java o JavaScript.
