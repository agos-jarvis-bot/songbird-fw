#!/usr/bin/env python3
"""
Prototype of `songbird validate <dir>` (RA R-052, R-020.2, R-020.3).

Two layers:
  1. Structural: every YAML document must validate against songbird.schema.json.
  2. Semantic: cross-object rules that JSON Schema cannot express.

Exit code 0 = valid, 1 = errors, 2 = usage.
Every error is reported as  <file>:<doc#> <kind>/<name> <rule>: <message>
"""
import sys, pathlib, ipaddress, collections
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
import json

SCHEMA_DIR = pathlib.Path(__file__).parent / "schema"

ADDRESS_NS = {"Address", "AddressGroup", "VirtualIP"}
SERVICE_NS = {"Service", "ServiceGroup"}
NETWORK_NS = {"Interface", "Zone"}
NAMESPACE_OF = ({k: "address" for k in ADDRESS_NS} | {k: "service" for k in SERVICE_NS}
                | {k: "network" for k in NETWORK_NS} | {"PolicySet": "policy", "Color": "color"})

# Shipped palette: name -> hex. A Color with predefined: true must keep this hex (users annotate, not repaint).
PREDEFINED_PALETTE = {
    "green": "#2E7D32", "blue": "#1565C0", "red": "#C62828", "orange": "#EF6C00",
    "purple": "#6A1B9A", "teal": "#00838F", "grey": "#616161",
}


def load_schema():
    reg = Registry()
    for p in SCHEMA_DIR.glob("*.schema.json"):
        s = json.loads(p.read_text())
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    root = json.loads((SCHEMA_DIR / "songbird.schema.json").read_text())
    return Draft202012Validator(root, registry=reg, format_checker=FormatChecker())


class Obj:
    def __init__(self, file, idx, doc):
        self.file, self.idx, self.doc = file, idx, doc
        self.kind = doc.get("kind", "?")
        self.name = (doc.get("metadata") or {}).get("name", "?")
        self.spec = doc.get("spec") or {}

    def where(self):
        return f"{self.file}:{self.idx} {self.kind}/{self.name}"


def structural(validator, objs, errors):
    ok = []
    for o in objs:
        errs = sorted(validator.iter_errors(o.doc), key=lambda e: list(e.absolute_path))
        if errs:
            # report the deepest / most specific error per document
            e = max(errs, key=lambda e: len(e.absolute_path))
            path = "/".join(str(p) for p in e.absolute_path) or "<root>"
            errors.append(f"{o.where()} schema: at /{path}: {e.message}")
        else:
            ok.append(o)
    return ok


def _cidr(s):
    return ipaddress.ip_network(s, strict=False)


def _port_span(v):
    if isinstance(v, int):
        return 1
    a, b = map(int, v.split("-"))
    return b - a + 1


