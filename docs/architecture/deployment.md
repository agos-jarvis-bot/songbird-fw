# Songbird – Deployment view

| | |
|---|---|
| **Document** | Deployment view |
| **Version** | 0.1.0-draft (release 0.1 only) |
| **Status** | Draft for team review |
| **Inputs** | Project Plan §2.2, §3; ADR-0013 (kernel floor, proposed); ADR-0015 (single Go binary); ADR-0016 (embedded BPF); ADR-0017 (Hadron, deferred to 0.3); C-004; R-031, R-033.1, R-038 |

> This view covers **release 0.1**: Songbird as a package on a stock Debian VM. The immutable Hadron image with A/B updates is the 0.3 deployment and lives in ADR-0017; nothing here is designed to be thrown away — the same binary, paths and systemd contract carry over to the image.

---

## 1. Target environment

| Aspect | 0.1 choice | Why / notes |
|---|---|---|
| OS | **Debian 13** (stable), minimal install, x86-64 | Kernel 6.12 ≥ 6.6 floor (ADR-0013); Debian 12 (6.1) unsupported |
| Form | KVM/Proxmox/VMware/VirtualBox VM, or bare metal for benchmarks (ADR-0007) | The team's lab is Proxmox; see §6 |
| vCPU / RAM | 2 vCPU, 2 GiB recommended; 1 vCPU, 1 GiB minimum | Conntrack at the ADR-0006 limits needs ~0.5 GiB of maps; 2 GiB leaves margin |
| NICs | ≥ 2: one WAN, one LAN; or one trunk NIC with 802.1Q sub-interfaces | XDP attaches to **physical** devices only (dataplane.md §5) |
| Runtime deps | **none** beyond the kernel and systemd | The binary is static (`CGO_ENABLED=0`, C-004) with BPF objects, JSON Schema and (from 0.2) UI assets embedded; `clang` is a build-time dep only |
| Privileges | systemd service with a dedicated user and ambient capabilities (§4) | Validated in M3; the set can only shrink |

## 2. Artifacts and filesystem layout

