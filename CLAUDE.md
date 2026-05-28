# stock-report-agent — Claude Instructions

## Session start
At the start of every session, read HANDOFF.md before doing anything else.
After reading, briefly confirm: state the project name, last session date, and what's next (1-2 lines max).

## PRD
Location: docs/PRD.md (not yet created — create before next implementation session)
Last reviewed: —

## Stack
Python, GitHub Actions (daily cron). Key modules: collectors/, composer.py, emailer.py, pdf_generator.py, main.py. Dependencies in requirements.txt.

## QA Criteria
- [ ] GitHub Actions workflow completes without errors
- [ ] PDF is generated and attached correctly
- [ ] Email is delivered to recipient

## Project rules
- No feature without a PRD entry first.

## Known issues / Do not repeat
- Node.js 24 env var syntax differs — check before modifying workflow YAML
- Errors must surface in step annotations, not silently swallowed
