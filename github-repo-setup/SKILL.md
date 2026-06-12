---
name: github-repo-setup
description: >-
  Automates the process of creating a remote GitHub repository, initializing a local Git repo, adding a standard .gitignore file, and pushing local code to remote.
---

# GitHub Repo Setup

## Overview
This skill automates the workflow of creating a new GitHub repository, creating a README file to prevent Unicode/encoding issues, setting up a comprehensive `.gitignore`, initializing (or cloning into) a local code directory, and finally pushing all local code to the remote repository.

## Quick Start
Provide the repository name, description, and the local path to the agent:
"Please use github-repo-setup to create a repository called 'My-New-Project' with the description 'A sample project' and sync it with the local code at 'E:\ProgrameSpace\MyProject'."

## Utility Scripts
The skill provides a `setup_repo.py` script located in the `scripts` directory to handle API rate-limiting and safe git operations.

### `setup`
**Required Arguments:**
- `--repo-name`: Name of the GitHub repository.
- `--local-path`: Path to the local directory where the code is stored or will be cloned.
- `--output`: File path to output the JSON result.

**Optional Arguments:**
- `--description`: Description of the GitHub repository. If provided, the README will be populated with this description.

**Example Usage:**
```powershell
python scripts/setup_repo.py setup --repo-name "My-New-Project" --description "A sample project" --local-path "E:\ProgrameSpace\MyProject" --output "result.json"
```

## Environment Variables
- `GITHUB_PERSONAL_ACCESS_TOKEN`: A valid GitHub Fine-grained PAT with "Repository creation" Account permissions set to Read/Write. The agent must read the token from this environment variable.

## Rate Limiting
- The GitHub API requests incorporate a 1-second delay between requests `time.sleep(1)` inside the script to comply with standard GitHub rate limits.

## Common Mistakes
- **Missing Token or Permissions**: The most common issue is `GITHUB_PERSONAL_ACCESS_TOKEN` not being set or the token lacking the Account-level "Repository creation" permission.
- **Git Conflicts on Pull**: If the local directory already has uncommitted complex git histories that diverge drastically from the remote, the script uses `git reset --mixed origin/main` to gracefully handle the merge. But sensitive keys might be blocked by GitHub secret scanning on push. Ensure you mask secrets before using this skill!
