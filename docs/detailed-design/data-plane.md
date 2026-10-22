# Songbird – Data Plane, Detailed Design

| | |
|---|---|
| **Document** | DD-DP – Data Plane detailed design |
| **Version** | 0.1.1-draft (milestone M0 deliverable) |
| **Status** | Draft for team review |
| **Codes against** | `docs/architecture/dataplane.md` v3.3 (design and rationale — **not** repeated here) |
| **Decisions** | ADR-0002 (forwarding model), ADR-0003 (own conntrack), ADR-0004 (policy change), ADR-0005 (fragments), ADR-0006 (capacity limits), ADR-0010 (DNAT in Policy) |
| **Requirements** | R-001.1, R-001.2, R-002, R-003, R-010…R-014.5, R-026, R-026.1, R-033, R-045, R-045.1, R-045.2, R-046.1…R-046.3, R-053; C-001 |
| **Tested by** | Test Plan suites S2 (PARSE), S3 (CLASS), S4 (CT), S5 (FWD), S6 (NAT), S8 (PERF smoke) |
| **Built in** | M2 (this document), M4 (§8 NAT) |

Rule of thumb: `dataplane.md` answers *why*, this document answers *what exactly, in which bytes*. If the two disagree, this document wins for M2 and `dataplane.md` must be updated in the same PR.

---

## 1. Program inventory

Three BPF programs, two attach families. Tail calls split the XDP path so each program stays small for the verifier (risk R1).

| Program | Attach | Type | Entry / called |
|---|---|---|---|
| `sb_xdp_parse` | XDP, native (drv) mode where the driver supports it, automatic fallback to generic (skb) with a logged warning (ADR-0013); every **physical** Interface (never on VLAN sub-devices) | `SEC("xdp")` | Entry point |
| `sb_xdp_classify` | tail-call slot 1 | xdp | called by `sb_xdp_parse` |
| `sb_xdp_ct` | tail-call slot 2 | xdp | called by `sb_xdp_parse` (fallback: inline if slots are free) |
| `sb_tc_in` | TC ingress on every logical Interface (**TCX**, kernel ≥ 6.6, ADR-0013; no clsact path) | `SEC("tc")` | Entry point |
| `sb_tc_egress` | TC egress on every logical Interface | `SEC("tc")` | Entry point |

**Tail-call map** `tail_calls` (`BPF_MAP_TYPE_PROG_ARRAY`, 4 entries): slot 0 = self (re-attach helper), 1 = classify, 2 = conntrack. A tail call that fails (program not loaded yet) falls through to the inline slow path — the pipeline must work, slower, even with an empty tail-call map. Hot reload (R-036, post-0.1) replaces slot contents with `link.Update()`.

**Context handoff XDP → TC** (dataplane.md §4): metadata via `bpf_xdp_adjust_meta`. The struct is 32 bytes (a multiple of 4, as `data_meta` requires) and carries everything TC needs, so TC never re-looks-up `dnat_candidates`:

```c
struct sb_meta {            // 32 bytes, in xdp_md->data_meta
    __u32 flow_id;          //  0: hash of the CT key, for TC-side correlation
    __u16 logical_if;       //  4: ingress logical Interface id
    __u16 flags;            //  6: SB_META_F_DNAT | SB_META_F_REVSNAT | SB_META_F_LOCAL
    __u16 ruleset_id;       //  8: 0 = none
    __u16 rule_idx;         // 10: matching Policy in the effective list (< MAX_RULES_PER_RULESET)
    __u16 dnat_id;          // 12: 0 = none (kept for events and counters)
    __be16 new_port;        // 14: DNAT target port (valid if SB_META_F_DNAT)
    __u8  new_addr[16];     // 16: DNAT target address, 128-bit form (valid if SB_META_F_DNAT)
};
```

## 2. Map inventory

Generation-scoped maps live inside an outer `ARRAY_OF_MAPS` with 2 slots (§5); everything else is global. `GEN` marks generation scope.

