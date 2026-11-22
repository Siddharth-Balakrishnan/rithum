# Security Policy

## 1. Security scope

Rithum is a physical robot with network-accessible control surfaces planned. A compromise of the control service can cause physical movement. Treat movement authorization and credential handling as safety-sensitive.

## 2. Credentials and secrets

Never commit:
- SSH private keys;
- GitHub tokens;
- Alexa skill secrets;
- API keys;
- passwords;
- session cookies;
- private certificates;
- `.env` files containing secrets;
- database files containing personal/session data.

The `.gitignore` should exclude local secrets and runtime data. Verify with `git status --ignored --short` and review staged changes before committing.

If a secret is committed:
1. revoke/rotate it immediately;
2. remove it from current code;
3. assess whether Git history must be rewritten;
4. do not assume deleting the latest file invalidates the exposed credential.

## 3. Network exposure

- Development bind address should remain `127.0.0.1` unless remote access is deliberately configured.
- Do not expose unauthenticated movement endpoints.
- Require application authentication and authorization even when using Tailscale or a protected tunnel.
- Separate read-only observer permissions from operator permissions.
- Use a single operator lease for movement authority.
- Verify Alexa Skill requests independently.
- Do not expose GPIO devices or Unix sockets directly to untrusted users.

## 4. Command validation

The server must validate:
- command type;
- numeric range;
- operating state;
- active operator lease;
- command freshness;
- heartbeat;
- safety interlocks.

Never trust the browser to enforce speed limits, mode restrictions, or emergency-stop behavior.

## 5. Reporting a vulnerability

Do not publish working exploit details or credentials in a public issue. Contact the repository maintainer privately through an account channel associated with the GitHub repository. Include affected commit/version, impact, reproduction steps, and a suggested mitigation where possible.

## 6. Physical safety

A software security control is not a substitute for a physical emergency stop and motor power isolation.
