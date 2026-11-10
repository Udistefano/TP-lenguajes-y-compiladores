"""Adaptadores que miden una misma fuente Lox en distintas implementaciones.

Cada medidor sabe:

* si su implementación está disponible en esta máquina y, si no, por qué;
* cómo ejecutar un programa midiendo sólo scan+parse+resolve+interpret,
  sin incluir el arranque del proceso ni de la máquina virtual.

La medición se hace en proceso (import directo o harness nativo) y con stdout
redirigido, para no medir el costo de la entrada/salida. Los medidores de
jlox y clox usan los harness de ``benchmarks/harness`` compilados por
``benchmarks/setup.sh``.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from mylox.interpreter import Interpreter
from mylox.pipeline.lexer import Lexer
from mylox.pipeline.parser import Parser

RAIZ = Path(__file__).resolve().parents[1]
CACHE = RAIZ / "benchmarks" / ".cache"
REPO_HERMANO = RAIZ.parent

# Iteraciones que se descartan antes de medir, para que el estado de la
# máquina (caché de Python, JIT de la JVM, tablas de la VM) quede estable.
CALENTAMIENTO = 3

LINEA_TIEMPO = re.compile(r"^BENCH_MS\s+([0-9.]+)\s*$")


class ImplementacionNoDisponible(Exception):
    """La implementación no puede usarse en esta máquina, con el motivo."""


class Medidor:
    """Interfaz común: ejecuta una fuente y devuelve su salida de texto.

    ``correr`` mide una ejecución y descarta lo que el programa imprime,
    devolviendo el tiempo en segundos y la salida capturada por separado.

    ``correr_varias`` es la operación de medición: devuelve los tiempos de
    varias ejecuciones seguidas. La implementación base las ejecuta de a una;
    los medidores externos delegan en su harness, que hace el calentamiento
    dentro del mismo proceso para que el estado de la máquina virtual o de
    la JVM sea el mismo que en una corrida larga.
    """

    nombre: str

    def disponible(self) -> None:
        """Verifica que la implementación pueda usarse; lanza si no."""
        raise NotImplementedError

    def correr(self, fuente: str) -> tuple[float, str]:
        """Ejecuta ``fuente`` una vez y devuelve (segundos, stdout)."""
        raise NotImplementedError

    def correr_varias(self, fuente: str, repeticiones: int) -> tuple[list[float], str]:
        """Ejecuta ``fuente`` varias veces y devuelve (tiempos, stdout).

        La implementación base descarta unas cuantas iteraciones de
        calentamiento antes de medir.
        """
        for _ in range(CALENTAMIENTO):
            self.correr(fuente)

        tiempos: list[float] = []
        salida = ""
        for _ in range(repeticiones):
            segundos, salida = self.correr(fuente)
            tiempos.append(segundos)
        return tiempos, salida


class MedidorMylox(Medidor):
    """Nuestra implementación, importada directamente en este proceso."""

    nombre = "mylox"

    def disponible(self) -> None:
        return

    def correr(self, fuente: str) -> tuple[float, str]:
        buffer = io.StringIO()
        inicio = time.perf_counter()
        with contextlib.redirect_stdout(buffer):
            arbol = Parser(Lexer(fuente).run()).parse()
            Interpreter().interpret(arbol)
        return time.perf_counter() - inicio, buffer.getvalue()


class MedidorPlox(Medidor):
    """Implementación de la cátedra (branch main), leída del árbol de git.

    No tocamos el checkout del usuario: extraemos el package ``plox`` de la
    rama pedida a un directorio temporal y lo importamos desde ahí. El repo
    hermano se busca igual que en ``tests/strict_real_tests.py``.
    """

    nombre = "plox"

    def __init__(self, repo: Path, ref: str, destino: Path) -> None:
        self.repo = repo
        self.ref = ref
        self.destino = destino
        self._modulos: dict[str, object] | None = None

    def disponible(self) -> None:
        if not (self.repo / ".git").exists():
            raise ImplementacionNoDisponible(f"no se encontró el repo git en {self.repo}")
        resultado = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "--verify", f"{self.ref}^{{commit}}"],
            capture_output=True,
            text=True,
        )
        if resultado.returncode != 0:
            raise ImplementacionNoDisponible(f"la referencia {self.ref} no existe en {self.repo}")

        self.destino.mkdir(parents=True, exist_ok=True)
        archivo = subprocess.run(
            ["git", "-C", str(self.repo), "archive", self.ref, "plox"],
            capture_output=True,
        )
        if archivo.returncode != 0:
            raise ImplementacionNoDisponible(f"git archive {self.ref} falló en {self.repo}")

        import tarfile

        # Se limpia el destino para no dejar archivos de una versión anterior.
        for viejo in self.destino.glob("plox"):
            shutil.rmtree(viejo, ignore_errors=True)

        with tarfile.open(fileobj=io.BytesIO(archivo.stdout)) as tar:
            tar.extractall(self.destino)

        sys.path.insert(0, str(self.destino))
        try:
            self._modulos = {
                modulo: importlib.import_module(f"plox.{modulo}")
                for modulo in ("Scanner", "Parser", "Resolver", "Interpreter")
            }
        except ImportError as error:
            raise ImplementacionNoDisponible(f"no se pudo importar plox: {error}") from error
        finally:
            sys.path.remove(str(self.destino))

    def correr(self, fuente: str) -> tuple[float, str]:
        assert self._modulos is not None
        buffer = io.StringIO()
        inicio = time.perf_counter()
        with contextlib.redirect_stdout(buffer):
            tokens = self._modulos["Scanner"].Scanner(fuente).scan()
            sentencias = self._modulos["Parser"].Parser(tokens).parse()
            interprete = self._modulos["Interpreter"].Interpreter()
            resolutor = self._modulos["Resolver"].Resolver(interprete)
            for sentencia in sentencias:
                resolutor.resolve(sentencia)
            interprete.interpret(sentencias)
        return time.perf_counter() - inicio, buffer.getvalue()


class MedidorExterno(Medidor):
    """Base para jlox y clox: corren un harness que imprime ``BENCH_MS``.

    El harness mide sólo scan+parse+resolve+interpret dentro de su propio
    proceso y hace el calentamiento ahí adentro, de modo que el JIT de la JVM
    o el estado de la VM queden estables como en una corrida larga. El
    medidor lanza el proceso una vez y lee los tiempos que el harness reporta.
    """

    def __init__(self, comando: list[str], etiqueta: str) -> None:
        self.comando = comando
        self.etiqueta = etiqueta

    def disponible(self) -> None:
        if not self._hay_harness():
            raise ImplementacionNoDisponible(
                f"{self.etiqueta}: falta compilar (correr benchmarks/setup.sh)"
            )

    def _hay_harness(self) -> bool:
        raise NotImplementedError

    def correr(self, fuente: str) -> tuple[float, str]:
        tiempos, salida = self.correr_varias(fuente, 1)
        return tiempos[0], salida

    def correr_varias(self, fuente: str, repeticiones: int) -> tuple[list[float], str]:
        archivo = self._escribir_temporal(fuente)
        try:
            return self._medir_archivo(archivo, repeticiones)
        finally:
            archivo.unlink(missing_ok=True)

    def _escribir_temporal(self, fuente: str) -> Path:
        raise NotImplementedError

    def _medir_archivo(self, archivo: Path, repeticiones: int) -> tuple[list[float], str]:
        resultado = subprocess.run(
            [*self.comando, str(archivo), str(CALENTAMIENTO), str(repeticiones)],
            capture_output=True,
            text=True,
        )
        if resultado.returncode != 0:
            raise ImplementacionNoDisponible(
                f"{self.etiqueta} terminó con exit={resultado.returncode}: {resultado.stderr.strip()}"
            )

        # Los tiempos van por stderr y la salida del programa por stdout.
        tiempos = [
            float(coincidencia.group(1)) / 1000.0
            for coincidencia in (
                LINEA_TIEMPO.match(linea) for linea in resultado.stderr.splitlines()
            )
            if coincidencia
        ]

        if not tiempos:
            raise ImplementacionNoDisponible(f"{self.etiqueta} no reportó BENCH_MS")

        return tiempos, resultado.stdout


class MedidorJlox(MedidorExterno):
    """jlox del libro (Java, tree-walk) mediante el harness Bench.java."""

    nombre = "jlox"

    def __init__(self) -> None:
        super().__init__(
            ["java", "-cp", str(CACHE / "jlox-build"), "com.craftinginterpreters.lox.Bench"],
            "jlox",
        )

    def _hay_harness(self) -> bool:
        return (CACHE / "jlox-build" / "com" / "craftinginterpreters" / "lox" / "Bench.class").exists()

    def _escribir_temporal(self, fuente: str) -> Path:
        archivo = CACHE / "jlox-temporal.lox"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(fuente, encoding="utf-8")
        return archivo


class MedidorClox(MedidorExterno):
    """clox del libro (C, máquina virtual de bytecode) mediante cloxbench.c."""

    nombre = "clox"

    def __init__(self) -> None:
        super().__init__([str(CACHE / "cloxbench")], "clox")

    def _hay_harness(self) -> bool:
        return (CACHE / "cloxbench").exists()

    def _escribir_temporal(self, fuente: str) -> Path:
        archivo = CACHE / "clox-temporal.lox"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(fuente, encoding="utf-8")
        return archivo


def construir_medidores(seleccion: list[str], ref_plox: str) -> dict[str, Medidor]:
    """Crea los medidores pedidos, en el orden de ``seleccion``."""

    disponibles: dict[str, Medidor] = {
        "mylox": MedidorMylox(),
        "plox": MedidorPlox(REPO_HERMANO / "plox", ref_plox, CACHE / "plox-src"),
        "jlox": MedidorJlox(),
        "clox": MedidorClox(),
    }

    faltantes = [nombre for nombre in seleccion if nombre not in disponibles]
    if faltantes:
        raise ValueError(f"implementaciones desconocidas: {', '.join(faltantes)}")

    return {nombre: disponibles[nombre] for nombre in seleccion}