| Map | Type | Key | Value | max_entries | GEN |
|---|---|---|---|---|---|
| `if_logical` | HASH | `{__u32 phys_ifindex; __u16 vlan_id; __u16 pad}` | `__u16 logical_if` | 256 | no |
| `rulesets` | HASH | `{__u16 in_if, out_if}` | `__u16 ruleset_id` | 256 (ADR-0006) | no* |
| `lpm_policy` | LPM_TRIE | `{__u32 prefixlen; __u16 ruleset_id; __u8 addr[16]}` | `struct bitmap` (128 B) | 262 144 | GEN |
| `port_class_tcp` / `port_class_udp` | ARRAY | `__u16 port` | `__u16 port_class` | 65 536 | GEN |
| `svc_bitmap` | ARRAY | `{__u16 ruleset_id; __u16 class}` | `struct bitmap` | 256 × 1 024 | GEN |
| `ruleset_meta` | ARRAY | `__u16 ruleset_id` | `{__u16 n_rules; __u16 flags; __u32 gen}` | 256 | GEN |
| `rule_names` | HASH | `{__u16 ruleset_id; __u32 rule_idx}` | `{char ruleset[64]; char policy[64]}` | 65 536 | GEN |
| `ct_main` | LRU_HASH | `struct ct_key` | `struct ct_entry` | 1 048 576 | no |
| `ct_syn` | LRU_HASH | `struct ct_key` | `struct ct_entry` | 65 536 | no |
| `frag_v4` | LRU_HASH | `{__u8 saddr[16], daddr[16]; __u16 id; __u8 proto}` | `__u8 verdict` | 65 536 | no |
| `dnat_candidates` | HASH | `{__u16 in_if; __u8 proto; __u8 pad; __u8 addr[16]; __be16 port}` | `{__u16 dnat_id, ruleset_id; __u32 rule_idx; __u8 new_addr[16]; __be16 new_port}` | 16 384 (ADR-0006) | GEN |
| `snat_rev` | LRU_HASH | `struct ct_key` (post-SNAT tuple) | `struct ct_key` (original) | 524 288 | no |
| `blocklist` | LPM_TRIE | `{__u32 prefixlen; __u8 addr[16]}` | `__u8 dummy` | 262 144 | GEN |
| `counters_rule` | PERCPU_ARRAY | `{__u16 ruleset_id; __u32 rule_idx}` | `{__u64 packets, bytes}` | 65 536 | GEN |
| `counters_drop` | PERCPU_ARRAY | `__u32 reason` | `__u64 count` | 32 | no |
| `counters_misc` | PERCPU_ARRAY | `__u32 idx` | `__u64 count` | 16 (`events_lost`, `snat_exhausted`, …) | no |
| `events` | RINGBUF | — | `struct flow_event` | 8 MiB (ADR-0006) | no |
| `gen_ctl` | ARRAY | `__u32 0` | `{__u32 active_gen; __u32 gen_seq}` | 1 | no |
| `gen_maps` | ARRAY_OF_MAPS | `__u32 slot` | inner-map fd | 2 | — |
| `tail_calls` | PROG_ARRAY | `__u32 slot` | prog fd | 4 | no |

\* `rulesets` is rewritten on Apply like the GEN maps, but it is tiny; it lives outside `gen_maps` only because the FIB lookup needs it before the generation is read. Alternative (preferred if simple): read `active_gen` first, then everything GEN including `rulesets`. **Decision needed in M2, task M2-01.**

All GEN maps are sized with the ADR-0006 limits; the Validator (DM-36) guarantees an Apply never exceeds them.

## 3. Structs (wire layout)

Compiled with `bpf2go`; every struct has an explicit `version` field where migration (hot reload) may matter. Packed, no implicit padding beyond what is listed.

