"""Benchmark de mylox contra otras implementaciones de Lox.

Mide el tiempo de scan+parse+resolve+interpret de varios programas en
distintas implementaciones, verifica que todas produzcan el mismo resultado
y reporta estadísticas. Ver ``docs/benchmarks.md`` para metodología,
resultados y conclusiones.

Uso:
    uv run python benchmarks/bench.py
    uv run python benchmarks/bench.py --implementaciones mylox,plox
    uv run python benchmarks/bench.py --programa fibonacci.lox --salida markdown
    uv run python benchmarks/bench.py benchmarks/programas/suma.lox
"""

from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# El script se puede ejecutar directo (``python benchmarks/bench.py``), en cuyo
# caso la raíz del repo no está en el path y el paquete ``benchmarks`` no
# resuelve. Se agrega para que funcione sin instalar nada.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from benchmarks.medidores import (  # noqa: E402
    ImplementacionNoDisponible,
    Medidor,
    construir_medidores,
)

PROGRAMAS = RAIZ / "benchmarks" / "programas"
IMPLEMENTACIONES = ["mylox", "plox", "jlox", "clox"]
EXIT_OK = 0
EXIT_ERROR = 65


@dataclass
class Medicion:
    """Tiempos de un programa en una implementación, ya sin calentamiento."""

    programa: str
    implementacion: str
    tiempos: list[float] = field(default_factory=list)

    @property
    def promedio(self) -> float:
        return statistics.mean(self.tiempos)

    @property
    def minimo(self) -> float:
        return min(self.tiempos)

    def percentil(self, p: float) -> float:
        """Percentil ``p`` (0..1) por rango cercano sobre los tiempos ordenados."""
        ordenados = sorted(self.tiempos)
        indice = min(len(ordenados) - 1, int(p * len(ordenados) + 0.999999) - 1)
        return ordenados[max(0, indice)]


@dataclass
class Resultado:
    """Agrupa las mediciones de todos los programas e implementaciones."""

    mediciones: list[Medicion] = field(default_factory=list)
    saltadas: list[tuple[str, str]] = field(default_factory=list)

    def agregar(self, medicion: Medicion) -> None:
        self.mediciones.append(medicion)

    def por_programa(self, programa: str, implementacion: str) -> Medicion | None:
        for medicion in self.mediciones:
            if medicion.programa == programa and medicion.implementacion == implementacion:
                return medicion
        return None

    @property
    def programas(self) -> list[str]:
        vistos: list[str] = []
        for medicion in self.mediciones:
            if medicion.programa not in vistos:
                vistos.append(medicion.programa)
        return vistos

    def implementaciones_usadas(self) -> list[str]:
        vistas: list[str] = []
        for medicion in self.mediciones:
            if medicion.implementacion not in vistas:
                vistas.append(medicion.implementacion)
        return vistas


def normalizar_salida(texto: str) -> list[str]:
    """Lleva la salida de distintas implementaciones a una forma comparable.

    Las implementaciones imprimen números citando el estilo de su lenguaje:
    plox usa ``7.0``/``None``/``True`` y jlox o clox usan notación científica
    para valores grandes. Comparamos por valor, no por texto.
    """
    lineas: list[str] = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        reemplazos = {"None": "nil", "True": "true", "False": "false"}
        if linea in reemplazos:
            linea = reemplazos[linea]
        try:
            numero = float(linea)
        except ValueError:
            lineas.append(linea)
        else:
            lineas.append(str(int(numero)) if numero.is_integer() else repr(numero))
    return lineas


def verificar_equivalencia(
    fuente: str, medidores: dict[str, Medidor], resultado: Resultado
) -> bool:
    """Comprueba que todas las implementaciones produzcan el mismo resultado.

    Corre cada implementación una vez y compara la salida normalizada. Una
    diferencia indica que el programa no es portable o que hay un bug: en ese
    caso no tiene sentido medir tiempos.
    """
    salidas: dict[str, list[str]] = {}
    for nombre, medidor in medidores.items():
        try:
            _, salida = medidor.correr(fuente)
        except ImplementacionNoDisponible as error:
            resultado.saltadas.append((nombre, str(error)))
            continue
        salidas[nombre] = normalizar_salida(salida)

    if len(salidas) <= 1:
        return True

    referencia, esperada = next(iter(salidas.items()))
    todas_iguales = True
    for nombre, salida in salidas.items():
        if salida != esperada:
            todas_iguales = False
            print(
                f"[error] salida distinta entre {referencia} y {nombre}\n"
                f"        {referencia}: {esperada}\n"
                f"        {nombre}: {salida}",
                file=sys.stderr,
            )
    return todas_iguales


