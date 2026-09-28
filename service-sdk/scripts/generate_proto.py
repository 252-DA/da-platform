#!/usr/bin/env python3
"""Regenerate gRPC Python stubs from proto/da_platform/embedding/v1/embedding.proto.

Usage: uv run python scripts/generate_proto.py
CI runs this then `git diff --exit-code` to catch stale generated code.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_ROOT = ROOT / "proto"
PROTO_FILE = PROTO_ROOT / "da_platform" / "embedding" / "v1" / "embedding.proto"
OUT_DIR = ROOT / "src" / "da_service_sdk" / "generated"


def main() -> int:
    if not PROTO_FILE.exists():
        print(f"proto file not found: {PROTO_FILE}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROTO_ROOT}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        f"--pyi_out={OUT_DIR}",
        str(PROTO_FILE),
    ]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    _fix_relative_imports()
    _ensure_package_inits()
    return 0


def _fix_relative_imports() -> None:
    """protoc emits an absolute `from da_platform.embedding.v1 import
    embedding_pb2` import inside the generated grpc file; rewrite it to a
    package-relative import so the generated tree stays importable regardless
    of where it ends up vendored (editable install vs built wheel)."""
    grpc_file = OUT_DIR / "da_platform" / "embedding" / "v1" / "embedding_pb2_grpc.py"
    if not grpc_file.exists():
        return
    text = grpc_file.read_text()
    text = text.replace(
        "from da_platform.embedding.v1 import embedding_pb2",
        "from . import embedding_pb2",
    )
    grpc_file.write_text(text)


def _ensure_package_inits() -> None:
    for pkg_dir in (
        OUT_DIR,
        OUT_DIR / "da_platform",
        OUT_DIR / "da_platform" / "embedding",
        OUT_DIR / "da_platform" / "embedding" / "v1",
    ):
        init_file = pkg_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")


if __name__ == "__main__":
    raise SystemExit(main())
