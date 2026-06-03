# nav-base-dora-node

Mobile-base navigation adapter conforming to `SPEC-VENDOR-NODE-V1`. Wires
[dora-nav](https://github.com/bobdingAI/dora-nav)'s navigation stack (mapping,
localization, planning, control) to the SPEC envelope so octos can call:
`base.go_to_pose`, `base.go_to_named`, `base.set_velocity`, `base.stop`,
`localization.get_pose`, `map.get_obstacles`.

## Architecture

Unlike a library-style vendor (e.g. moveit-arm-dora-node wrapping dora-moveit2),
this repo provides the SPEC endpoint as a single dora node that **co-runs** with
dora-nav's existing nodes in a shared dataflow. Topic-level integration; no
Python import of dora-nav.

## Quick start

```bash
pip install -e .
dora up
dora start examples/dataflow-standalone.yml
```

## License

Apache-2.0 — see LICENSE.