One package: `songbird_<version>_amd64.deb` (a plain tarball with the same layout is also produced for non-Debian testing; the `.deb` is the supported path, Project Plan decision #6).

| Path | Content | Owner / mode |
|---|---|---|
| `/usr/sbin/songbird` | The single static binary | root:root 0755 |
| `/usr/lib/songbird/prestart` | Privileged boot helper (§4) | root:root 0750 |
| `/var/lib/songbird/config/` | The **local Git repository** — the configuration, source of truth (ADR-0001) | songbird:songbird 0750 |
| `/var/lib/songbird/data/` | Runtime data that survives restarts (e.g. sealed secrets, R-020.5, from 0.3) | songbird:songbird 0750 |
| `/var/lib/songbird/log/` | Traffic Log and Audit Log, rotated (R-029, R-035.1) | songbird:songbird 0750 |
| `/etc/songbird/songbird.env` | Optional service overrides (listen address, data dir) — not configuration: configuration is the Git repo | root:songbird 0640 |
| `/sys/fs/bpf/songbird/` | Pinned maps and links (bpffs) | created by `prestart` |
| `/usr/lib/sysctl.d/60-songbird.conf` | `net.ipv4.ip_forward=1`, `net.ipv6.conf.all.forwarding=1` (from 0.2) | root:root 0644 |
| `/usr/lib/tmpfiles.d/songbird.conf` | Creates the `/var/lib/songbird` tree on install/boot | root:root 0644 |
| `/usr/lib/systemd/system/songbird.service` | The unit (§4) | root:root 0644 |

Upgrade in 0.1: `apt install ./songbird_<new>.deb` → the unit restarts, the new binary **re-attaches to the pinned maps** and keeps filtering with the last applied generation while the Control Plane comes up (R-033.1, detailed-design/data-plane.md §5). Downgrade is installing the previous `.deb`; there is **no A/B mechanism before 0.3** (R-019).

## 3. Boot and runtime sequence

1. `systemd` runs `prestart` as root: mounts bpffs if needed, creates `/sys/fs/bpf/songbird`, hands it to the service user, loads the sysctl file.
2. `songbird` starts; **preflight** (`test/env` rules, Test Plan §5): kernel ≥ 6.6, bpffs writable, CAP set present, `ip_forward` on. Failure → exit non-zero with the missing piece named; systemd logs it.
3. Config Manager opens `/var/lib/songbird/config`. If the repository is missing or has no valid commit → **Initial Setup** (R-031): factory defaults are written (LAN `192.168.1.1/24` on the first non-WAN Interface with `allowAccess: ["https"]`), and the wizard is served **only on Interfaces with HTTPS management enabled** (R-031.1, R-056) until the first commit exists.
4. Reconciler: read HEAD → validate (schema + semantic rules; a corrupt tree never applies, R-020.3) → compile → apply atomically (R-020.6) → status. On restart after a crash it re-attaches to the pinned maps instead of reloading (R-033.1).
5. API/UI listens on the configured HTTPS port (R-038; default 443 in production, the example configuration shows 8443) with HTTP→HTTPS redirect (R-038.1). Authentication is required for everything except `/health` and the login form (R-043).

## 4. The systemd unit (as shipped)

```ini
[Unit]
Description=Songbird firewall (eBPF data plane, GitOps control plane)
Documentation=https://github.com/songbird-fw/songbird-fw
After=network-pre.target bpffs.mount
Wants=network-pre.target
Before=network.target

[Service]
Type=notify
User=songbird
Group=songbird
EnvironmentFile=-/etc/songbird/songbird.env
# privileged one-shot setup (the '+' runs it as root)
ExecStartPre=+/usr/lib/songbird/prestart
ExecStart=/usr/sbin/songbird serve
AmbientCapabilities=CAP_BPF CAP_PERFMON CAP_NET_ADMIN CAP_NET_RAW
CapabilityBoundingSet=CAP_BPF CAP_PERFMON CAP_NET_ADMIN CAP_NET_RAW
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/songbird /sys/fs/bpf/songbird
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK AF_PACKET
RestrictNamespaces=true
LockPersonality=true
Restart=on-failure
RestartSec=2s
WatchdogSec=30s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

Notes:
- **CAP_SYS_ADMIN is deliberately absent**: bpffs mounting is the one operation that needs it, so it is isolated in the `+`-prefixed `prestart` helper. Everything else runs as the `songbird` user with four capabilities. The set is validated in M3 and may only shrink (e.g. CAP_PERFMON proves unnecessary if ring buffer reads stay within CAP_BPF).
- `Type=notify` + watchdog: a wedged Control Plane is restarted while the pinned Data Plane keeps filtering (§3.4).
- The unit never stops the data plane on `systemctl stop`: maps and links stay pinned and packets keep flowing with the last generation; a stop is a Control Plane restart, not a firewall outage. `systemctl stop songbird` followed by uninstall is the only path that unpins (`prestart --cleanup`, run by the package's `postrm`).

## 5. Network ownership in 0.1 (interim)

Songbird manages **only the Interfaces named in its configuration**: addresses, VLAN sub-interfaces, static routes (R-001.5), sysctls on those Interfaces, `rxvlan` offload (ADR-0013). Everything else on the host is left untouched. Two practical consequences for the stock VM:

- Do **not** let netplan/networkd configure the Interfaces Songbird owns: the install docs ship a netplan snippet that marks them `unmanaged`. (The full "who owns the network configuration" decision is a candidate ADR in `docs/architecture/README.md`; 0.1's answer is: Songbird owns what its YAML names.)
- Out-of-band access: keep the hypervisor console reachable. A bad first Apply can lock SSH out of the managed Interfaces; console access is the 0.1 recovery path (R-031's wizard listens on the LAN Interface).

## 6. Hypervisor notes (Proxmox reference lab)

| Choice | Consequence |
|---|---|
| **VirtIO NICs** | No native XDP → generic (skb) mode: correct, slower; fine for functional 0.1 work. ADR-0013 logs a warning and surfaces the mode in `/health`. |
| **PCIe passthrough (Intel i225/i226, X520/X710 class)** | Native XDP; required for the M5 benchmark numbers (C-003/ADR-0007). |
| **vLAN on the hypervisor vs guest** | For the 0.1 VLAN tests (R-001.2) tag inside the guest: bridge ports stay untagged. |
| **Live migration** | Untested in 0.1; the pinned maps and CT state do not migrate. Treat the firewall VM as pinned to a node. |

## 7. Quick start (0.1, as it will appear in the README)

```bash
# Debian 13 VM, 2 NICs (wan on ens18, lan on ens19), console reachable
curl -LO https://github.com/songbird-fw/songbird-fw/releases/download/v0.1.0/songbird_0.1.0_amd64.deb
sudo apt install ./songbird_0.1.0_amd64.deb
sudo systemctl enable --now songbird
systemctl status songbird          # preflight must pass (kernel, caps, bpffs)
# from a host on the LAN:
xdg-open https://192.168.1.1       # wizard (R-031) → first admin, WAN/LAN → first commit
```

Verification right after install: `songbird validate /var/lib/songbird/config` (R-052) and `curl -k https://<lan-ip>/health` (R-032).

## 8. Explicitly not part of 0.1 deployment

Immutable rootfs, A/B partitions and rollback boot (R-019, ADR-0017 → 0.3); TPM/sealed secrets at rest (R-020.5, ADR-0009 → 0.3); HA/VRRP (R-023 → post-1.0 candidate); live migration support; cloud images other than the Debian 13 base.

---

## 9. Change log

| Version | Date | Author | Summary |
|---|---|---|---|
| 0.1.0-draft | 2026-10-21 | Hermes (for team review) | 0.1 deployment view: Debian 13 VM target, package layout, hardened systemd unit with prestart helper, boot/preflight/reconcile sequence, network ownership interim, Proxmox notes, quick start, 0.3 deferrals. |
