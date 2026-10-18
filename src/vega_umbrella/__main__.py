"""python -m vega_umbrella status | audit ROOT LICENSE_SHA256 | order     (read-only; prints JSON)"""
import json
import sys

from vega_umbrella import audit, registry


def main(argv):
    if not argv or argv[0] not in ("status", "audit", "order"):
        print("usage: status | audit ROOT LICENSE_SHA256 | order", file=sys.stderr)
        return 2
    if argv[0] == "status":
        registry.check_registry()
        print(json.dumps({n: {"layer": e["layer"], "owns": e["owns"], "status": e["status"]} for n, e in registry.FAMILY.items()}, indent=1))
        return 0
    if argv[0] == "order":
        print(json.dumps(registry.build_order()))
        return 0
    if len(argv) != 3:
        print("audit needs ROOT and LICENSE_SHA256", file=sys.stderr)
        return 2
    r = audit.audit_family(argv[1], argv[2])
    print(json.dumps(r, indent=1))
    return 0 if r["verdict"] == "READY" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
