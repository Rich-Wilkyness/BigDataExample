# Git and CI/CD for Data Engineers

> Status: Guided introduction
>
> Level: Beginner, with production context
>
> Applies to: Python, SQL, data pipelines, infrastructure, and documentation
>
> Practice: [Tuesday homework](./2.2_Tue_HW.md)
>
> Last reviewed: 2026-09

## Overview

Git records and coordinates changes to code and configuration. CI/CD turns those recorded changes into repeatable evidence and deployable artifacts.

For a data engineer, this is not just about saving Python files. A change can alter a table schema, historical backfill, scheduler configuration, access policy, or dataset consumed by other teams. Git helps reviewers understand exactly what changed; CI checks whether the change satisfies known requirements; delivery and deployment controls determine whether that change should reach an environment.

This guide focuses on the Git and CI/CD knowledge needed for day-to-day data-engineering work. It does not attempt to cover every Git command or build a complete production deployment platform.

## Learning objectives

After completing this guide, you should be able to:

- Explain the working tree, staging area, commit history, branch, and remote.
- Make a small change on a branch and submit it for review.
- Inspect changes before committing, recover from common mistakes, and resolve a basic merge conflict.
- Explain continuous integration, continuous delivery, and continuous deployment without treating them as the same thing.
- Trace the provided GitHub Actions workflow from source commit to tested container image.
- Identify which pipeline layer failed and what evidence to inspect.
- Explain why deploying old code does not necessarily reverse data already written by a pipeline.

## What you need at each stage

| Stage | Git and CI/CD knowledge |
| --- | --- |
| Beginner | Clone or initialize a repository, inspect changes, commit, pull, push, use a branch, and read a CI failure. |
| Working data engineer | Use pull requests, resolve conflicts, protect secrets and data, write tests, understand pipeline triggers and artifacts, and make backward-compatible changes. |
| Senior data engineer | Design release gates, environment promotion, rollback and forward-repair plans, supply-chain controls, observability, and safe schema/backfill deployments. |

You do not need to memorize every command. You do need a reliable mental model and the habit of inspecting state before changing it.

## Part 1: Git

### Git, GitHub, and other hosting platforms

**Git** is the version-control system installed on your computer. **GitHub, GitLab, Bitbucket, Azure DevOps, and similar products** host Git repositories and add collaboration features such as pull requests, permissions, issue tracking, and CI/CD runners.

Git can work without GitHub, and GitHub is not a replacement for Git. In a restricted network, an organization may host Git and CI/CD services internally.

### The Git mental model

```text
working tree          staging area             local history              remote
files you edit   ->   selected next change ->  commits on a branch   ->   shared repository
                   git add                   git commit                git push
```

| Term | Meaning |
| --- | --- |
| Repository | A project plus its Git history and metadata. |
| Working tree | The files currently checked out in your folder. |
| Staging area, or index | The exact changes selected for the next commit. |
| Commit | An identified snapshot with a parent, author, time, and message. |
| Branch | A movable name pointing to a sequence of commits. |
| `HEAD` | The commit or branch currently checked out. |
| Remote | A saved name for another repository, usually `origin`. |
| Pull request | A hosting-platform review of proposed commits before merging. Git itself does not create pull requests. |

The staging area is why `git add` matters: it lets you commit one coherent change even when your working tree contains other unfinished edits.

### Create or obtain a repository

Use `clone` when the remote repository already exists:

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

Use `init` only when starting version control in an existing local directory:

```bash
mkdir example-project
cd example-project
git init
```

If that local repository later needs a remote:

```bash
git remote add origin https://github.com/OWNER/REPOSITORY.git
git remote -v
```

Do not run `git init` inside a repository that you already cloned.

### Inspect before you change history

These are the most useful Git commands because they answer what state you are in:

```bash
git status
git diff
git diff --staged
git log --oneline --decorate --graph -10
git branch --show-current
git remote -v
```

| Command | Question it answers |
| --- | --- |
| `git status` | Which branch am I on, and which files are untracked, modified, or staged? |
| `git diff` | What unstaged lines have I changed? |
| `git diff --staged` | What exactly will the next commit contain? |
| `git log ...` | Which recent commits and branches led here? |

### A safe daily branch workflow

Start from an up-to-date `main`, create a small branch, inspect the work, and push the branch:

```bash
git switch main
git pull --ff-only
git switch -c feature/add-quality-check

# Edit files and run relevant tests.

git status
git diff
git add path/to/file.py path/to/test_file.py
git diff --staged
git commit -m "Add order quality check"
git push -u origin feature/add-quality-check
```

Then open a pull request, let CI run, address review comments, and merge only after the required checks pass.