```c
#define SB_BITMAP_WORDS 16          // MAX_RULES_PER_RULESET = 1024 (ADR-0006)
struct bitmap { __u64 w[SB_BITMAP_WORDS]; };          // 128 B

struct ct_key {                     // 40 B
    __u8  saddr[16], daddr[16];     // IPv4-mapped ::ffff:a.b.c.d (dataplane.md §5)
    __be16 sport, dport;            // ICMP: id + type
    __u8  proto, pad[3];
};

struct ct_entry {                   // 96 B, same fields as dataplane.md §9
    __u64 last_seen_ns;             //  0
    __u64 packets, bytes;           //  8, 16  per direction
    __u32 policy_gen;               // 24  gen_seq that accepted the Flow (ADR-0004)
    __u16 rule_idx;                 // 28  Policy index within the RuleSet (< 1024)
    __u16 ruleset_id;               // 30
    __u16 flags;                    // 32  DIR_REPLY, SEEN_REPLY, NAT_SNAT, NAT_DNAT, LOCAL
    __u8  tcp_state;                // 34  §6
    __u8  version;                  // 35  = 1 (was `pad` in dataplane.md)
    __u16 dnat_id;                  // 36  0 = none
    __be16 nat_port;                // 38
    __u8  nat_addr[16];             // 40  translated address applied in TC
    struct ct_key peer;             // 56  key of the other direction (re-classify / delete both)
};                                  // 96, no implicit padding

struct flow_event {                 // 80 B, ring buffer record (R-026)
    __u64 ts_ns;                    //  0
    __u32 policy_gen;               //  8  with ruleset_id and rule_idx names the Policy (dataplane.md §11)
    __u32 rule_idx;                 // 12
    __u16 ruleset_id;               // 16
    __u16 in_if;                    // 18
    __u16 reason;                   // 20  §10, only for FLOW_DROP/FLOW_END
    __u8  kind;                     // 22  1 FLOW_NEW, 2 FLOW_DROP, 3 FLOW_END
    __u8  proto;                    // 23
    __u8  saddr[16], daddr[16];     // 24, 40
    __be16 sport, dport;            // 56, 58
    __u8  pad[4];                   // 60  explicit
    __u64 packets, bytes;           // 64, 72  FLOW_END only
};
```

`ct_entry` is 96 B, as assumed by ADR-0006's memory estimate (~350–400 MB for 1 M Flows, to be confirmed by the M5 benchmark); `flow_event` is 80 B (8 MiB ring buffer ≈ 100 000 records). Sizes include C alignment: **no struct has implicit padding**. Layout is a contract: the build must emit `_Static_assert(sizeof(...))` and `offsetof` checks for every struct in this section (including `sb_meta` = 32), and the Go side asserts the same sizes on the `bpf2go`-generated types.

## 4. Constants

From ADR-0006 and `System.session` defaults (RA R-045.2). Values the user can change arrive as **global variables** (`.rodata`, set by the loader before attach); the rest are `#define`.

```c
#define MAX_RULESETS            256
#define MAX_RULES_PER_RULESET   1024
#define MAX_CT                  1048576
#define MAX_CT_SYN              65536
#define MAX_DNAT                16384
#define RINGBUF_BYTES           (8 << 20)
#define SNAT_PORT_LO            32768
#define SNAT_PORT_HI            60999
#define SNAT_ALLOC_TRIES        8
#define EV_TOKENS_PER_SEC       1000    // per CPU, R-026.1

/* globals (loader-set): */
volatile const __u64 tmo_tcp_syn_ns   = 30ULL  * 1000000000;
volatile const __u64 tmo_tcp_est_ns   = 3600ULL * 1000000000;
volatile const __u64 tmo_tcp_close_ns = 10ULL  * 1000000000;
volatile const __u64 tmo_udp_ns       = 60ULL  * 1000000000;
volatile const __u64 tmo_udp_bi_ns    = 180ULL * 1000000000;
volatile const __u64 tmo_icmp_ns      = 30ULL  * 1000000000;
```

