# Contributing to Asteria Command Station

Contributions, experiments, and questions are welcome. Asteria is a student robotics project, but it is also meant to be useful as a reference for agent-assisted robotics, finite state machines, safer teleop, and educational tooling.

Good contribution areas include:

- FSM examples that are easy to read, teach from, and run safely.
- GUI improvements for operator clarity, debugging, and accessibility.
- Agent workflow improvements around prompts, notes, leases, and reproducible actions.
- Documentation that helps new robotics or AI-agent learners understand the system.
- Bug reports with clear setup notes, screenshots, logs, or reproduction steps.

Please keep changes practical and reviewable:

- Keep generated files, private tokens, local robot logs, virtual environments, and personal runtime artifacts out of Git.
- Default to local-only networking unless a trusted-LAN use case is explicit.
- Preserve the daemon-centered safety model: command leases, stop behavior, and operator visibility matter.
- Prefer focused pull requests over broad rewrites.
- For live robot changes, describe what was tested disconnected and what still needs hardware verification.

This repository pairs with Asteria DS: https://github.com/RedLynx101/asteria-ds
