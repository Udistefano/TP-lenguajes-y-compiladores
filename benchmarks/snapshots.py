from __future__ import annotations

import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import types


def source_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.py"))
    }


@contextlib.contextmanager
def checkout(repo: Path, revision: str, subdir: str, baseline: Path | None = None, resources=None):
    archive = subprocess.check_output(["git", "-C", str(repo), "archive", revision, subdir])
    temporary = tempfile.TemporaryDirectory(prefix="mylox-benchmark-")
    directory = temporary.name
    record = {"path": directory, "purpose": f"fuentes {revision} ({subdir})", "removed": False}
    if resources is not None:
        resources.append(record)
    try:
        destination = Path(directory)
        print(f"[temporal] {directory}: fuentes {revision[:8]} ({subdir})", flush=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(destination, filter="data")
        if baseline is not None:
            metadata = json.loads(baseline.read_text(encoding="utf-8"))
            patch = baseline.with_suffix(".patch").read_bytes()
            if hashlib.sha256(patch).hexdigest() != metadata["patch_sha256"]:
                raise ValueError("El parche de referencia fue modificado")
            subprocess.run(["git", "apply", "-"], input=patch, cwd=destination, check=True)
            for filename, expected in metadata["sources_sha256"].items():
                actual = hashlib.sha256((destination / filename).read_bytes()).hexdigest()
                if actual != expected:
                    raise ValueError(f"La referencia no coincide: {filename}")
        yield destination
    finally:
        temporary.cleanup()
        record["removed"] = not Path(directory).exists()
        print(f"[limpieza] {directory}: eliminado", flush=True)


def load_package(directory: Path, alias: str):
    import sys

    if (directory / "__init__.py").exists():
        spec = importlib.util.spec_from_file_location(
            alias, directory / "__init__.py", submodule_search_locations=[str(directory)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        spec.loader.exec_module(module)
    else:
        module = types.ModuleType(alias)
        module.__path__ = [str(directory)]
        sys.modules[alias] = module
    return lambda name: importlib.import_module(f"{alias}.{name}")
