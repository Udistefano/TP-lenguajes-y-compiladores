// Bench.java — harness de medición para jlox (Crafting Interpreters, Java).
//
// Este archivo es NUESTRO: mide el tiempo de ejecución de jlox sin incluir el
// arranque de la JVM ni la lectura de archivo, para poder compararlo con las
// demás implementaciones en igualdad de condiciones.
//
// Replica el flujo de Lox.run (scan -> parse -> resolve -> interpret) porque
// ese método es privado, y vive en el package com.craftinginterpreters.lox
// porque las clases del intérprete son package-private.
//
// Uso: java com.craftinginterpreters.lox.Bench <archivo.lox> <calentamiento> <repeticiones>
// Imprime la salida del programa y, por cada repetición medida, una línea
// BENCH_MS. Las iteraciones de calentamiento se descartan: son las que
// permiten que el JIT de la JVM optimice el camino caliente, igual que el
// warmup de Python.

package com.craftinginterpreters.lox;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

public class Bench {
  private static List<Stmt> analyze(String source) {
    Scanner scanner = new Scanner(source);
    List<Token> tokens = scanner.scanTokens();
    Parser parser = new Parser(tokens);
    return parser.parse();
  }

  private static void runOnce(String source) {
    List<Stmt> statements = analyze(source);
    Interpreter interpreter = new Interpreter();
    Resolver resolver = new Resolver(interpreter);
    resolver.resolve(statements);
    interpreter.interpret(statements);
  }

  public static void main(String[] args) throws IOException {
    if (args.length < 3) {
      System.err.println("uso: Bench <archivo.lox> <calentamiento> <repeticiones>");
      System.exit(64);
    }

    String source = new String(
        Files.readAllBytes(Paths.get(args[0])), StandardCharsets.UTF_8);
    int warmup = Integer.parseInt(args[1]);
    int reps = Integer.parseInt(args[2]);

    // La salida del programa se captura para imprimirla una sola vez: si
    // no, cada iteración repetiría la salida y el benchmark no podría
    // usarla para verificar la equivalencia entre implementaciones.
    // Los tiempos van por stderr para no mezclarse con la salida.
    PrintStream original = System.out;
    ByteArrayOutputStream buffer = new ByteArrayOutputStream();
    System.setOut(new PrintStream(buffer));

    try {
      // Una primera ejecución dedicado a capturar la salida del programa.
      runOnce(source);
      String salida = buffer.toString(StandardCharsets.UTF_8);

      // El resto de las ejecuciones (calentamiento y medidas) no interesa
      // su salida, así que se descarta.
      buffer.reset();

      for (int i = 0; i < warmup; i++) {
        runOnce(source);
      }

      for (int i = 0; i < reps; i++) {
        long start = System.nanoTime();

        runOnce(source);

        long elapsed = System.nanoTime() - start;
        double ms = elapsed / 1_000_000.0;
        System.err.printf("BENCH_MS %.3f%n", ms);
      }

      original.print(salida);
    } finally {
      System.setOut(original);
    }
  }
}
