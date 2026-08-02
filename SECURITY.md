# Security Policy

## Supported versions

Security fixes land on the latest minor release and on `develop`. Older minor
versions do not receive backported patches.

| Version | Supported |
| --- | --- |
| 0.6.x | Yes |
| < 0.6 | No |

## Reporting a vulnerability

Report privately. Do not open a public issue for a security problem.

Use [GitHub private vulnerability reporting](https://github.com/Extralit/extralit/security/advisories/new),
or email **contact@extralit.ai** if you would rather not use GitHub.

Include what you have: affected version or commit, reproduction steps, and the
impact you believe it has. A partial report is more useful than no report.

## What to expect

- **Acknowledgement within 5 business days.** If you do not hear back, email
  contact@extralit.ai directly.
- **An assessment within 15 business days**, saying whether we consider it a
  vulnerability and what severity we assign.
- **Fix and disclosure coordinated with you.** We will credit you in the advisory
  unless you ask us not to.

Extralit is maintained by a small team. These are the timelines we hold
ourselves to, not a commercial SLA.

## Scope

In scope: the Extralit server, Python SDK, frontend, and the Hugging Face Spaces
deployment bundle in this repository.

Out of scope: vulnerabilities in upstream dependencies with no Extralit-specific
exploit path (report those upstream), and findings against third-party instances
of Extralit that you do not own or have permission to test.

## Deploying Extralit safely

Extralit is self-hosted software that handles document data and user
credentials. The default `docker-compose.yaml` is for local development, not
production: change the default credentials, terminate TLS in front of the
server, and do not expose Elasticsearch, PostgreSQL, or Redis to untrusted
networks.