Why these details matter:

- `git switch -c` creates and switches to a new branch. It is clearer for branch work than the older multi-purpose `git checkout` command.
- `git pull --ff-only` refuses to create an unexpected merge commit while updating your local branch.
- Explicit paths in `git add` reduce the chance of including credentials, generated files, or unrelated edits.
- `git push -u` records the upstream branch, so later `git push` and `git pull` know the default destination.
- A focused commit is easier to review, test, revert, and diagnose than a mixture of unrelated work.

### Fetch, pull, and push

```text
git fetch = download remote commits and branch information; do not change working files
git pull  = fetch, then integrate the remote branch into the current branch
git push  = upload local commits to a remote branch
```

Use `git fetch` when you want to inspect remote changes before integrating them. Never assume `pull` means “download only.”

### Branching and pull requests

A practical default for a small team is:

```text
main: protected and expected to pass required checks
  └── short-lived feature/fix branch
        └── pull request -> review + CI -> merge
```

Long-lived personal branches accumulate conflicts and hide work. Prefer small branches and pull requests that represent one reviewable change. More elaborate strategies such as Git Flow can be useful for certain release models, but they are not automatically better.

A pull request should help a reviewer answer:

- What behavior or contract changes?
- Which data, tables, jobs, or consumers are affected?
- How was the change tested?
- Is the change backward compatible with running jobs and existing data?
- What is the deployment, rollback, or forward-repair plan?

### Merge conflicts

A conflict means Git cannot safely decide how to combine overlapping changes. It is not an indication that Git is broken.

```bash
git status
```

Open each conflicted file and find `<<<<<<< HEAD`, `=======`, and `>>>>>>> other-branch` surrounding the two versions Git could not combine.

Choose or combine the correct content, remove all markers, rerun relevant tests, and then stage the resolution:

```bash
git add path/to/resolved_file.py
git status
git commit
```

Resolve the meaning of the code, schema, or configuration—not merely the conflict markers. A syntactically clean merge can still produce an incorrect pipeline.

### Recover from common mistakes

Inspect `git status` and `git diff` before using an undo command.

| Situation | Safer command | Effect |
| --- | --- | --- |
| Staged the wrong file | `git restore --staged path/to/file` | Removes it from the staging area but keeps the working change. |
| Want to discard an uncommitted file change | `git restore path/to/file` | Replaces the working copy with the committed version; the discarded change is difficult to recover. |
| Need to undo a shared commit | `git revert COMMIT` | Adds a new commit that reverses the selected commit. |
| Need to temporarily set aside work | `git stash push -m "description"` | Stores tracked changes for later application. |
| Need to recover an apparently lost commit | `git reflog` | Shows recent movements of local references. |

Avoid copying destructive commands such as `git reset --hard` or force-pushing a shared branch without understanding exactly which commits and uncommitted changes will be discarded.

### Worktrees: two working environments from one repository

A Git worktree gives another branch its own directory while sharing the repository’s Git history:

```bash
git worktree add ../BigDataExample-experiment -b experiment/new-pipeline
git worktree list
```

This is useful when a long-running test or notebook must remain untouched while you fix something on another branch. Each worktree has separate checked-out files, but Git normally prevents the same branch from being checked out in two worktrees.

A worktree separates code; it does not automatically separate dependencies or services. Give each Python worktree its own `.venv`, and use separate container or service names and ports when both environments run simultaneously.

When finished:

```bash
git worktree remove ../BigDataExample-experiment
git worktree prune
```

### Repository hygiene for data engineering

Commit durable, reviewable inputs to the engineering process:

- Python and SQL source code.
- Tests and small deterministic test fixtures.
- Schema definitions, migrations, and data contracts.
- Workflow, container, and infrastructure configuration.
- Dependency and lock files.
- Documentation and runbooks.

Do not commit:

- Passwords, API keys, private keys, access tokens, or populated `.env` files.
- Production data or personally identifiable information.
- Large raw datasets, warehouse exports, database files, or model artifacts unless the repository has an explicit storage policy for them.
- Virtual environments, caches, logs, or generated build output.

A `.gitignore` prevents new untracked files from being added accidentally; it does not remove a file already committed. If a secret is committed, removing the file is not enough: revoke or rotate the credential and follow the organization’s incident procedure.

