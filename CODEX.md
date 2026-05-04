# CODEX.md

Working rules for this repository:

1. Commit incrementally.
   - Make small, coherent commits as work progresses instead of batching unrelated changes together.
   - Prefer one commit per logical change area.

2. Push after completing the intended change.
   - After the relevant commit is ready, push it to `origin/master` so GitHub Pages can rebuild from the latest code.

3. Verify deployment for frontend changes.
   - If a change affects the frontend or deployment, confirm the GitHub Pages workflow completes successfully.
   - Confirm the live site serves the updated bundle or behavior, not just the local build.

4. Do not mix unrelated work into the same commit.
   - If the worktree contains unrelated crawler, fixture, or generated-data changes, leave them out unless explicitly requested.

5. Prefer backend as source of truth for synced user data.
   - Test completion state, result views, and progress views should read from backend APIs when available.
   - localStorage may be used only for passcode storage or temporary submit-time cache unless explicitly intended otherwise.
