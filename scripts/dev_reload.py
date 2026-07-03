from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


WATCH_SUFFIXES = {".py", ".json", ".toml", ".yaml", ".yml"}
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


def iter_files(paths: list[Path]):
    for root in paths:
        if root.is_file():
            yield root
            continue

        if not root.exists():
            continue

        for path in root.rglob("*"):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix in WATCH_SUFFIXES:
                yield path


def snapshot(paths: list[Path]) -> dict[str, tuple[int, int]]:
    files: dict[str, tuple[int, int]] = {}
    for path in iter_files(paths):
        try:
            stat = path.stat()
        except OSError:
            continue
        files[str(path)] = (stat.st_mtime_ns, stat.st_size)
    return files


def start_module(module: str) -> subprocess.Popen[bytes]:
    print(f"dev_reload: starting python -m {module}", flush=True)
    return subprocess.Popen([sys.executable, "-m", module])


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def wait_for_change(paths: list[Path], previous: dict[str, tuple[int, int]], interval: float):
    while True:
        time.sleep(interval)
        current = snapshot(paths)
        if current != previous:
            return current


def main() -> int:
    parser = argparse.ArgumentParser(description="Restart a Python module when source files change.")
    parser.add_argument("module")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    paths = [Path(path) for path in args.paths]
    state = snapshot(paths)
    child = start_module(args.module)

    def handle_stop(signum, _frame):
        stop_process(child)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    while True:
        time.sleep(args.interval)

        exited = child.poll()
        current = snapshot(paths)

        if exited is not None:
            print(
                f"dev_reload: child exited with code {exited}; waiting for a file change",
                flush=True,
            )
            state = wait_for_change(paths, current, args.interval)
            child = start_module(args.module)
            continue

        if current != state:
            print("dev_reload: change detected; restarting", flush=True)
            stop_process(child)
            state = current
            child = start_module(args.module)


if __name__ == "__main__":
    raise SystemExit(main())