## 5. Generation swap protocol (R-020.6)

The applied state is the content of the GEN maps plus `gen_ctl.active_gen ∈ {0,1}`. Apply steps, all in the Go compiler/applier:

1. `g_new = 1 - active_gen`. Delete and recreate the inner maps at slot `g_new` of `gen_maps` (fresh, empty — no incremental edits).
2. Compile the new Configuration into the `g_new` maps (classifier bitmaps, DNAT candidates, port classes, rule names, blocklist).
3. **Self-check**: for every RuleSet, walk the effective list and verify `rule_names` and `ruleset_meta.n_rules` agree with the compiled bitmaps (cheap, catches compiler bugs before they touch traffic).
4. Flip `active_gen = g_new` (single `Map.Update` of 4 bytes; `gen_seq++`).
5. Programs read `active_gen` once per packet into a local; a packet always sees one complete generation.
6. CT entries are **not** swept. Each `ct_entry` carries `policy_gen` (the `gen_seq` that accepted it, ADR-0004). The Applier bumps `gen_seq` in step 4; the next packet in either direction of a Flow whose `policy_gen != gen_ctl.gen_seq` is re-classified (§6). `rule_idx` alone is **not** a valid staleness test: after a reorder the same index resolves to a different Policy and the Flow would silently stay permitted by the wrong rule.
7. On any failure in steps 2–3: delete slot `g_new` content, leave `active_gen` untouched, report the error. The previous state is provably intact because nothing shared was written.
8. After a successful flip, the old generation's maps stay allocated until the next Apply (instant rollback = flip back); the *second* next Apply recreates them.

Crash-resilience: maps and links are pinned under `/sys/fs/bpf/songbird/`; on restart the loader re-opens them and resumes with the pinned `active_gen` (plan exit criterion 5).

## 6. Conntrack state machine

States (`tcp_state`): `SYN_SENT=1, SYN_RECV=2, ESTABLISHED=3, FIN_WAIT=4, CLOSE=5`. UDP/ICMP use `ESTABLISHED` with their own timeouts; `SEEN_REPLY` flag distinguishes 60 s vs 180 s UDP.

Transitions (new Flows only; established packets update `last_seen_ns` and counters):

| Event | From | To | Side effects |
|---|---|---|---|
| TCP SYN, policy accept | — | `SYN_SENT` | entry in `ct_syn` only |
| SYN-ACK seen (reply direction) | `SYN_SENT` | `ESTABLISHED` | move entry `ct_syn → ct_main` (both directions) |
| RST, or FIN+FIN/ACK | any | `CLOSE` | entry stays until `tmo_tcp_close_ns`, then sweep emits `FLOW_END` |
| UDP first packet accepted | — | `ESTABLISHED` | `tmo_udp_ns`; first reply sets `SEEN_REPLY` → `tmo_udp_bi_ns` |
| ICMP echo request accepted | — | `ESTABLISHED` | `tmo_icmp_ns` |
| ICMP/ICMPv6 **error** packet | — | (no state) | parse inner header, look up the **inverted** tuple in `ct_main`; match → treat as RELATED (pass, count on that Flow); no match → normal policy path |

Timeouts are lazy: `now - last_seen > tmo(state)` during lookup ⇒ treat as new Flow (and emit `FLOW_END` with reason `timeout` from the Go sweeper, which also walks `ct_main` every 10 s and deletes expired entries).

SYN-flood protection (dataplane.md §9): `ct_syn` is small (65 536) and LRU; a flood evicts only half-open entries. Promotion happens on the first reply, not on the SYN.

Policy change (ADR-0004): a packet of a Flow with `policy_gen != gen_seq` has its ORIG tuple re-classified against the active generation. Still accepted → update `policy_gen`, `rule_idx`, `ruleset_id` in both entries (the other one via `peer`) and forward. Not accepted → drop the packet, delete both entries (via `peer`), emit `FLOW_DROP` with reason `policy-change`; `FLOW_END` is never emitted from BPF. This is the only re-classification path; no mass sweep on Apply. Cost: one re-classification per active Flow per Apply.

