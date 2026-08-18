# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report them privately via GitHub's
[Security Advisory](https://github.com/finn-liam/knowledge-research-agent/security/advisories/new)
page (repository **Security** tab → **Report a vulnerability**).

We aim to acknowledge reports within 48 hours and publish a fix for confirmed
issues as soon as possible. Once a fix is released, we will credit the reporter
(unless you prefer to remain anonymous).

## API Keys

- The project never stores API keys in source code. All secrets are read from
  `apps/api/.env` at runtime (see `apps/api/.env.example`), and `.env` is
  git-ignored.
- Never commit real keys; CI and the public demo run in Mock mode without keys.
- Rotate a key immediately if you suspect it has been committed or exposed.

## Dependencies

- Python and Node dependencies are declared in
  `apps/api/requirements*.txt` and `apps/web/package*.json`.
- Report vulnerable or outdated dependencies through the channel above, or
  open a normal issue labelled `dependencies`.

## Model & Runtime Notes

- Local models (`bge-m3`, `bge-reranker-v2-m3`) are downloaded at setup time
  into `models/` (git-ignored) and are not shipped with the repository.
- `infra/docker-compose.yml` uses default development credentials
  (`kra_secret`) for local containers only; change them before any
  non-local deployment.