def medir(
    programa: str,
    fuente: str,
    medidor: Medidor,
    repeticiones: int,
    resultado: Resultado,
) -> None:
    """Mide un programa en una implementación y guarda la medición.

    El calentamiento lo hace el propio medidor: para mylox y plox son
    ejecuciones en el mismo proceso de Python, y para jlox y clox las hace
    el harness dentro de su proceso, de modo que el JIT o la VM queden en el
    mismo estado que durante las ejecuciones medidas.
    """

    medicion = Medicion(programa=programa, implementacion=medidor.nombre)
    tiempos, _ = medidor.correr_varias(fuente, repeticiones)
    medicion.tiempos.extend(tiempos)
    resultado.agregar(medicion)


def formatear_tabla(resultado: Resultado) -> str:
    """Tabla de texto alineada, agrupada por programa."""

    lineas = []
    encabezado = f"{'programa':<16} {'impl':<7} {'prom':>10} {'min':>10} {'p50':>10} {'p95':>10}"
    lineas.append(encabezado)
    lineas.append("-" * len(encabezado))
    for programa in resultado.programas:
        for implementacion in resultado.implementaciones_usadas():
            medicion = resultado.por_programa(programa, implementacion)
            if medicion is None:
                continue
            lineas.append(
                f"{programa:<16} {implementacion:<7} "
                f"{medicion.promedio * 1000:>10.2f} {medicion.minimo * 1000:>10.2f} "
                f"{medicion.percentil(0.50) * 1000:>10.2f} {medicion.percentil(0.95) * 1000:>10.2f}"
            )
        lineas.append("")
    return "\n".join(lineas).rstrip() + "\n"


def formatear_markdown(resultado: Resultado) -> str:
    """Tabla en formato Markdown, lista para pegar en la documentación."""

    encabezado = "| programa | implementación | prom (ms) | min (ms) | p50 (ms) | p95 (ms) |"
    separador = "| --- | --- | ---: | ---: | ---: | ---: |"
    lineas = [encabezado, separador]
    for programa in resultado.programas:
        for implementacion in resultado.implementaciones_usadas():
            medicion = resultado.por_programa(programa, implementacion)
            if medicion is None:
                continue
            lineas.append(
                f"| {programa} | {implementacion} | "
                f"{medicion.promedio * 1000:.2f} | {medicion.minimo * 1000:.2f} | "
                f"{medicion.percentil(0.50) * 1000:.2f} | {medicion.percentil(0.95) * 1000:.2f} |"
            )
    return "\n".join(lineas) + "\n"


def formatear_csv(resultado: Resultado) -> str:
    """Tabla en CSV con las mismas columnas que las otras salidas."""

    lineas = ["programa,implementacion,prom_ms,min_ms,p50_ms,p95_ms"]
    for programa in resultado.programas:
        for implementacion in resultado.implementaciones_usadas():
            medicion = resultado.por_programa(programa, implementacion)
            if medicion is None:
                continue
            lineas.append(
                f"{programa},{implementacion},{medicion.promedio * 1000:.3f},"
                f"{medicion.minimo * 1000:.3f},{medicion.percentil(0.50) * 1000:.3f},"
                f"{medicion.percentil(0.95) * 1000:.3f}"
            )
    return "\n".join(lineas) + "\n"


FORMATOS = {
    "tabla": formatear_tabla,
    "markdown": formatear_markdown,
    "csv": formatear_csv,
}


