---
name: github-repo-setup
description: >-
  Automates the workflow of creating a public repository on GitHub, initializing or pulling it to a local folder, creating a comprehensive .gitignore file, making an initial commit, and pushing.
---

# GitHub Repo Setup Skill

## Overview
This skill automates the process of setting up a new git project integrated with GitHub. It handles the API call to create a repository, sets up local Git tracking, auto-generates a standard `.gitignore` file, and executes the initial commit and push.

## Dependencies
None. This skill uses Python's standard library and the local Git CLI client.

## Quick Start
To set up a repository, run the Python utility script:

```bash
python E:\ProgrameSpace\VibeCodingSpace\Personal-Skills-Scripts\github-repo-setup\setup_repo.py --token <GITHUB_PAT> --repo-name <REPO_NAME> --local-path <LOCAL_PATH>
```

## Utility Scripts
The skill provides a Python automation script `setup_repo.py`:

```bash
python setup_repo.py --token <token> --repo-name <name> --local-path <path> [--description <desc>]
```

### Arguments:
* `--token`: (Required) Your GitHub Personal Access Token (PAT).
* `--repo-name`: (Required) The name of the repository to create on GitHub.
* `--local-path`: (Required) The path to the local directory where the code is located or should be cloned.
* `--description`: (Optional) Description of the repository. Defaults to "Created via setup_repo.py".

## Rate Limiting
This script makes direct calls to the GitHub API. It handles rate limit errors gracefully and logs them to stderr. Since it is intended for project setup workflows, rate limit exhaustion is highly unlikely (GitHub allows 5,000 requests per hour for authenticated accounts).

## Common Mistakes
1. **Invalid Token Scope**: The provided Token must have permission to create repositories (either `repo` scope for classic tokens, or **Repository creation: Read & Write** under Account Permissions for fine-grained tokens).
2. **Untracked Secret Files**: The default `.gitignore` ignores common Python environment files like `.env` and `.venv`. Ensure you do not add secret tokens directly to any versioned source code.
