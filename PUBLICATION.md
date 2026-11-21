# Source publication

Publish from the release owner's isolated checkout of the existing brain_work repository. The local research checkout contains deployment state and unrelated work. The source history began with a sanitized snapshot and carries its own reviewed commits. [Project repository](https://github.com/victor000000/brain_work)

## Prepare a candidate

Use the existing release branch and agree on one publisher. Contributors give that owner their proposed patches and test results. The package version lives in `pyproject.toml`. Include version changes once in the release candidate.

Keep credentials, live databases and WALs, logs, receipts, account or API captures, email/forum archives, private research, caches, binary distributions and local test reports outside the commit. Stage the intended source, tests and public guides by path. Inspect `git status --short`, `git diff --cached --name-status`, `git diff --cached --check` and the staged diff itself before committing. The ignore file helps with untracked files. Review the contents of modified tracked files too.

After committing, identify the candidate and the current destination. Keep these variables in the same shell through verification.

```bash
git fetch origin main
candidate=$(git rev-parse HEAD)
candidate_tree=$(git rev-parse "${candidate}^{tree}")
remote_main=$(git rev-parse FETCH_HEAD)
remote_tree=$(git rev-parse "${remote_main}^{tree}")
git status --short
```

If `test "$remote_tree" = "$candidate_tree"` succeeds, the source is already on main, even when GitHub gave the commit a different SHA. Use `remote_main` for hosted verification. If main advanced after an earlier push, use the branch history or the merged pull request to locate the integrated commit and its workflow. Reuse that publication.

For an unpublished candidate, check that the fetched main is its ancestor and review the committed delta.

```bash
git merge-base --is-ancestor "$remote_main" "$candidate"
git diff --name-status "$remote_main" "$candidate"
git diff --check "$remote_main" "$candidate"
```

Continue with a clean working tree and a successful ancestry check. If main has advanced on a different line, integrate its changes and verify the resulting candidate. Run the complete gate and the optimized parser build from [Development](docs/DEVELOPMENT.md#reproduce-ci). Keep the results with the candidate SHA locally.

## Publish once and verify GitHub

The release owner checks for an existing push or open pull request for that candidate. If it is already on the destination, proceed to hosted verification. If a pull request is open, continue in that pull request. Set `release_ref` to the agreed branch’s full ref. For a release review branch, use its `refs/heads/codex/...` ref. Publish the verified commit by SHA.

```bash
git push origin "${candidate}:${release_ref}"
git fetch origin "${release_ref}"
published=$(git rev-parse FETCH_HEAD)
test "$published" = "$candidate"
test "$(git rev-parse "${published}^{tree}")" = "$candidate_tree"
```

If a push disconnects before confirming success, fetch the destination and check its SHA before retrying. With a pull request or an API-created commit, identify the actual commit integrated on `main` and compare its tree with `candidate_tree`. If the tip has advanced again, inspect the branch history for the published commit. A non-fast-forward rejection calls for integrating the new head and rerunning validation.

Open **Offline validation** for the published SHA on GitHub and record its terminal result. If a check fails, reproduce that step using the same candidate and pinned dependencies. For a correction to a published commit, use a reviewed forward fix or revert and validate it through the same workflow. [GitHub Actions](https://github.com/victor000000/brain_work/actions) · [Workflow definition](.github/workflows/ci.yml)

The workflow validates source. Deployment, restoring private data or credentials, and starting the service belong to the deployment owner in a separately authorized window. [Setup](docs/SETUP.md) · [Recovery procedure](docs/OPERATIONS.md#recover-an-interrupted-run)
