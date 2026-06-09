# Deploy guide — octos → nav-base-dora-node (zero to driving a base)

This is the **complete, newcomer-facing setup** for controlling a mobile base from
[octos](https://github.com/dorarobotics/octos), from a clean machine all the way to
issuing `go_to_pose` against this node. You'll stand up four things, in order:

```
octos (Agentic OS, Rust)
   │  HTTP POST /tools/<verb>
   ▼
octos-dora-bridge      (SPEC ⇄ HTTP bridge: a dora node + FastAPI on :8769)
   │  dora cmd_request / cmd_response
   ▼
nav-base-dora-node     ← THIS REPO (SPEC-VENDOR-NODE-V1 adapter)
   │  dora topics: goal / cancel / cmd_vel  ↕  pose / status / obstacles
   ▼
dora-nav stack         (real SLAM/planning/control)  — or fakes for sim
```

octos never learns anything about dora or the robot — it just calls HTTP tools. The
**bridge** is the only translator. **nav-base-dora-node** is the per-robot adapter
that turns SPEC verbs (`base.go_to_pose`, `localization.get_pose`, …) into dora topics
that [dora-nav](https://github.com/bobdingAI/dora-nav) consumes.

Two milestones, do them in order:

- **A — Simulation (no robot, no GPU):** fake localization + planner stand in for
  dora-nav. Gets the whole octos→bridge→node path running and verified end-to-end.
- **B — Real hardware:** swap the two fake nodes for dora-nav's real binaries.

---

## 0. Prerequisites

| Need | Version / notes |
|---|---|
| OS | Linux x86_64/ARM64 or macOS ARM64. Validated on Ubuntu 22.04/24.04. |
| Python | **3.10** (3.10–3.12 OK). conda/miniforge or `venv`. |
| Rust toolchain | `cargo` — only if building octos from source (see §1). |
| `git`, `curl`, `jq` | for cloning, health checks, inspecting tool JSON. |
| dora CLI **and** Python `dora-rs` | **both pinned to the same minor — use 0.2.6.** See §2. This is the #1 source of failure. |

> ⚠️ **The single most important rule.** The dora **CLI/daemon** and the Python
> **`dora-rs`** package share a wire protocol that is **not stable across versions**.
> Both must come from the same minor release. This repo and the bridge pin
> `dora-rs>=0.2.1,<0.3`; **use 0.2.6 on both sides.** A mismatch fails at node
> registration with errors like `message format v0.5.0 is not compatible with
> expected message format v0.2.1` or `unknown variant 'socket_addr'`.
> **0.3.x is not supported** — the bridge's background sends hit `Already borrowed`.

---

## 1. Install octos (the Agentic OS)

**Option A — prebuilt release (fastest):**

```bash
curl -fsSL https://github.com/octos-org/octos/releases/latest/download/install.sh | bash
# installs to ~/.octos/bin and registers `octos serve` as a service
```

> ⚠️ **glibc gotcha.** The prebuilt release is linked against glibc 2.38/2.39. On
> **Ubuntu 22.04 (glibc 2.35)** it fails with `version 'GLIBC_2.38' not found`. Use
> **Ubuntu 24.04+**, or build from source (Option B).

**Option B — build from source (works on any glibc; needs `cargo`):**

```bash
mkdir -p ~/octos-deploy && cd ~/octos-deploy
git clone https://github.com/dorarobotics/octos.git
cd octos
cargo install --path crates/octos-cli --root ~/.octos --force    # ~15–30 min
~/.octos/bin/octos --version
export PATH="$HOME/.octos/bin:$PATH"                              # add to ~/.bashrc
```

Give octos a model provider (for the LLM agent in §6): `export ANTHROPIC_API_KEY=…`,
or point it at a local Ollama. Not needed for the HTTP/curl path in §5.

---

## 2. Install the dora CLI (version-matched)

```bash
cargo install dora-cli --locked --version 0.2.6      # or grab the 0.2.6 release binary
dora --version                                        # MUST report 0.2.6
```

The Python `dora-rs==0.2.6` gets installed by pip in §4 — keep both at 0.2.6.

> Note: the epyc reference box runs a **custom 0.2.1** build; a stock 0.2.6 on both
> sides is the recommended, reproducible combination for a fresh machine.

---

## 3. Clone the repos

```bash
cd ~/octos-deploy
git clone https://github.com/dorarobotics/octos-dora-bridge.git
git clone https://github.com/dorarobotics/nav-base-dora-node.git   # THIS repo
# dora-nav is only needed for Milestone B (real hardware):
git clone https://github.com/bobdingAI/dora-nav.git
```

All repos are public — no auth needed.

---

## 4. Create the venv and install the stack

The dataflows invoke a wrapper, `dataflows/venv-python`, that `exec`s
**`octos-dora-bridge/bridge/.venv/bin/python`**. So the venv **must live at that exact
path**:

```bash
cd ~/octos-deploy/octos-dora-bridge/bridge
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip

# Installs the bridge + pulls nav-base-dora-node (the `robots.nav-base` extra):
pip install -e ".[dev,robots.nav-base]"
```

> **Developing against your local nav-base clone?** The `robots.nav-base` extra pulls
> nav-base-dora-node from GitHub `@main`. To use your working copy instead, install it
> editable afterward:
> ```bash
> pip install -e ~/octos-deploy/nav-base-dora-node
> ```

Confirm both packages and dora are present in the venv:

```bash
python -c "import nav_base_node, octos_spec_bridge, dora; print('ok')"
pip show dora-rs | grep Version          # -> 0.2.6, matching the CLI
```

---

## 5. Milestone A — run the simulation and verify

The shipped `dataflows/nav-base-bridge.yaml` wires four nodes: **bridge** (HTTP :8769)
→ **nav_base** (this node) ← **fake_localization** + **fake_planner** (stand-ins for
dora-nav). It needs no robot and no GPU.

```bash
cd ~/octos-deploy/octos-dora-bridge
dora up
dora start dataflows/nav-base-bridge.yaml --attach
```

In a second terminal, verify the bridge and the SPEC verbs:

```bash
curl -fsS http://127.0.0.1:8769/healthz                       # -> {"status":"ok"}
curl -fsS http://127.0.0.1:8769/tools | jq '.tools[].name'    # lists the verbs

# Where am I?
curl -fsS -X POST http://127.0.0.1:8769/tools/vendor.dora_nav.localization.get_pose \
  -H "Content-Type: application/json" -d '{"args":{}}'

# Drive to a pose (returns OK once the goal is QUEUED — status is async):
curl -fsS -X POST http://127.0.0.1:8769/tools/vendor.dora_nav.base.go_to_pose \
  -H "Content-Type: application/json" \
  -d '{"args":{"pose":{"position":[2.0,0.0,0.0],"orientation":[0,0,0,1]},"control_source":"manual"}}'

# Emergency stop:
curl -fsS -X POST http://127.0.0.1:8769/tools/robot.estop \
  -H "Content-Type: application/json" -d '{"args":{"reason":"manual_test"}}'
```

Tear down with `Ctrl-C`, then `dora stop --grace 5 && dora destroy`.

**Verbs this node exposes** (full reference in `octos-dora-bridge/skills/nav-base/SKILL.md`):

| Verb | Args |
|---|---|
| `vendor.dora_nav.base.go_to_pose` | `{"pose": {"position":[x,y,z], "orientation":[x,y,z,w]}}` |
| `vendor.dora_nav.base.go_to_named` | `{"name": "kitchen"}` (resolved via `WAYPOINTS_PATH`) |
| `vendor.dora_nav.base.set_velocity` | `{"linear": 0.3, "angular": 0.0}` (cancels active goal) |
| `vendor.dora_nav.base.stop` | — (privileged; works during estop) |
| `vendor.dora_nav.localization.get_pose` | — → `{"x","y","theta"}` |
| `vendor.dora_nav.map.get_obstacles` | — |

### Optional: watch it in a live viewer

A turnkey visual variant boots a kinematic toy sim + a rerun top-down viewer + this
node + the bridge, then drives a scripted skill sequence (`dataflows/nav-base-viz.yml`
/ `scripts/run-nav-viz.sh` in the bridge repo). Run it from a desktop session (it opens
a rerun window) and watch the robot drive to goals, spin, stop, and halt on estop.

---

## 6. Drive it from the octos agent (skill integration)

The octos side loads a **skill** that (a) documents the verbs for the LLM and (b) runs
lifecycle hooks (preflight / init / ready_check / shutdown / emergency). Install it:

```bash
mkdir -p ~/.octos/skills
cp -r ~/octos-deploy/octos-dora-bridge/skills/nav-base ~/.octos/skills/nav-base
octos skills list        # -> nav-base
```

The skill's `init` hook starts the dataflow and `ready_check` polls
`http://127.0.0.1:8769/healthz`. Two paths the hook expects you to reconcile:

- **`init` runs `cd /opt/octos-dora-bridge && dora up && dora start
  dataflows/nav-base-bridge.yaml`.** Either symlink your clone to that path
  (`sudo ln -s ~/octos-deploy/octos-dora-bridge /opt/octos-dora-bridge`) or edit the
  command in `SKILL.md` to point at your clone.
- **`preflight`** checks `/opt/octos-dora-bridge/load_path.yml` exists **or**
  `NAV_FAKE_MAP=1` is set. For the sim, export `NAV_FAKE_MAP=1` (the node then emits a
  synthetic empty map). For real hardware, provide the waypoints/map file.

Then run the agent and talk to it:

```bash
octos serve            # serve with NAV_FAKE_MAP=1 in the env for the sim
octos chat
> go to the charger
```

> **How the LLM actually invokes the tools.** The verbs live as HTTP endpoints on the
> bridge (`:8769`). The `nav-base` skill ships `SKILL.md` (hooks + verb docs); to have
> the LLM call the verbs as first-class tools, register them via a skill
> `manifest.json` (MCP `url`/tools), the same pattern the arm skills use — see
> `octos-dora-bridge/manual_skill.md` and `octos/docs/app-skill-dev-guide-zh.md`. For
> scripted/operator use, the §5 HTTP calls work directly with no manifest.

---

## 7. Milestone B — real hardware (dora-nav)

The sim's only fakes are `fake_localization` and `fake_planner`. To go live, replace
those two nodes in a copy of `nav-base-bridge.yaml` with **dora-nav's real
localization/planning/control nodes**, keeping the same topic names so this node's
wiring is unchanged:

| nav_base input | comes from (dora-nav) |
|---|---|
| `dora_nav_pose` | localization node's pose output |
| `dora_nav_status` | planner's nav-status output |
| `dora_nav_obstacles` | perception/obstacle output |

| nav_base output | goes to (dora-nav) |
|---|---|
| `dora_nav_goal` | planner goal input |
| `dora_nav_cancel` | planner cancel input |
| `dora_nav_cmd_vel` | base controller velocity input |

Then set the node's env for real operation (in the dataflow YAML):

- `MAP_PATH=/path/to/map` — **required on real hardware** (drop `NAV_FAKE_MAP`).
- `WAYPOINTS_PATH=load_path.yml` — YAML of named poses for `go_to_named`.
- `HEARTBEAT_TIMEOUT_MS=1000` — operator/LLM must send heartbeats; the bridge does
  **not** yet pulse them automatically for non-zero timeouts.

Build/run dora-nav per its own README (mapping → path file → localization → tracking).
Bring up the combined dataflow exactly as in §5 (`dora up` / `dora start … --attach`),
verify `/healthz`, then drive via octos or curl.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `message format vX not compatible with vY` at startup | CLI vs Python `dora-rs` minor mismatch. Pin **both** to 0.2.6 (§2, §4). |
| `unknown variant 'socket_addr'` / `no variant of enum NodeKind` | Same version mismatch, or a non-0.2.x CLI. |
| `RuntimeError: Already borrowed` | You're on dora **0.3.x** — unsupported. Drop to 0.2.6. |
| `venv` python not found / wrong site-packages | The venv must be at `octos-dora-bridge/bridge/.venv` (the `venv-python` wrapper hard-codes that path). |
| `/healthz` never comes up | Read the dataflow log; check the bridge node didn't crash. Ensure port 8769 is free. |
| `BRIDGE_TIMEOUT` on a call | No `cmd_response` in 30 s — long planning. Raise `CMD_TIMEOUT_S` on the bridge node. |
| `VENDOR_ERROR` | dora-nav reported no path / blocked / localization lost — surface `msg`, replan. |
| `CONTROLLER_BUSY` | Another caller holds the motion slot — `robot.release_control`, then retry. |
| octos `init` hook fails | `/opt/octos-dora-bridge` path mismatch — symlink or edit `SKILL.md` (§6). |

---

## Quick reference

```bash
# one-time
git clone https://github.com/dorarobotics/octos-dora-bridge.git
git clone https://github.com/dorarobotics/nav-base-dora-node.git
cd octos-dora-bridge/bridge && python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,robots.nav-base]"
cargo install dora-cli --locked --version 0.2.6

# every run (sim)
cd octos-dora-bridge && dora up && dora start dataflows/nav-base-bridge.yaml --attach
curl -fsS http://127.0.0.1:8769/healthz
```

Canonical SPEC/verb reference: `octos-dora-bridge/skills/nav-base/SKILL.md`.
This node's own quick start and architecture: `README.md`.