def semantic(objs, errors):
    err = lambda o, rule, msg: errors.append(f"{o.where()} {rule}: {msg}")

    # --- uniqueness per namespace
    byname = collections.defaultdict(dict)  # ns -> name -> obj
    for o in objs:
        ns = NAMESPACE_OF[o.kind]
        if o.name in byname[ns]:
            err(o, "unique-name", f"name already used by {byname[ns][o.name].where()} (shared {ns} namespace)")
        else:
            byname[ns][o.name] = o
    addr, svc, net, colors = byname["address"], byname["service"], byname["network"], byname["color"]

    def ref(o, ns_table, name, field, allowed_kinds=None):
        t = ns_table.get(name)
        if t is None:
            err(o, "dangling-ref", f"{field} references unknown object '{name}'")
            return None
        if allowed_kinds and t.kind not in allowed_kinds:
            err(o, "wrong-kind", f"{field} references {t.kind}/{name}, expected one of {sorted(allowed_kinds)}")
        return t

    # --- Color: unique hex, predefined hex immutable, name of a predefined colour implies predefined
    seen_hex = {}
    for o in objs:
        if o.kind != "Color":
            continue
        h = o.spec["hex"].lower()
        if h in seen_hex:
            err(o, "duplicate-hex", f"hex {o.spec['hex']} already used by Color '{seen_hex[h]}' (two names for one colour defeats the classification)")
        seen_hex[h] = o.name
        if o.spec.get("predefined"):
            exp = PREDEFINED_PALETTE.get(o.name)
            if exp is None:
                err(o, "predefined-unknown", f"'{o.name}' is marked predefined but is not in the shipped palette {sorted(PREDEFINED_PALETTE)}")
            elif exp.lower() != h:
                err(o, "predefined-hex", f"predefined colour '{o.name}' must keep hex {exp}; annotate 'meaning' instead, or define a new Color")
        elif o.name in PREDEFINED_PALETTE:
            err(o, "predefined-shadow", f"'{o.name}' is a predefined colour name; set predefined: true or choose another name")

    # --- metadata.color references on every object
    for o in objs:
        c = (o.doc.get("metadata") or {}).get("color")
        if c is not None:
            ref(o, colors, c, "metadata.color", {"Color"})

    # --- Interface
    for o in objs:
        if o.kind != "Interface":
            continue
        if o.spec["type"] == "vlan":
            p = ref(o, net, o.spec["parent"], "spec.parent", {"Interface"})
            if p and p.spec.get("type") != "physical":
                err(o, "vlan-parent", "parent of a VLAN Interface must be a physical Interface")
        ra = (o.spec.get("ipv6") or {}).get("routerAdvertisement") or {}
        if "delegatedPrefixFrom" in ra:
            src = ref(o, net, ra["delegatedPrefixFrom"], "spec.ipv6.routerAdvertisement.delegatedPrefixFrom", {"Interface"})
            if src and (src.spec.get("ipv6") or {}).get("mode") != "dhcpv6-pd":
                err(o, "pd-source", f"delegatedPrefixFrom '{src.name}' is not in dhcpv6-pd mode")
    # duplicate (parent, vlanId) and duplicate device
    seen_vlan, seen_dev = {}, {}
    for o in objs:
        if o.kind != "Interface":
            continue
        if o.spec["type"] == "vlan":
            k = (o.spec["parent"], o.spec["vlanId"])
            if k in seen_vlan:
                err(o, "duplicate-vlan", f"VLAN {k[1]} on '{k[0]}' already defined by {seen_vlan[k].name}")
            seen_vlan[k] = o
        else:
            d = o.spec["device"]
            if d in seen_dev:
                err(o, "duplicate-device", f"device '{d}' already used by {seen_dev[d].name}")
            seen_dev[d] = o

    # --- Zone: members exist, are Interfaces, belong to at most one Zone
    zone_of = {}
    for o in objs:
        if o.kind != "Zone":
            continue
        for i in o.spec["interfaces"]:
            t = ref(o, net, i, "spec.interfaces[]", {"Interface"})
            if t:
                if i in zone_of:
                    err(o, "zone-overlap", f"Interface '{i}' already belongs to Zone '{zone_of[i]}'")
                zone_of[i] = o.name

    # --- Address
    for o in objs:
        if o.kind != "Address":
            continue
        if "interface" in o.spec:
            ref(o, net, o.spec["interface"], "spec.interface", {"Interface"})
        if "range" in o.spec:
            a, b = ipaddress.ip_address(o.spec["range"]["start"]), ipaddress.ip_address(o.spec["range"]["end"])
            if a.version != b.version:
                err(o, "range-family", "range start and end must be the same IP family")
            elif a > b:
                err(o, "range-order", "range start must be <= end")
        if "subnet" in o.spec:
            try:
                _cidr(o.spec["subnet"])
            except ValueError as e:
                err(o, "cidr", str(e))

    # --- groups: members exist, no cycles
    def check_group(kind, table, allowed):
        graph = {o.name: o.spec["members"] for o in objs if o.kind == kind}
        for o in objs:
            if o.kind != kind:
                continue
            for m in o.spec["members"]:
                ref(o, table, m, "spec.members[]", allowed)
        # DFS cycle detection
        WHITE, GREY, BLACK = 0, 1, 2
        color = {n: WHITE for n in graph}

        def dfs(n, path):
            color[n] = GREY
            for m in graph.get(n, []):
                if m not in graph:
                    continue
                if color[m] == GREY:
                    err(table[n], "group-cycle", "cycle: " + " -> ".join(path + [m]))
                elif color[m] == WHITE:
                    dfs(m, path + [m])
            color[n] = BLACK

        for n in graph:
            if color[n] == WHITE:
                dfs(n, [n])

    check_group("AddressGroup", addr, {"Address", "AddressGroup"})
    check_group("ServiceGroup", svc, {"Service", "ServiceGroup"})

    # --- VirtualIP
    for o in objs:
        if o.kind != "VirtualIP":
            continue
        ref(o, net, o.spec["externalInterface"], "spec.externalInterface")
        pf = o.spec.get("portForwarding")
        if pf and _port_span(pf["externalPort"]) != _port_span(pf["mappedPort"]):
            err(o, "vip-port-span", "externalPort and mappedPort ranges must have the same size")
        ea = o.spec["externalAddress"]
        if ea != "interface" and ipaddress.ip_address(ea).version != ipaddress.ip_address(o.spec["mappedAddress"]).version:
            err(o, "vip-family", "externalAddress and mappedAddress must be the same IP family (NAT64 is not done via VirtualIP)")

    # --- PolicySet
    pairs = {}
    for o in objs:
        if o.kind != "PolicySet":
            continue
        f, t = o.spec["from"], o.spec["to"]
        ref(o, net, f, "spec.from")
        ref(o, net, t, "spec.to")
        if f == t and net.get(f) and net[f].kind == "Interface":
            err(o, "same-interface", "from and to cannot be the same Interface (use a Zone for intra-zone traffic)")
        if (f, t) in pairs:
            err(o, "duplicate-pair", f"PolicySet for ({f} -> {t}) already defined by {pairs[(f, t)].name}")
        pairs[(f, t)] = o
        names = set()
        for i, p in enumerate(o.spec["policies"]):
            fld = f"spec.policies[{i}]"
            if p["name"] in names:
                err(o, "duplicate-policy", f"{fld}: policy name '{p['name']}' repeated in this PolicySet")
            names.add(p["name"])
            for side in ("source", "destination"):
                for a in p[side]:
                    if a == "any":
                        continue
                    tgt = ref(o, addr, a, f"{fld}.{side}[]", ADDRESS_NS)
                    if tgt and tgt.kind == "VirtualIP":
                        if side == "source":
                            err(o, "vip-as-source", f"{fld}: VirtualIP '{a}' cannot be a source")
                        elif p["action"] != "accept":
                            err(o, "vip-drop", f"{fld}: a VirtualIP destination requires action=accept")
                        elif tgt.spec["externalInterface"] != f and zone_of.get(tgt.spec["externalInterface"]) != f:
                            err(o, "vip-interface", f"{fld}: VirtualIP '{a}' is bound to '{tgt.spec['externalInterface']}', which is not the incoming side '{f}'")
                    if tgt and tgt.kind == "Address" and "mac" in tgt.spec and side == "destination":
                        err(o, "mac-as-destination", f"{fld}: MAC Address '{a}' can only be used as source")
            for s in p["service"]:
                if s != "any":
                    ref(o, svc, s, f"{fld}.service[]", SERVICE_NS)

    # --- orphan warnings are out of scope here (would be `songbird lint`)


def load_dir(root):
    objs, errors = [], []
    files = sorted(p for p in pathlib.Path(root).rglob("*.y*ml"))
    for f in files:
        try:
            docs = list(yaml.safe_load_all(f.read_text()))
        except yaml.YAMLError as e:
            errors.append(f"{f}:0 yaml: {e}")
            continue
        for i, d in enumerate(docs):
            if d is None:
                continue
            if not isinstance(d, dict):
                errors.append(f"{f}:{i} yaml: document is not a mapping")
                continue
            objs.append(Obj(str(f), i, d))
    return objs, errors


def main(argv):
    if len(argv) != 2:
        print(__doc__); return 2
    objs, errors = load_dir(argv[1])
    v = load_schema()
    ok = structural(v, objs, errors)
    # semantic checks only across structurally valid objects (and only kinds we know)
    semantic([o for o in ok if o.kind in NAMESPACE_OF], errors)
    for e in errors:
        print("ERROR", e)
    print(f"{len(objs)} objects, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
