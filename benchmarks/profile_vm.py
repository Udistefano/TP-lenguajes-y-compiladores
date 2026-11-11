from __future__ import annotations

import argparse
import contextlib
import cProfile
import io
import json
from pathlib import Path
import pstats
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.compare import EXPECTED
from benchmarks.snapshots import checkout, load_package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("program", choices=("suma", "fibonacci"))
    version = parser.add_mutually_exclusive_group()
    version.add_argument("--before", action="store_true")
    version.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = ROOT / "benchmarks/baselines/pre-optimization.json" if args.before else args.snapshot
    with contextlib.ExitStack() as resources:
        source_root = ROOT
        if baseline:
            metadata = json.loads(baseline.read_text(encoding="utf-8"))
            source_root = resources.enter_context(checkout(ROOT, metadata["base_commit"], "src", baseline))
        load = load_package(source_root / "src/mylox", "profiled_mylox")
        lexer, compiler, vm = load("pipeline.lexer").Lexer, load("bytecode.compiler").Compiler, load("bytecode.vm").VM
        source = (ROOT / "benchmarks/programas" / f"{args.program}.lox").read_text(encoding="utf-8")
        runtime = vm(compiler(lexer(source).run()).compile())
        profile = cProfile.Profile()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            profile.runcall(runtime.run)
        if output.getvalue().strip() != EXPECTED[args.program]:
            raise ValueError("El programa perfilado dio un resultado incorrecto")
        report = io.StringIO()
        pstats.Stats(profile, stream=report).strip_dirs().sort_stats("tottime").print_stats(30)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.getvalue(), encoding="utf-8")


if __name__ == "__main__":
    main()
