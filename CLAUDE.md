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

## Linear
Project: **stock-report-agent** (ID: `391e64ce-8921-4dfd-bb29-7e645efb7503`)
When creating any ticket for this repo, always pass `project: "stock-report-agent"`.

## Wiki type: code

---
<!-- common-rules: v1, 2026-06-07 -->
## Common Rules (auto-synced from Archive/CLAUDE.md)

### Response style
- Korean input → Korean response, English → English. Match the user's language.
- Concise by default. Go deep only when asked.
- Surface tradeoffs. Don't silently pick an interpretation.

### Branch strategy
- **Non-code changes** (docs, HANDOFF, SESSION_LOG, wiki, config) → commit directly to main, no PR needed.
- **Code changes** → always use a feature branch.
  - **Before writing the first line of code**: run `git branch`. If on main, STOP — create a feature branch (name = Linear sub-issue ID, e.g. `YEO-17`) and open a Draft PR. Never commit code to main.
  - `/eod` pushes to the existing branch — it does NOT create a new branch.

### After merging a PR
- **Never commit to a merged branch.** Merged = closed. For more changes → new sub-issue + new branch.

### GitHub push rule
- Always confirm with the user before pushing to GitHub.
- After opening a PR, immediately attach the PR URL to the Linear issue via `save_issue` `links` field.

### Linear ticket ↔ PR structure
- Feature ticket (parent) = planning unit. Sub-issue (child) = one branch + one PR.
- Branch name = sub-issue ID. Feature ticket is Done only when all sub-issues are closed.
- Always set `project` field when creating tickets.

### PR splitting (before writing any code)
- Each PR must be reviewable in under 60 min (single concern).
- API + UI change = minimum 2 PRs. Show breakdown to user before creating branches.

### PR Gate — mandatory before every `gh pr create` (Draft PRs included, no exceptions)
1. `git diff main...<branch>` — review the diff
2. **Run `/security-review` — wait for completion. Fix HIGH/MEDIUM findings. Document in PR body under `## Security review`.**
3. Run `code-reviewer` agent — fix flagged issues.
4. Only then run `gh pr create`.
GitHub Actions is not a substitute. No skipping.

### Proactive /qa suggestion
When user signals feature complete ("이제 됐다", "다 됐어", "기능 완성", "다음으로 넘어가자", "됐고"):
> "[feature name]이 완성된 것 같네요. PRD에 done 마킹 전에 /qa 돌릴까요?"
Only at feature completion — not after every PR merge.

### /eod order
1. Update HANDOFF.md
2. Append to SESSION_LOG.md
3. Update this project's row in `~/Desktop/Archive/my-second-brain/HUB.md`
4. Run wiki-updater agent (type from `## Wiki type:` above)
5. Propose Linear issue status updates
6. Git commit + push (project repo + my-second-brain)
7. Sync any changed config files to my-second-brain/docs/setup-exports/