def seleccionar_programas(nombres: list[str] | None) -> list[Path]:
    """Devuelve los archivos .lox a medir, todos o los pedidos.

    Acepta tanto un nombre suelto (``suma.lox``) como una ruta relativa al
    directorio de programas (``benchmarks/programas/suma.lox``), que es lo
    que se escribe al invocar el script con un archivo.
    """

    todos = sorted(PROGRAMAS.glob("*.lox"))
    if not nombres:
        return todos

    pedidos = []
    for nombre in nombres:
        archivo = Path(nombre)
        if not archivo.exists():
            archivo = PROGRAMAS / nombre
        if not archivo.exists():
            raise FileNotFoundError(f"no existe el programa {nombre}")
        pedidos.append(archivo)
    return pedidos


def main(argv: list[str] | None = None) -> int:
    """Corre el benchmark completo y reporta los resultados."""

    parser = argparse.ArgumentParser(
        prog="bench",
        description="Benchmark de mylox contra otras implementaciones de Lox",
    )
    parser.add_argument(
        "archivo",
        nargs="?",
        type=Path,
        help="un solo programa a medir (alternativa a --programa)",
    )
    parser.add_argument(
        "-n",
        "--repeticiones",
        type=int,
        default=20,
        help="ejecuciones medidas por programa e implementación (por defecto: 20)",
    )
    parser.add_argument(
        "--implementaciones",
        default=",".join(IMPLEMENTACIONES),
        help="lista separada por comas (por defecto: todas las disponibles)",
    )
    parser.add_argument(
        "--programa",
        action="append",
        help="nombre de un programa a medir; se puede repetir",
    )
    parser.add_argument(
        "--ref-plox",
        default="origin/main",
        help="referencia de git de la que extraer plox (por defecto: origin/main)",
    )
    parser.add_argument(
        "--salida",
        choices=sorted(FORMATOS),
        default="tabla",
        help="formato de los resultados (por defecto: tabla)",
    )
    parser.add_argument(
        "--sin-chequeo",
        action="store_true",
        help="no verificar que las implementaciones den la misma salida",
    )

    args = parser.parse_args(argv)

    pedidos = list(args.programa or [])
    if args.archivo is not None:
        pedidos.append(str(args.archivo))

    try:
        programas = seleccionar_programas(pedidos)
    except FileNotFoundError as error:
        print(f"[error] {error}", file=sys.stderr)
        return EXIT_ERROR

    if not programas:
        print(f"[error] no hay programas .lox en {PROGRAMAS}", file=sys.stderr)
        return EXIT_ERROR

    seleccion = [nombre.strip() for nombre in args.implementaciones.split(",") if nombre.strip()]
    try:
        medidores = construir_medidores(seleccion, args.ref_plox)
    except ValueError as error:
        print(f"[error] {error}", file=sys.stderr)
        return EXIT_ERROR

    resultado = Resultado()
    activos: dict[str, Medidor] = {}

    print(f"# benchmark: {len(programas)} programa(s), {len(seleccion)} implementación(es)\n")
    for nombre, medidor in medidores.items():
        try:
            medidor.disponible()
        except ImplementacionNoDisponible as error:
            resultado.saltadas.append((nombre, str(error)))
            print(f"[saltada] {nombre}: {error}")
        else:
            activos[nombre] = medidor

    if "mylox" not in activos:
        print("[error] mylox debe estar disponible", file=sys.stderr)
        return EXIT_ERROR

    for archivo in programas:
        fuente = archivo.read_text(encoding="utf-8")
        print(f"[programa] {archivo.name}")

        if not args.sin_chequeo:
            if not verificar_equivalencia(fuente, activos, resultado):
                print(f"[error] se omite {archivo.name} por salidas divergentes", file=sys.stderr)
                continue

        for nombre, medidor in activos.items():
            try:
                medir(archivo.name, fuente, medidor, args.repeticiones, resultado)
            except ImplementacionNoDisponible as error:
                resultado.saltadas.append((nombre, str(error)))
                print(f"[saltada] {nombre} en {archivo.name}: {error}")

    print()
    print(FORMATOS[args.salida](resultado), end="")

    if resultado.saltadas:
        print("\nno medidas:", file=sys.stderr)
        for nombre, motivo in resultado.saltadas:
            print(f"  - {nombre}: {motivo}", file=sys.stderr)

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
