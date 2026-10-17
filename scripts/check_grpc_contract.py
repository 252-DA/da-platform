#!/usr/bin/env python3
"""Verify 1-to-1 gRPC method parity across proto, core-api, and web BFF.

Because CoreApiService uses JSON-over-gRPC (JsonRequest / JsonResponse),
@grpc/proto-loader only registers RPC methods present in
contracts/proto/core_api.proto at runtime. If an RPC is added to
web/src/lib/core-api.ts and core-api/src/grpc/grpc-server.service.ts without
updating core_api.proto (or vice versa), calls fail at runtime with TypeError
or UNIMPLEMENTED.

Run from the da-platform repo root:
    python3 scripts/check_grpc_contract.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_FILE = ROOT / "contracts/proto/core_api.proto"
SERVER_FILE = ROOT / "core-api/src/grpc/grpc-server.service.ts"
WEB_CLIENT_FILE = ROOT / "web/src/lib/core-api.ts"


def _proto_rpcs(text: str) -> set[str]:
    return set(re.findall(r"^\s*rpc\s+([A-Z]\w+)\s*\(", text, flags=re.MULTILINE))


def _server_handlers(text: str) -> set[str]:
    match = re.search(
        r"private\s+handlers\(\)\s*:\s*grpc\.UntypedServiceImplementation\s*\{\s*return\s*\{(.*?)\n\s{4}\};",
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Could not locate handlers() block in {SERVER_FILE}")
    body = match.group(1)
    return set(re.findall(r"^\s{6}([A-Z]\w+)\s*:\s*this\.unary\(", body, flags=re.MULTILINE))


def _web_core_methods(text: str) -> tuple[set[str], set[str]]:
    match = re.search(r"type\s+CoreMethod\s*=(.*?);", text, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not locate CoreMethod union in {WEB_CLIENT_FILE}")
    union_methods = set(re.findall(r'"([A-Z]\w+)"', match.group(1)))
    called_methods = set(re.findall(r'callCore<[^>]+>\(\s*"([A-Z]\w+)"', text))
    return union_methods, called_methods


def main() -> int:
    proto_rpcs = _proto_rpcs(PROTO_FILE.read_text(encoding="utf-8"))
    server_rpcs = _server_handlers(SERVER_FILE.read_text(encoding="utf-8"))
    web_union_rpcs, web_called_rpcs = _web_core_methods(
        WEB_CLIENT_FILE.read_text(encoding="utf-8")
    )

    issues: list[str] = []

    missing_in_proto = (server_rpcs | web_union_rpcs) - proto_rpcs
    if missing_in_proto:
        issues.append(
            f"RPCs missing in {PROTO_FILE.relative_to(ROOT)}: {sorted(missing_in_proto)}"
        )

    missing_in_server = (proto_rpcs | web_union_rpcs) - server_rpcs
    if missing_in_server:
        issues.append(
            f"RPCs missing in {SERVER_FILE.relative_to(ROOT)}: {sorted(missing_in_server)}"
        )

    missing_in_web_union = (proto_rpcs | server_rpcs) - web_union_rpcs
    if missing_in_web_union:
        issues.append(
            f"RPCs missing in CoreMethod union ({WEB_CLIENT_FILE.relative_to(ROOT)}): "
            f"{sorted(missing_in_web_union)}"
        )

    uncalled_in_web = web_union_rpcs - web_called_rpcs
    if uncalled_in_web:
        issues.append(
            f"CoreMethod entries never used in callCore() ({WEB_CLIENT_FILE.relative_to(ROOT)}): "
            f"{sorted(uncalled_in_web)}"
        )

    if issues:
        for issue in issues:
            print(f"grpc contract: {issue}", file=sys.stderr)
        return 1

    print(f"grpc contract: ok ({len(proto_rpcs)} RPCs synchronized across proto, core-api, and web)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

