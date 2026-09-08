# Claude Code Instructions

Read `AGENTS.md` first. Then inspect the relevant `config/`, `knowledge/`, `skills/`, `schemas/`, and `workflows/` files before changing behavior.

Never publish directly to production. WordPress status must remain `draft` unless an explicit human-controlled workflow enables publishing.

Prefer deterministic validation for schemas, HTML, links, filenames, and credentials. Do not overwrite knowledge or production configuration without explicit instruction.