## 7. Classifier mechanics

Effective lists are built by the Compiler (Zone expansion, dataplane.md §7.1). In the kernel:

```
bm_src = lpm_policy[{longest_prefix(saddr), ruleset_id}]
bm_dst = lpm_policy[{longest_prefix(daddr), ruleset_id}]
class  = port_class_<proto>[dport]
bm_svc = svc_bitmap[{ruleset_id, class}]
match  = bm_src & bm_dst & bm_svc            // 16 u64 ANDs
rule_idx = first_set_bit(match)              // de Bruijn on each word, first non-zero word
```

- **LPM folding (Compiler)**: the bitmap of prefix `P` must include the bits of every prefix that contains `P` (LPM returns only the longest). The Compiler computes, for each RuleSet, the bitmap of each prefix as the union of its own bits and all its ancestors', plus a `::/0` entry with the "any" bits. Address ranges are split into CIDRs first; Address Groups are flattened (flat groups, R-013).
- **Port classes (Compiler)**: global equivalence classes over all Policies' destination ports (single ports and ranges merge into classes); two 64 KiB arrays map port → class; ICMP uses `type` in the low byte of the same mechanism. A `Service` with several protocol entries contributes to each protocol's class set (R-010).
- **first_set_bit**: for each of the 16 words (unrolled), if non-zero return `64*word + debruijn64(word & -word)`; the de Bruijn table is a 64-entry `ARRAY`.
- **No match** → `XDP_DROP`, `counters_drop[DEFAULT_DENY]++`, event subject to rate limiting (§9).

Per-packet cost bound (new Flow, no DNAT): 2 LPM + 1 ARRAY + 1 ARRAY + 1 HASH(ruleset) + 1 HASH(CT) + 16 ANDs ≈ 6 lookups. Verifier budget: no loops except the unrolled 16-word AND and the bounded parser loops (≤ 2 VLAN tags, ≤ 4 chained headers reserved for IPv6 in 0.2).

## 8. NAT (M4)

**DNAT** (TC ingress, `sb_tc_in`): if `sb_meta.flags & SB_META_F_DNAT`, rewrite `daddr/dport` from `dnat_candidates[dnat_id]` (`new_addr`/`new_port` are carried in the 32-byte `sb_meta`, so TC does **not** re-lookup) using `bpf_l3_csum_replace`/`bpf_l4_csum_replace`; with checksum offload, mark `skb->ip_summed = CHECKSUM_NONE` only when the packet is not already `CHECKSUM_PARTIAL`. Both offload modes are tested (S6).