Example Python and local-data exclusions:

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
.env
data/raw/
dist/
```

Keep small fake fixtures in an intentional tracked path rather than ignoring every file named `data`.

## Part 2: CI/CD

### CI, continuous delivery, and continuous deployment

| Practice | Meaning |
| --- | --- |
| Continuous integration (CI) | Frequently integrate small changes and automatically validate them. |
| Continuous delivery | Keep a tested, versioned artifact ready for deployment; a human approval may still release it. |
| Continuous deployment | Automatically deploy every qualifying change after all gates pass. |

“CD” is ambiguous unless the team says whether it means delivery or deployment.

The Tuesday homework performs automated tests, builds an image, and publishes it to GitHub Container Registry. Pulling and running that image locally is a manual deployment. The exercise therefore demonstrates CI and part of continuous delivery; it does not create fully automated production deployment.

### The delivery mental model

```text
edit -> local checks -> commit -> push/pull request -> CI evidence
                                                     |
                                                     v
source commit -> build once -> versioned artifact -> registry
                                                     |
                                                     v
                                   approve/promote -> deploy -> verify
                                                              |
                                                        rollback or repair
```

The artifact should be traceable to one source commit. Mature pipelines build it once and promote the same immutable artifact through environments instead of rebuilding different bytes for test and production.

### Why CI/CD matters to data engineers

CI can check more than whether Python imports successfully:

- Unit tests for transformation logic.
- SQL syntax and model tests.
- Schema and data-contract compatibility.
- Data-quality rules using small deterministic fixtures.
- DAG or workflow parsing.
- Integration tests against a real database, object store, broker, or processing engine.
- Container and package builds.
- Dependency, secret, and vulnerability scans.
- Infrastructure-plan validation.

CD for a data pipeline must consider persistent effects. Rolling back code does not automatically remove duplicate rows, restore overwritten partitions, reverse a schema migration, or undo messages already published. A safe release may require backward-compatible schema changes, idempotent writes, staged publication, reconciliation, a compensating operation, or a forward fix.

### Anatomy of a GitHub Actions workflow

GitHub Actions reads YAML files from `.github/workflows/`.

| Element | Purpose |
| --- | --- |
| `name` | Human-readable workflow name. |
| `on` | Events and branch/path filters that trigger the workflow. |
| `permissions` | Access granted to the workflow’s `GITHUB_TOKEN`. |
| `jobs` | Units of work that may run independently or depend on other jobs. |
| `runs-on` | Runner operating system or runner label. |
| `steps` | Ordered actions or shell commands within one job. |
| `uses` | Executes a reusable action. |
| `run` | Executes a shell command. |
| `env` and `secrets` | Non-secret variables and protected secret values. |
| Artifact | Output retained or published by a run, such as a package, report, or container image. |

CI runners are temporary machines. A file created in one job is not automatically available in another job; it must be rebuilt, cached appropriately, or uploaded and downloaded as an artifact.

### Trace the homework pipeline

The workflow in [the homework](./2.2_Tue_HW.md) uses this sequence:

| Step | Input | Evidence or output | Typical failure layer |
| --- | --- | --- | --- |
| Checkout | Source revision | Files available on the runner | Repository or permissions |
| Set up Python | Requested runtime version | Python executable | Runtime/tool setup |
| Install dependencies | `app/requirements.txt` | Installed environment | Dependency resolution or network |
| Run tests | Application plus dependencies | Passing or failing test result | Python behavior, import path, or test |
| Registry login | `GITHUB_TOKEN` | Authenticated Docker client | Token or package permissions |
| Build image | Dockerfile and application | Local container image | Dockerfile, dependency, or application |
| Push image | Built image | Registry package | Registry name, permission, or network |

The workflow grants `contents: read` so it can read the repository and `packages: write` so it can publish the image. The automatically supplied `GITHUB_TOKEN` should receive only the permissions required by its job.

### From homework pipeline to production pipeline

The homework intentionally keeps one job and one `latest` tag so the flow is easy to see. A production pipeline would usually evolve in small steps:

1. Run validation on pull requests before merge, not only after a push to `main`.
2. Separate unprivileged test jobs from the package-publishing job.
3. Pin dependencies and record the runtime used to make builds reproducible.
4. Tag artifacts with an immutable identifier such as the commit SHA or release version; use `latest` only as a convenient movable alias.
5. Grant write permissions only to the job and event that publish artifacts.
6. Add contract, integration, security, and data-quality checks based on actual risks.
7. Use protected environments, approvals, and deployment concurrency controls.
8. Deploy the exact artifact that passed validation, then run health, smoke, and data-reconciliation checks.
9. Record who deployed which artifact to which environment and whether recovery succeeded.

Do not add every possible gate to a small project. Add evidence for real failure risks, keep fast feedback early, and move slower integration or deployment checks to later stages.

### Security boundaries

- Store secrets in the CI/CD platform or a dedicated secret manager, not in Git or workflow YAML.
- Give tokens the minimum permissions and lifetime needed.
- Do not print secrets or sensitive data into logs or test artifacts.
- Treat pull-request code as untrusted, especially when it originates from a fork.
- Review third-party actions and pin them according to organizational policy; a full commit SHA provides stronger immutability than a movable tag.
- Use synthetic or deidentified test data unless an approved environment explicitly supports sensitive data.
- Prefer short-lived identity federation for cloud access over long-lived cloud keys when the platform supports it.

### Failure diagnosis

Start with the first failed step. Later failures may only be consequences.

| Symptom | First evidence to inspect | Likely owner |
| --- | --- | --- |
| Test passes locally but fails in CI | Python version, dependency versions, working directory, case-sensitive paths, environment variables | Application or CI configuration |
| Docker build fails locally and in CI | First failing Dockerfile layer and build context | Dockerfile or application |
| Docker works locally but build fails only in CI | Runner architecture, credentials, network, paths, or missing ignored files | CI environment |
| Registry login or push fails | Registry path, token scope, workflow `permissions`, package access | Identity or registry configuration |
| Deployment starts but data is wrong | Artifact identity, configuration, schema compatibility, input/output counts, quality checks | Release or pipeline behavior |
| Rollback restores code but not data | Writes already committed, messages emitted, migrations applied, or backfill state | Recovery design |

Useful questions are:

1. Which commit triggered this run?
2. Which job and first step failed?
3. Did the same command pass locally in the documented runtime?
4. Was an artifact created, and what immutable version identifies it?
5. Which environment, dataset, and consumers were affected?
6. Is retry safe, or could it duplicate or partially overwrite data?

## Common pitfalls

### “It is committed, so it is on GitHub”

A commit exists locally until it is pushed. Confirm the branch and upstream with `git status` and inspect the remote repository.

### “The CI file proves the pipeline works”

YAML is configuration, not evidence. The workflow must run, and its logs, test results, and artifacts must show what passed.

### “The image was built, so it was deployed”

Building creates an artifact. Publishing stores it in a registry. Deployment changes a running environment. These are separate boundaries and can fail independently.

### “Rerun the failed data job”

A rerun is safe only if the operation is idempotent or has a recovery design. Otherwise it may duplicate output or compound a partial write.

### “Rollback means put the old code back”

That may restore application behavior but cannot automatically reverse persistent data effects. Some incidents require data repair or a forward-compatible fix.

### “Put credentials in the workflow temporarily”

Git history, logs, caches, and artifacts can preserve them. Use the platform’s protected secret mechanism and rotate any exposed credential.

## Knowledge check

1. What is the difference between the working tree, staging area, and a commit?
2. Why should you inspect both `git diff` and `git diff --staged`?
3. What does `git pull` do that `git fetch` does not?
4. How does a worktree differ from a Python virtual environment?
5. Is a workflow that tests and publishes an image but requires a person to deploy it continuous delivery or continuous deployment?
6. Why is a commit-SHA image tag safer for rollback than relying only on `latest`?
7. A pipeline wrote half of a partition before failing. What must you determine before rerunning it?
8. Which parts of the homework prove local behavior, CI behavior, artifact publication, and deployment behavior?

## Key takeaways

- Git is a model of snapshots and references, not just `push` and `pull` commands.
- Inspect state, make small commits on short-lived branches, and use pull requests for review and automated evidence.
- Source code, schemas, workflow definitions, and small fixtures belong in Git; secrets and production data do not.
- CI validates a change, delivery produces a releasable artifact, and deployment changes a running environment.
- Build once, identify the artifact immutably, promote it deliberately, and verify the result.
- Code rollback and data recovery are different problems.
- Diagnose the first failing boundary before changing unrelated files.

## Primary resources

- [Git reference](https://git-scm.com/docs)
- [Git command cheat sheet](https://git-scm.com/cheat-sheet.pdf)
- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Using `GITHUB_TOKEN` in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
- [GitHub Actions secure-use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [Publishing Docker images with GitHub Actions](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)

## Completion checklist

- [ ] I can explain the Git mental model without reciting commands.
- [ ] I can create a branch, inspect changes, make a focused commit, and push it.
- [ ] I can distinguish unstaged changes from staged changes.
- [ ] I can resolve a basic conflict and rerun the relevant checks.
- [ ] I can explain what belongs in a data-engineering repository and what must stay out.
- [ ] I can distinguish CI, continuous delivery, and continuous deployment.
- [ ] I can trace every step in the homework workflow and identify its permissions.
- [ ] I can explain why a data deployment may require reconciliation or repair in addition to code rollback.
- [ ] I completed the homework and recorded the requested evidence.
