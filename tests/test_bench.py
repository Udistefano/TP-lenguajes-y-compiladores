"""Tests del harness de benchmarks.

Verifican las piezas que no dependen de las implementaciones externas: la
normalización de salidas, las estadísticas, el formato de las tablas y la
selección de programas. La medición real se ejerce con
``uv run python benchmarks/bench.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from benchmarks import bench, medidores  # noqa: E402


class TestNormalizarSalida:
    """La normalización iguala diferencias de formato entre implementaciones."""

    def test_normaliza_floats_de_plox(self) -> None:
        assert bench.normalizar_salida("7.0\n") == ["7"]

    def test_normaliza_booleanos_de_plox(self) -> None:
        assert bench.normalizar_salida("None\nTrue\nFalse\n") == ["nil", "true", "false"]

    def test_normaliza_notacion_cientifica(self) -> None:
        # jlox y clox imprimen así los números grandes.
        assert bench.normalizar_salida("4.50135E8\n") == ["450135000"]
        assert bench.normalizar_salida("5.00005e+09\n") == ["5000050000"]

    def test_conserva_no_enteros(self) -> None:
        assert bench.normalizar_salida("7.5\n") == ["7.5"]

    def test_conserva_strings(self) -> None:
        assert bench.normalizar_salida("FizzBuzz\n") == ["FizzBuzz"]

    def test_ignora_lineas_vacias(self) -> None:
        assert bench.normalizar_salida("\n  \nOK\n") == ["OK"]

    def test_salidas_equivalentes_coinciden(self) -> None:
        mylox = bench.normalizar_salida("17710\n")
        plox = bench.normalizar_salida("17710.0\n")
        jlox = bench.normalizar_salida("1.771E4\n")
        assert mylox == plox == jlox


class TestPercentil:
    """El cálculo de percentiles sobre los tiempos medidos."""

    def test_mediana_de_una_lista_impar(self) -> None:
        medicion = bench.Medicion("p", "mylox", [3.0, 1.0, 2.0])
        assert medicion.percentil(0.50) == 2.0

    def test_percentil_95_de_lista_corta(self) -> None:
        medicion = bench.Medicion("p", "mylox", [1.0, 2.0])
        assert medicion.percentil(0.95) == 2.0

    def test_promedio_y_minimo(self) -> None:
        medicion = bench.Medicion("p", "mylox", [4.0, 2.0, 6.0])
        assert medicion.promedio == 4.0
        assert medicion.minimo == 2.0


class TestFormatos:
    """Los tres formatos de salida contienen las mismas mediciones."""

    def _resultado(self) -> bench.Resultado:
        resultado = bench.Resultado()
        resultado.agregar(bench.Medicion("suma.lox", "mylox", [0.5, 0.7]))
        resultado.agregar(bench.Medicion("suma.lox", "plox", [2.0, 2.4]))
        return resultado

    def test_tabla_tiene_una_fila_por_medicion(self) -> None:
        tabla = bench.formatear_tabla(self._resultado())
        assert "suma.lox" in tabla
        assert tabla.count("mylox") == 1
        assert tabla.count("plox") == 1

    def test_markdown_empieza_con_la_cabecera(self) -> None:
        markdown = bench.formatear_markdown(self._resultado())
        assert markdown.startswith("| programa | implementación |")
        assert "| suma.lox | mylox |" in markdown

    def test_csv_tiene_encabezado_y_filas(self) -> None:
        csv = bench.formatear_csv(self._resultado())
        lineas = csv.strip().splitlines()
        assert lineas[0] == "programa,implementacion,prom_ms,min_ms,p50_ms,p95_ms"
        assert len(lineas) == 3

    def test_csv_usa_milisegundos(self) -> None:
        csv = bench.formatear_csv(self._resultado())
        assert "500.000" in csv


class TestMedidorMylox:
    """El medidor de mylox mide in-process y captura la salida del programa."""

    def test_devuelve_tiempo_y_salida(self) -> None:
        medidor = medidores.MedidorMylox()
        segundos, salida = medidor.correr("print 1 + 2;\n")
        assert segundos > 0
        assert salida == "3\n"

    def test_correr_varias_devuelve_una_measure_por_repeticion(self) -> None:
        medidor = medidores.MedidorMylox()
        tiempos, salida = medidor.correr_varias("print 7;\n", 3)
        assert len(tiempos) == 3
        assert all(t > 0 for t in tiempos)
        assert salida == "7\n"

    def test_el_calentamiento_no_cuenta_como_medicion(self) -> None:
        # con 1 repetición sólo se mide una vez, aunque haya calentamiento.
        medidor = medidores.MedidorMylox()
        tiempos, _ = medidor.correr_varias("print 1;\n", 1)
        assert len(tiempos) == 1

    def test_captura_la_salida_del_programa(self) -> None:
        medidor = medidores.MedidorMylox()
        _, salida = medidor.correr('print "hola";\n')
        assert salida == "hola\n"


class TestVerificarEquivalencia:
    """El chequeo compara salidas normalizadas entre implementaciones."""

    def test_detecta_una_salida_distinta(self) -> None:
        class Falso(medidores.Medidor):
            def __init__(self, nombre: str, salida: str) -> None:
                self.nombre = nombre
                self.salida = salida

            def disponible(self) -> None:
                return

            def correr(self, fuente: str) -> tuple[float, str]:
                return 0.001, self.salida

        resultado = bench.Resultado()
        medidores_ = {"a": Falso("a", "1\n"), "b": Falso("b", "2\n")}
        assert bench.verificar_equivalencia("print 1;", medidores_, resultado) is False

    def test_acepta_salidas_equivalentes(self) -> None:
        class Falso(medidores.Medidor):
            def __init__(self, nombre: str, salida: str) -> None:
                self.nombre = nombre
                self.salida = salida

            def disponible(self) -> None:
                return

            def correr(self, fuente: str) -> tuple[float, str]:
                return 0.001, self.salida

        resultado = bench.Resultado()
        medidores_ = {"a": Falso("a", "7.0\n"), "b": Falso("b", "7\n")}
        assert bench.verificar_equivalencia("print 7;", medidores_, resultado) is True

    def test_con_una_sola_implementacion_no_hay_que_comparar(self) -> None:
        class Falso(medidores.Medidor):
            nombre = "a"

            def disponible(self) -> None:
                return

            def correr(self, fuente: str) -> tuple[float, str]:
                return 0.001, "1\n"

        resultado = bench.Resultado()
        assert bench.verificar_equivalencia("print 1;", {"a": Falso()}, resultado) is True


class TestSeleccionDeProgramas:
    """La selección de programas del directorio benchmarks/programas."""

    def test_trae_todos_por_defecto(self) -> None:
        programas = bench.seleccionar_programas(None)
        nombres = {archivo.name for archivo in programas}
        assert {"suma.lox", "fibonacci.lox", "closures.lox"} <= nombres

    def test_filtra_por_nombre(self) -> None:
        programas = bench.seleccionar_programas(["suma.lox"])
        assert [archivo.name for archivo in programas] == ["suma.lox"]

    def test_error_si_el_programa_no_existe(self) -> None:
        with pytest.raises(FileNotFoundError):
            bench.seleccionar_programas(["no-existe.lox"])


class TestProgramasPortables:
    """Los programas del benchmark deben ser portables entre implementaciones."""

    def _fuente(self, nombre: str) -> str:
        return (bench.PROGRAMAS / nombre).read_text(encoding="utf-8")

    def _codigo(self, nombre: str) -> str:
        """La fuente sin los comentarios, que pueden mencionar el operador."""
        fuente = self._fuente(nombre)
        return "\n".join(
            linea for linea in fuente.splitlines() if not linea.strip().startswith("//")
        )

    @pytest.mark.parametrize(
        "nombre",
        ["suma.lox", "fibonacci.lox", "closures.lox", "fizzbuzz.lox", "primos.lox"],
    )
    def test_no_usa_porcentaje(self, nombre: str) -> None:
        # jlox y clox no tienen el operador módulo.
        assert "%" not in self._codigo(nombre)

    @pytest.mark.parametrize(
        "nombre",
        ["suma.lox", "fibonacci.lox", "closures.lox", "fizzbuzz.lox", "primos.lox"],
    )
    def test_no_usa_clases(self, nombre: str) -> None:
        # plox no soporta clases.
        assert "class " not in self._codigo(nombre)

    @pytest.mark.parametrize(
        "nombre",
        ["suma.lox", "fibonacci.lox", "closures.lox", "fizzbuzz.lox", "primos.lox"],
    )
    def test_produce_una_salida_no_vacia(self, nombre: str) -> None:
        fuente = self._fuente(nombre)
        assert fuente.strip()
        assert "print" in fuente