**SNAT** (TC egress, `sb_tc_egress`): on the first packet of an accepted Flow flagged `NAT_SNAT` (flag set at classification time from the Policy's `nat` section):
1. translated source = `ct_entry.nat_addr` (outgoing Interface address when `translateIpTo` is omitted, pool address otherwise — chosen by the Applier at Apply time for pools, by the kernel for the Interface case via a Go-maintained `if_addr` map: `HASH logical_if → {addr[16]}`);
2. pick port: hash of the tuple, linear probe up to `SNAT_ALLOC_TRIES` with `BPF_NOEXIST` insert into `snat_rev`; exhausted → drop + `counters_misc[snat_exhausted]++` + `FLOW_DROP` reason `snat-exhausted`;
3. write `ct_entry.nat_port`; subsequent packets of the Flow just apply `(nat_addr, nat_port)`.

**Reverse SNAT**: inbound packets hit `snat_rev` before CT lookup (the `RN` stage in the pipeline); on hit, XDP tags `SB_META_F_REVSNAT` and TC ingress restores the original destination.

**NAT64**: out of 0.1 scope (IPv6 arrives in 0.2); the 128-bit address representation keeps it additive.

## 9. Events and rate limiting

Emission points (R-026): `FLOW_NEW` on accepted new Flows (after CT insert), `FLOW_DROP` on every drop with reason, `FLOW_END` from the Go sweeper only (never from BPF — the kernel cannot know it is the last packet).

Rate limiting (R-026.1): per-CPU token bucket in a 2-entry `PERCPU_ARRAY` (`{tokens_ns, last_refill_ns}`): refill `EV_TOKENS_PER_SEC` per second, burst 4×; drops and new-Flow events cost 1 token; when empty, increment `counters_misc[events_lost]` instead. `bpf_ringbuf_reserve` failure also increments `events_lost`. Established-flow packets never emit.

## 10. Drop reasons (enum, wire values stable)

```
0  none
1  malformed            (parser)
2  ipv6-unsupported     (0.1 interim, R-057)
3  blocklist
4  no-ruleset
5  default-deny
6  policy-drop
7  local-in-denied
8  dnat-route-mismatch
9  dnat-shadowed
10 snat-exhausted
11 fragment-dropped     (R-053)
12 ct-invalid
```

Go mirrors this enum in one generated file; adding a reason is a schema-of-record change (both sides, one PR).

## 11. Build and test hooks (M2 work items)

| Task | Content | Suite (Test Plan) |
|---|---|---|
| M2-01 | Repo skeleton: `bpf/` + `bpf2go`, pinned clang/`cilium/ebpf`, `gen_maps` decision (§2 \*), static asserts for §3 | — (builds) |
| M2-02 | Parser: L2/VLAN×2/PPPoE-session/IPv4+IHL/fragments; 128-bit normalisation; ARP/DHCP-to-firewall pass-through | S2 |
| M2-03 | Classifier + Compiler bitmaps + generation swap; reference Go classifier; fuzz equivalence ≥ 10⁶ packets (R-014.4) | S3 |
| M2-04 | Conntrack FSM, SYN map, RELATED, timeouts, sweep; ring-buffer events + rate limiting | S4 |
| M2-05 | netns topology helper (client – songbird – server, VLAN variant) | S5 base |
| M2-06 | Local-in path: `allowAccess` + System Services ports admitted without Policy (R-056/R-058) | S5 |
| M4-01 | DNAT in TC ingress + metadata handoff | S6 |
| M4-02 | SNAT + reverse SNAT + port allocation | S6 |

Every task ends with its suite green on CI-bpf; S3 fuzz may run nightly if over the per-PR budget (Test Plan open item 3).

## 12. Open items for M2

| # | Item | Blocks | Resolution |
|---|---|---|---|
| 1 | `rulesets` map inside or outside the GEN scope (§2 \*) | M2-01 | M2-01 decides, one ADR line if it contradicts dataplane.md |
| 2 | TCX vs clsact attach | — | Resolved by ADR-0013 (TCX, kernel ≥ 6.6); pending its acceptance and spike 7.1 |
| 3 | PPPoE: does XDP metadata survive to TC on `ppp0`? | WAN on FTTH | spike 7.2; fallback: re-lookup in TC |
| 4 | Exact `ct_entry` layout (§3 note) | M2-01 | static asserts are the contract |

---

## 13. Change log

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1.0-draft | 2026-10-21 | Hermes (for team review) | v0 for M0: program/map inventory, wire structs, constants, generation-swap protocol, CT FSM, classifier mechanics, NAT detail, events and rate limiting, drop-reason enum, M2/M4 task breakdown mapped to Test Plan suites. |
| 0.1.1-draft | 2026-10-23 | Hermes (for team review) | Review fixes: `ct_entry` realigned to dataplane.md §9 (adds `policy_gen` and `peer`, 96 B, no implicit padding); `flow_event` 80 B with `policy_gen`; `sb_meta` widened to 32 B to carry the DNAT target; staleness test uses `policy_gen`, not `rule_idx` (ADR-0004); attach choice aligned with ADR-0013. |
