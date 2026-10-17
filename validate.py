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

ADDRESS_NS = {"Address", "AddressGroup"}
SERVICE_NS = {"Service", "ServiceGroup"}
NETWORK_NS = {"Interface", "Zone"}
NAMESPACE_OF = ({k: "address" for k in ADDRESS_NS} | {k: "service" for k in SERVICE_NS}
                | {k: "network" for k in NETWORK_NS} | {"RuleSet": "ruleset", "Color": "color", "System": "system"})

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
                err(o, "predefined-hex", f"predefined colour '{o.name}' must keep hex {exp}; annotate metadata.comment instead, or define a new Color")
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

    # --- System: singleton, references
    systems = [o for o in objs if o.kind == "System"]
    if len(systems) > 1:
        for o in systems[1:]:
            err(o, "system-singleton", f"only one System object is allowed; first defined at {systems[0].where()}")
    for o in systems:
        adm = o.spec.get("admin") or {}
        for a in adm.get("trustedHosts", []):
            ref(o, addr, a, "spec.admin.trustedHosts[]", {"Address", "AddressGroup"})
        for sec in ("ntp", "dns"):
            for i in (o.spec.get(sec) or {}).get("serveToInterfaces", []):
                ref(o, net, i, f"spec.{sec}.serveToInterfaces[]")
        for i in ((o.spec.get("logging") or {}).get("anonymizeSourceIp") or {}).get("interfaces", []):
            ref(o, net, i, "spec.logging.anonymizeSourceIp.interfaces[]", {"Interface"})
        dns = o.spec.get("dns") or {}
        if dns.get("dns64") and not (o.spec.get("nat64") or {}).get("enabled"):
            err(o, "dns64-without-nat64", "spec.dns.dns64 requires spec.nat64.enabled: true")
        if dns.get("mode") == "recursive" and "upstreams" in dns:
            err(o, "recursive-upstreams", "spec.dns.upstreams is meaningless in recursive mode")

    def single_host(a):
        if "subnet" in a.spec:
            n = _cidr(a.spec["subnet"]); return n.num_addresses == 1
        return "range" in a.spec

    # --- RuleSet
    pairs = {}
    for o in objs:
        if o.kind != "RuleSet":
            continue
        f, t = o.spec["from"], o.spec["to"]
        ref(o, net, f, "spec.from")
        ref(o, net, t, "spec.to")
        if f == t and net.get(f) and net[f].kind == "Interface":
            err(o, "same-interface", "from and to cannot be the same Interface (use a Zone for intra-zone traffic)")
        if (f, t) in pairs:
            err(o, "duplicate-pair", f"RuleSet for ({f} -> {t}) already defined by {pairs[(f, t)].name}")
        pairs[(f, t)] = o
        names = set()
        for i, r in enumerate(o.spec["rules"]):
            fld = f"spec.rules[{i}]"
            if r["name"] in names:
                err(o, "duplicate-rule", f"{fld}: rule name '{r['name']}' repeated in this RuleSet")
            names.add(r["name"])
            for side in ("source", "destination"):
                for a in r[side]:
                    if a == "any":
                        continue
                    tgt = ref(o, addr, a, f"{fld}.{side}[]", ADDRESS_NS)
                    if tgt and tgt.kind == "Address" and "mac" in tgt.spec and side == "destination":
                        err(o, "mac-as-destination", f"{fld}: MAC Address '{a}' can only be used as source")
            for sname in r["service"]:
                if sname != "any":
                    ref(o, svc, sname, f"{fld}.service[]", SERVICE_NS)
            nat = r.get("nat")
            if not nat:
                continue
            tip = nat.get("translateIpTo")
            if tip is not None:
                a = ref(o, addr, tip, f"{fld}.nat.translateIpTo", {"Address"})
                if a and ("fqdn" in a.spec or "mac" in a.spec):
                    err(o, "nat-address-kind", f"{fld}.nat.translateIpTo: '{tip}' must be a subnet or range Address, not fqdn/mac")
                elif a and nat["type"] == "dnat" and not single_host(a):
                    err(o, "dnat-single-host", f"{fld}.nat.translateIpTo: '{tip}' must be a single host (/32, /128) or a range")
            if nat["type"] == "dnat":
                if r["destination"] == ["any"]:
                    err(o, "dnat-any-destination", f"{fld}: a dnat rule needs an explicit destination (the public address), not 'any'")
                tst = nat.get("translateServiceTo")
                if tst is not None:
                    if r["service"] == ["any"]:
                        err(o, "dnat-any-service", f"{fld}: translateServiceTo requires an explicit service, not 'any'")
                    sv = ref(o, svc, tst, f"{fld}.nat.translateServiceTo", {"Service"})
                    if sv:
                        protos = sv.spec["protocols"]
                        if len(protos) != 1 or protos[0]["protocol"] not in ("tcp", "udp", "sctp") or not isinstance(protos[0].get("port"), int):
                            err(o, "dnat-service-shape", f"{fld}.nat.translateServiceTo: '{tst}' must have exactly one tcp/udp/sctp entry with a single port")
                        else:
                            # protocol of the translated service must appear in the rule's service(s)
                            rule_protos = set()
                            for sname in r["service"]:
                                x = svc.get(sname)
                                if x and x.kind == "Service":
                                    rule_protos |= {pe["protocol"] for pe in x.spec["protocols"]}
                                elif x:  # group: expand one level is enough for the check to be useful
                                    for m in x.spec["members"]:
                                        y = svc.get(m)
                                        if y and y.kind == "Service":
                                            rule_protos |= {pe["protocol"] for pe in y.spec["protocols"]}
                            if rule_protos and protos[0]["protocol"] not in rule_protos:
                                err(o, "dnat-protocol-mismatch", f"{fld}: translateServiceTo uses {protos[0]['protocol']} but the rule's service has {sorted(rule_protos)}")

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
