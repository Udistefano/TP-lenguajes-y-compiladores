#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "vm.h"

static int run_once(const char* source) {
    initVM();
    InterpretResult result = interpret(source);
    freeVM();
    return result == INTERPRET_OK;
}

static double milliseconds(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec * 1000.0 + now.tv_nsec / 1e6;
}

int main(int argc, char** argv) {
    if (argc != 4) return 64;
    int warmup = atoi(argv[2]);
    int repetitions = atoi(argv[3]);
    if (warmup < 0 || repetitions < 1) return 64;

    FILE* file = fopen(argv[1], "rb");
    if (file == NULL) return 74;
    fseek(file, 0, SEEK_END);
    long length = ftell(file);
    if (length < 0) return 74;
    rewind(file);
    char* source = malloc((size_t)length + 1);
    if (source == NULL) return 74;
    if (fread(source, 1, (size_t)length, file) != (size_t)length) return 74;
    source[length] = '\0';
    fclose(file);

    FILE* capture = tmpfile();
    int saved_stdout = dup(fileno(stdout));
    if (capture == NULL || saved_stdout < 0) return 74;
    if (setvbuf(capture, NULL, _IONBF, 0) != 0) return 74;
    fflush(stdout);
    if (dup2(fileno(capture), fileno(stdout)) < 0) return 74;
    if (!run_once(source)) return 70;
    fflush(stdout);
    long output_length = lseek(fileno(capture), 0, SEEK_CUR);
    if (output_length < 0) return 74;
    char* output = malloc((size_t)output_length + 1);
    if (output == NULL) return 74;
    rewind(capture);
    if (fread(output, 1, (size_t)output_length, capture) != (size_t)output_length) return 74;
    output[output_length] = '\0';
    char* observed = malloc((size_t)output_length + 1);
    if (observed == NULL) return 74;

    for (int i = -warmup; i < repetitions; i++) {
        rewind(capture);
        double start = milliseconds();
        int ok = run_once(source);
        double elapsed = milliseconds() - start;
        fflush(stdout);
        if (!ok) return 70;
        long observed_length = lseek(fileno(capture), 0, SEEK_CUR);
        if (observed_length != output_length) {
            fprintf(stderr, "La salida cambió de longitud: %ld -> %ld\n", output_length, observed_length);
            return 70;
        }
        rewind(capture);
        if (fread(observed, 1, (size_t)output_length, capture) != (size_t)output_length) return 74;
        if (memcmp(output, observed, (size_t)output_length) != 0) {
            fprintf(stderr, "La salida cambió entre muestras\n");
            return 70;
        }
        if (i >= 0) fprintf(stderr, "BENCH_MS %.6f\n", elapsed);
    }

    if (dup2(saved_stdout, fileno(stdout)) < 0) return 74;
    close(saved_stdout);
    fputs(output, stdout);
    fclose(capture);
    free(observed);
    free(output);
    free(source);
    return 0;
}
