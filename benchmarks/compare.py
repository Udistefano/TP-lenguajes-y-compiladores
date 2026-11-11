from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.snapshots import checkout, load_package, source_hashes

PARTIAL = "088a86c2c86816dea2bbd3d3bb5fe549855ccf6d"
PLOX = "734f4d2adaf708c503dc5d17e88315e273c2f0ab"
EXPECTED = {
    "suma": "5000050000",
    "fibonacci": "17710",
    "closures": "450135000",
    "primos": "62",
    "fizzbuzz": "".join(
        "FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else "."
        for i in range(1, 401)
    ),
    "objetos": "200030000",
    "listas": "100010000",
}


class Mylox:
    def __init__(self, load, bytecode=False):
        self.lexer = load("pipeline.lexer").Lexer
        self.bytecode = bytecode
        if bytecode:
            self.compiler = load("bytecode.compiler").Compiler
            self.vm = load("bytecode.vm").VM
        else:
            self.parser = load("pipeline.parser").Parser
            self.resolver = load("resolver").BindingResolver
            self.interpreter = load("interpreter").Interpreter

    def run(self, source):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cpu_start = time.process_time_ns()
            start = time.perf_counter_ns()
            tokens = self.lexer(source).run()
            if self.bytecode:
                chunk = self.compiler(tokens).compile()
                runtime = self.vm(chunk)
                ready = time.perf_counter_ns()
                runtime.run()
            else:
                statements = self.parser(tokens).parse()
                runtime = self.interpreter()
                runtime.local_bindings.update(self.resolver().resolve_program(statements))
                ready = time.perf_counter_ns()
                for statement in statements:
                    statement.accept(runtime)
            end = time.perf_counter_ns()
            cpu_end = time.process_time_ns()
        return {
            "frontend_ms": (ready - start) / 1e6,
            "execution_ms": (end - ready) / 1e6,
            "total_ms": (end - start) / 1e6,
            "cpu_ms": (cpu_end - cpu_start) / 1e6,
        }, output.getvalue().strip()


class Plox:
    def __init__(self, load):
        self.scanner = load("Scanner").Scanner
        self.parser = load("Parser").Parser
        self.resolver = load("Resolver").Resolver
        self.interpreter = load("Interpreter").Interpreter

    def run(self, source):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            start = time.perf_counter_ns()
            statements = self.parser(self.scanner(source).scan()).parse()
            runtime = self.interpreter()
            resolver = self.resolver(runtime)
            for statement in statements:
                resolver.resolve(statement)
            ready = time.perf_counter_ns()
            runtime.interpret(statements)
            end = time.perf_counter_ns()
        text = output.getvalue().strip()
        if text.endswith(".0"):
            text = text[:-2]
        return {
            "frontend_ms": (ready - start) / 1e6,
            "execution_ms": (end - ready) / 1e6,
            "total_ms": (end - start) / 1e6,
        }, text


class NativePython:
    def run(self, source):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            start = time.perf_counter_ns()
            code = compile(source, "<benchmark>", "exec")
            ready = time.perf_counter_ns()
            exec(code, {})
            end = time.perf_counter_ns()
        text = output.getvalue().strip()
        if text.endswith(".0"):
            text = text[:-2]
        return {
            "frontend_ms": (ready - start) / 1e6,
            "execution_ms": (end - ready) / 1e6,
            "total_ms": (end - start) / 1e6,
        }, text


def machine():
    cpu = platform.processor()
    if Path("/proc/cpuinfo").exists():
        cpu = next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name"))
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
    }


def save(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--program", action="append", choices=EXPECTED)
    parser.add_argument("--only-vm", action="store_true")
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--baseline", type=Path, default=ROOT / "benchmarks/baselines/pre-optimization.json")
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.repetitions < 1 or args.warmup < 0:
        parser.error("Las repeticiones deben ser positivas y el calentamiento no negativo")
    if args.cpu is not None:
        os.sched_setaffinity(0, {args.cpu})

    baseline = args.baseline
    metadata = json.loads(baseline.read_text(encoding="utf-8"))
    result = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "machine": machine(), "repetitions": args.repetitions, "warmup": args.warmup,
        "seed": 1111, "gc": "enabled; collect before each Python sample, outside timer",
        "base_commit": metadata["base_commit"], "baseline_patch_sha256": metadata["patch_sha256"],
        "partial_commit": PARTIAL, "plox_commit": PLOX,
        "current_sources_sha256": source_hashes(ROOT / "src"),
        "programs": {}, "samples": [], "resources": [], "complete": False,
    }
    rng = random.Random(result["seed"])
    with contextlib.ExitStack() as resources:
        resources.callback(save, args.output, result)
        current_root = ROOT
        if args.snapshot:
            snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
            current_root = resources.enter_context(checkout(ROOT, snapshot["base_commit"], "src", args.snapshot, result["resources"]))
            result["current_sources_sha256"] = source_hashes(current_root / "src")
        current = load_package(current_root / "src/mylox", "bench_current")
        before_root = resources.enter_context(checkout(ROOT, metadata["base_commit"], "src", baseline, result["resources"]))
        before = load_package(before_root / "src/mylox", "bench_before")
        variants = {"bytecode-before": Mylox(before, True), "bytecode-after": Mylox(current, True)}
        if not args.only_vm:
            partial_root = resources.enter_context(checkout(ROOT, PARTIAL, "src", resources=result["resources"]))
            plox_root = resources.enter_context(checkout(ROOT.parent / "plox", PLOX, "plox", resources=result["resources"]))
            variants.update({
                "tree-walk": Mylox(current),
                "partial": Mylox(load_package(partial_root / "src/mylox", "bench_partial")),
                "plox": Plox(load_package(plox_root / "plox", "bench_plox")),
                "python-native": NativePython(),
            })
        for name in args.program or EXPECTED:
            directory = "programas" if name not in ("listas", "objetos") else "extensions"
            path = ROOT / "benchmarks" / directory / f"{name}.lox"
            source = path.read_text(encoding="utf-8")
            result["programs"][name] = {"sha256": hashlib.sha256(source.encode()).hexdigest(), "expected": EXPECTED[name]}
            active = [label for label in variants if name not in ("listas", "objetos") or label not in ("partial", "plox", "python-native")]
            sources = {label: source for label in active}
            if "python-native" in active:
                sources["python-native"] = (ROOT / "benchmarks/native" / f"{name}.py").read_text(encoding="utf-8")
                result["programs"][name]["python_sha256"] = hashlib.sha256(sources["python-native"].encode()).hexdigest()
            print(f"[programa] {name}: {', '.join(active)}", flush=True)
            for round_index in range(-args.warmup, args.repetitions):
                order = active.copy()
                rng.shuffle(order)
                for label in order:
                    gc.collect()
                    sample, output = variants[label].run(sources[label])
                    if output != EXPECTED[name]:
                        raise ValueError(f"Salida incorrecta en {name}/{label}: {output!r}")
                    if round_index >= 0:
                        result["samples"].append({"program": name, "variant": label, "round": round_index, **sample})
                if round_index >= 0:
                    save(args.output, result)
                if round_index >= 0 and (round_index + 1) % 5 == 0:
                    print(f"  {round_index + 1}/{args.repetitions}", flush=True)
            for label in active:
                values = [s["total_ms"] for s in result["samples"] if s["program"] == name and s["variant"] == label]
                print(f"  {label}: {statistics.median(values):.2f} ms", flush=True)
    result["complete"] = True
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    save(args.output, result)


if __name__ == "__main__":
    main()
