# Contributing to Rithum

## 1. Before changing code

- Read `README.md`.
- Read the subsystem document relevant to the change.
- Check the current implementation rather than assuming the roadmap is implemented.
- Check `git status` and pull the latest `main`.

## 2. Branches and commits

Use a focused branch for non-trivial work:

```bash
git switch -c feature/short-description
```

Suggested commit prefixes:

- `feat:` new behavior;
- `fix:` bug fix;
- `test:` test-only changes;
- `docs:` documentation;
- `refactor:` behavior-preserving restructuring;
- `chore:` tooling/configuration maintenance.

Keep commits small enough to review.

## 3. Required checks

Before committing:

```bash
python -m unittest discover -s tests -v
git diff --check
git status --short
git diff
```

Review staged files before committing:

```bash
git add <specific-paths>
git diff --cached
```

## 4. Tests

Every behavior change should include tests. Safety-related behavior needs both allowed-path and rejected-path tests.

Unit tests must not:
- energize motors;
- depend on live GPIO;
- require a camera or IR sensor;
- contact an external service unless the test is explicitly an integration test.

## 5. Documentation

Update documentation when changing:
- state names or transitions;
- environment variables or defaults;
- hardware models, wiring, or pin assignments;
- safety behavior;
- network/API behavior;
- phase acceptance criteria;
- installation or troubleshooting steps.

Keep the README documentation index synchronized.

## 6. Safety-sensitive changes

Changes to motion, motor output, GPIO, E-stop, heartbeat, obstacle response, authentication, or autonomy require explicit safety review.

Do not:
- bypass the supervisor;
- expose raw GPIO to web clients;
- remove motor-disabled-at-boot behavior;
- allow autonomous mode before its phase gate;
- clear E-stop/fault latches without trusted confirmation;
- treat a sensor communication failure as a clear path.

## 7. Pull request description

Include:
- purpose and scope;
- files/subsystems changed;
- implementation vs. planned status;
- tests run and results;
- hardware tested (if any);
- safety implications;
- remaining limitations.
