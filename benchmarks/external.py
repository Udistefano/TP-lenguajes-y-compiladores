from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.compare import EXPECTED, machine, save

CLOX_COMMIT = "4a840f70f69c6ddd17cfef4f6964f8e1bcd8c3d4"


def same_output(actual, expected):
    try:
        return Decimal(actual.strip()) == Decimal(expected)
    except InvalidOperation:
        return actual.strip() == expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--clox-source", type=Path)
    args = parser.parse_args()
    result = json.loads(args.results.read_text(encoding="utf-8"))
    if not result["complete"]:
        parser.error("Primero debe terminar la comparación de Python")
    affinity = result["machine"]["affinity"]
    if affinity is not None:
        os.sched_setaffinity(0, affinity)
    if machine() != result["machine"]:
        parser.error("Las implementaciones externas deben medirse en el mismo entorno")
    if any(s["variant"] in ("clox", "javascript-native") for s in result["samples"]):
        parser.error("Este archivo ya tiene mediciones externas")
    count = result["repetitions"]
    warmup = result["warmup"]
    temporary = tempfile.TemporaryDirectory(prefix="mylox-clox-benchmark-")
    directory = temporary.name
    if "external_resources" in result:
        result["resources"].append(result["external_resources"])
    result["external_resources"] = {"path": directory, "purpose": "fuentes clox y ejecutable de comparación", "removed": False}
    try:
        temp = Path(directory)
        if shutil.disk_usage(temp).free < 20 * 1024**3:
            raise RuntimeError("Se requieren al menos 20 GiB libres para compilar")
        save(args.results, result)
        print(f"[temporal] {directory}: clox {CLOX_COMMIT}", flush=True)
        repo = args.clox_source.resolve() if args.clox_source else temp / "craftinginterpreters"
        if args.clox_source is None:
            subprocess.run(["git", "clone", "--quiet", "--no-checkout", "--depth", "1", "--filter=blob:none", "--sparse", "https://github.com/munificent/craftinginterpreters.git", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "c"], check=True)
            head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            if head != CLOX_COMMIT:
                subprocess.run(["git", "-C", str(repo), "fetch", "--quiet", "--depth", "1", "origin", CLOX_COMMIT], check=True)
            subprocess.run(["git", "-C", str(repo), "checkout", "--quiet", "--detach", CLOX_COMMIT], check=True)
        revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        if revision != CLOX_COMMIT:
            raise ValueError(f"Se esperaba clox {CLOX_COMMIT}, se encontró {revision}")
        binary = temp / "cloxbench"
        flags = ["-std=c99", "-O2", "-DNDEBUG"]
        source_files = sorted(path for path in (repo / "c").glob("*.c") if path.name != "main.c")
        subprocess.run(["gcc", *flags, "-I", str(repo / "c"), "-o", str(binary), str(ROOT / "benchmarks/harness/clox/cloxbench.c"), *map(str, source_files), "-lm"], check=True)
        result["clox"] = {
            "commit": revision, "flags": flags,
            "compiler": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
            "harness_sha256": hashlib.sha256((ROOT / "benchmarks/harness/clox/cloxbench.c").read_bytes()).hexdigest(),
        }
        for name in result["programs"]:
            if name != "listas":
                folder = "extensions" if name == "objetos" else "programas"
                completed = subprocess.run([str(binary), str(ROOT / "benchmarks" / folder / f"{name}.lox"), str(warmup), str(count)], capture_output=True, text=True, timeout=120)
                if completed.returncode:
                    raise RuntimeError(f"clox falló en {name} (exit={completed.returncode}): {completed.stderr}")
                if not same_output(completed.stdout, EXPECTED[name]):
                    raise ValueError(f"Salida incorrecta de clox: {name}")
                times = [float(line.split()[1]) for line in completed.stderr.splitlines() if line.startswith("BENCH_MS ")]
                if len(times) != count:
                    raise ValueError("clox no devolvió todas las muestras")
                result["samples"].extend({"program": name, "variant": "clox", "round": i, "total_ms": value} for i, value in enumerate(times))
            if name not in ("listas", "objetos"):
                source = ROOT / "benchmarks/native" / f"{name}.js"
                completed = subprocess.run(["node", "--expose-gc", str(ROOT / "benchmarks/harness/native.js"), str(source), str(warmup), str(count)], capture_output=True, text=True, check=True, timeout=120)
                measured = json.loads(completed.stdout)
                if measured["output"] != EXPECTED[name] or len(measured["samples"]) != count:
                    raise ValueError(f"Salida incorrecta de JavaScript: {name}")
                result["javascript"] = {"node": measured["node"], "v8": measured["v8"]}
                result["programs"][name]["javascript_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
                result["samples"].extend({"program": name, "variant": "javascript-native", "round": i, **sample} for i, sample in enumerate(measured["samples"]))
            save(args.results, result)
            print(f"[externos] {name}: OK", flush=True)
    finally:
        temporary.cleanup()
        result["external_resources"]["removed"] = not Path(directory).exists()
        save(args.results, result)
        print(f"[limpieza] {directory}: eliminado", flush=True)
    result["external_complete"] = True
    save(args.results, result)


if __name__ == "__main__":
    main()
