# Rithum — Antigravity Instructions

The shared repository engineering contract is `AGENTS.md`. Read and obey it before every task. This file adds Antigravity-specific workflow requirements.

## First-session procedure
1. Run `pwd`, `git status --short`, and `git log -5 --oneline`.
2. Read `AGENTS.md`.
3. Read `README.md` and the relevant files under `docs/`.
4. Inspect existing code before proposing or applying replacements.
5. Confirm the Python environment and test command.
6. Summarize findings, intended files, risks, assumptions, and test plan before editing.

Do not assume prior ChatGPT conversation history is available. Repository code and checked-in documentation are the source of truth. If repository reality conflicts with `AGENTS.md`, report the discrepancy and ask; do not guess.

## Permissions and execution boundaries
- Run as the non-root Linux account `r1t-hum`.
- If current shell is root, stop before editing and ask the owner to relaunch Antigravity as `r1t-hum`.
- Never use sudo automatically.
- Do not install packages, modify system services, permissions outside the repository, boot/network/firewall configuration, or persistent system data without explicit approval.
- Do not connect to or energize motors, access physical GPIO, or enable autonomy without explicit approval.
- Do not run destructive commands (`rm -rf`, `git reset --hard`, forced checkout, history rewriting, etc.).
- Never overwrite uncommitted user work.

## Scope discipline
- Implement only the explicitly assigned milestone.
- The next expected milestone is `core/supervisor.py`, unless the owner says otherwise.
- Do not implement future phases pre-emptively.
- Autonomous movement and IR obstacle avoidance are forbidden until Phase 6 is completed, verified, and the owner approves the next phase.
- Do not introduce Docker, another MCU, React, a local LLM, or heavyweight GUI frameworks without approval.
- Prefer existing dependencies and patterns; justify any new dependency.

## Implementation quality
- Preserve existing architecture and public interfaces unless a change is justified.
- Use type hints and narrow interfaces.
- Keep hardware access behind injectable abstractions.
- Do not initialize GPIO or open devices at import time.
- Validate IPC envelopes, action names, payload schemas, peer identity, and authorization at the correct boundary.
- Never treat claimed IPC `source` as authentication.
- Use monotonic clocks for timeouts and leases.
- Fail safely on disconnect, timeout, worker crash, malformed messages, and shutdown.
- Do not silently swallow exceptions or claim success before it occurs.
- Do not weaken production checks to satisfy tests.
- Add normal-path, invalid-input, authorization-failure, and cleanup/failure tests.

## Required workflow
Before changes:
- State what the repository currently contains.
- Give a short implementation plan and test plan.
- Identify safety-relevant assumptions needing owner confirmation.
- Do not ask for information already documented.

During changes:
- Make small, reviewable edits.
- Avoid unrelated refactoring and formatting churn.
- Run focused tests after meaningful changes.
- Stop and ask if a safety-relevant design decision is ambiguous.

After changes, run:
```bash
pytest -v -ra --tb=short
git diff --check
git status --short
git diff --stat
```
Inspect the diff for unintended changes. Do not commit or push unless explicitly requested.

Report:
1. Implementation summary.
2. Files created/modified.
3. Exact tests run and results.
4. Safety/security implications.
5. Known limitations and remaining work.
6. Whether physical hardware validation remains necessary.

Then stop and wait for owner review. Do not start another milestone automatically.

## Supervisor milestone requirements
When assigned `core/supervisor.py`:
- Read `core/config.py`, `core/state_manager.py`, and every `core/ipc/` module.
- Read `docs/IPC_PROTOCOL.md`, `docs/ARCHITECTURE.md`, `docs/SAFETY.md`, and `docs/STATE_MACHINE.md` if present.
- Propose a testable supervisor API before implementation.
- Supervisor owns worker lifecycle, state transitions, IPC dispatch, command authorization, and safety coordination.
- It must not contain low-level motor GPIO code.
- Motors disabled and autonomy disabled at startup.
- Reject motion unless state, operator lease, dead-man heartbeat, hardware readiness, and applicable interlocks permit it.
- E-stop and faults override ordinary commands.
- Shutdown and worker failure must lead to safe stopped state.
- Keep implementation hardware-independent and mockable.
- Explicitly address or document unresolved IPC concerns: per-connection sequence reset, process-session replay protection, peer-to-component authentication, and connection-handler cleanup.
- Passing unit tests alone does not establish production readiness.

## Context efficiency
- Read relevant files without repeatedly dumping entire repository contents.
- Prefer focused diffs and concise test output.
- Do not regenerate whole documents for small corrections.
- End each task with a concise handoff summary that a fresh agent session can use.
