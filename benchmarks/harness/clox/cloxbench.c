/* cloxbench.c — harness de medición para clox (Crafting Interpreters, C).
 *
 * Este archivo es NUESTRO: mide el tiempo de compilación a bytecode más la
 * ejecución en la VM, sin incluir el arranque del proceso ni la lectura de
 * archivo, para poder compararlo con las demás implementaciones.
 *
 * `interpret(source)` es la misma entrada que usa main.c: compila la fuente y
 * la ejecuta en la VM. Se descarta el valor devuelto porque el programa de
 * benchmark no debe producir errores (el script de medición ya verificó la
 * equivalencia de salida).
 *
 * Debe compilarse junto a las fuentes de clox; `initVM()` y `freeVM()` viven
 * en vm.c (main.c es la CLI y no se incluye).
 *
 * La salida del programa se captura en un archivo temporal para imprimirla
 * una sola vez: si no, cada iteración repetiría la salida y el benchmark no
 * podría usarla para verificar la equivalencia entre implementaciones. Los
 * tiempos van por stderr para no mezclarse con la salida.
 */

/* fileno() y dup2() son POSIX; con -std=c99 hay que pedirlo explícitamente. */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#include "vm.h"
int main(int argc, char** argv) {
    if (argc < 4) {
        fprintf(stderr, "uso: cloxbench <archivo.lox> <calentamiento> <repeticiones>\n");
        return 64;
    }

    FILE* file = fopen(argv[1], "rb");
    if (file == NULL) {
        fprintf(stderr, "no se pudo abrir: %s\n", argv[1]);
        return 74;
    }

    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    fseek(file, 0, SEEK_SET);

    char* source = malloc((size_t)length + 1);
    if (source == NULL) {
        fclose(file);
        return 74;
    }
    /* El resultado de fread se verifica indirectamente por el '\0' agregado. */
    size_t read_bytes = fread(source, 1, (size_t)length, file);
    source[read_bytes] = '\0';
    fclose(file);

    int warmup = atoi(argv[2]);
    int reps = atoi(argv[3]);

    initVM();

    /* Se desvía stdout a un archivo temporal para capturar la salida. */
    FILE* captura = tmpfile();
    fflush(stdout);
    int guardado = dup(fileno(stdout));
    if (captura == NULL || guardado < 0) {
        fprintf(stderr, "no se pudo capturar la salida\n");
        return 74;
    }
    dup2(fileno(captura), fileno(stdout));

    /* Una primera ejecución dedicada a capturar la salida del programa. */
    interpret(source);
    fflush(stdout);

    long salida_long = ftell(captura);
    if (salida_long < 0) {
        salida_long = 0;
    }
    rewind(captura);
    char* salida = malloc((size_t)salida_long + 1);
    if (salida == NULL) {
        fprintf(stderr, "no se pudo reservar memoria para la salida\n");
        return 74;
    }
    size_t leidos = fread(salida, 1, (size_t)salida_long, captura);
    salida[leidos] = '\0';

    /* El resto de las ejecuciones no interesa su salida, así que se descarta. */
    fflush(stdout);
    rewind(captura);

    for (int i = 0; i < warmup; i++) {
        interpret(source);
    }

    for (int i = 0; i < reps; i++) {
        clock_t start = clock();
        interpret(source);
        clock_t end = clock();

        double ms = (double)(end - start) * 1000.0 / CLOCKS_PER_SEC;
        fprintf(stderr, "BENCH_MS %.3f\n", ms);
    }

    /* Se restaura stdout y se vuelca la salida capturada. */
    fflush(stdout);
    dup2(guardado, fileno(stdout));
    close(guardado);

    fputs(salida, stdout);

    fclose(captura);
    free(salida);
    freeVM();
    free(source);
    return 0;
}
