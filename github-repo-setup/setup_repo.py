import argparse
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess

GITIGNORE_CONTENT = """#java
*.class

#package file
*.war

#maven ignore
target/
build/

#eclipse ignore
.settings/
.project
.classpath

#Intellij idea
.idea/
*.ipr
*.iml
*.iws

#vue&npm
node_modules/

#Python
#Python缓存文件
__pycache__/
*.py[cod]
#虚拟环境文件夹
.venv/
venv/
.env

# Editor & OS files
.vscode/
.DS_Store
Thumbs.db
"""

def request_github(url, method, token, data=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "antigravity-setup-repo-script"
    }
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        
    req = urllib.request.Request(url, headers=headers, method=method, data=req_data)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err_json = json.loads(body)
            msg = err_json.get("message", body)
        except Exception:
            msg = body
        print(f"GitHub API Error ({e.code}): {msg}", file=sys.stderr)
        raise RuntimeError(f"GitHub API request failed: {msg}")
    except Exception as e:
        print(f"Failed to connect to GitHub API: {e}", file=sys.stderr)
        raise e

def run_git_cmd(args, cwd):
    print(f"Running: git {' '.join(args)} in {cwd}")
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "false"
    
    res = subprocess.run(["git"] + args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Git command failed: git {' '.join(args)}", file=sys.stderr)
        print(f"STDOUT: {res.stdout}", file=sys.stderr)
        print(f"STDERR: {res.stderr}", file=sys.stderr)
        raise RuntimeError(f"Git command failed with exit code {res.returncode}")
    return res.stdout.strip()

def main():
    parser = argparse.ArgumentParser(description="Automate GitHub repository creation, local initialization, and initial commit/push.")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token (PAT)")
    parser.add_argument("--repo-name", required=True, help="Name of the GitHub repository")
    parser.add_argument("--local-path", required=True, help="Path to local folder")
    parser.add_argument("--description", default="Created via setup_repo.py", help="Description of the repository")
    args = parser.parse_args()
    
    local_path = os.path.abspath(args.local_path)
    
    # 1. Fetch GitHub User details to get username and email
    print("Fetching GitHub user details...")
    user_info, _ = request_github("https://api.github.com/user", "GET", args.token)
    username = user_info["login"]
    email = user_info.get("email") or f"{username}@users.noreply.github.com"
    print(f"Authenticated as: {username} <{email}>")
    
    # 2. Create the Repository on GitHub
    repo_url = f"https://github.com/{username}/{args.repo_name}"
    print(f"Creating public repository '{args.repo_name}' on GitHub...")
    repo_data = {
        "name": args.repo_name,
        "description": args.description,
        "private": False
    }
    
    try:
        request_github("https://api.github.com/user/repos", "POST", args.token, repo_data)
        print(f"Repository created successfully at: {repo_url}")
    except RuntimeError as e:
        if "already exists" in str(e).lower():
            print(f"Repository '{args.repo_name}' already exists on GitHub. Proceeding with existing repository.")
        else:
            raise e
            
    auth_remote_url = f"https://{username}:{args.token}@github.com/{username}/{args.repo_name}.git"
    
    # 3. Setup local repository
    if not os.path.exists(local_path):
        print(f"Local path '{local_path}' does not exist. Cloning repository...")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            run_git_cmd(["clone", auth_remote_url, local_path], cwd=os.getcwd())
            print("Cloned successfully.")
        except RuntimeError:
            print("Clone failed (possibly empty repository). Initializing locally instead...")
            os.makedirs(local_path, exist_ok=True)
            run_git_cmd(["init"], cwd=local_path)
            run_git_cmd(["remote", "add", "origin", auth_remote_url], cwd=local_path)
    else:
        print(f"Local path '{local_path}' exists. Initializing Git if not already initialized...")
        if not os.path.exists(os.path.join(local_path, ".git")):
            run_git_cmd(["init"], cwd=local_path)
            run_git_cmd(["remote", "add", "origin", auth_remote_url], cwd=local_path)
        else:
            print("Git already initialized. Updating remote 'origin' URL...")
            try:
                run_git_cmd(["remote", "set-url", "origin", auth_remote_url], cwd=local_path)
            except RuntimeError:
                run_git_cmd(["remote", "add", "origin", auth_remote_url], cwd=local_path)
        
        print("Fetching remote repository history...")
        try:
            run_git_cmd(["fetch", "origin"], cwd=local_path)
            run_git_cmd(["branch", "-M", "main"], cwd=local_path)
            try:
                run_git_cmd(["reset", "--mixed", "origin/main"], cwd=local_path)
                print("Merged remote history with local changes.")
            except RuntimeError:
                print("No remote main branch found or unable to reset. Proceeding...")
        except RuntimeError:
            print("Fetch failed or repository is empty. Proceeding...")
            run_git_cmd(["branch", "-M", "main"], cwd=local_path)
            
    # 4. Create .gitignore if not exists
    gitignore_path = os.path.join(local_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        print("Creating .gitignore...")
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(GITIGNORE_CONTENT)
        print(".gitignore created.")
    else:
        print(".gitignore already exists. Skipping.")
        
    # 5. Configure Git user info locally
    print("Configuring local git user...")
    run_git_cmd(["config", "user.name", username], cwd=local_path)
    run_git_cmd(["config", "user.email", email], cwd=local_path)
    
    # 6. Add and commit files
    print("Checking git status...")
    run_git_cmd(["add", "."], cwd=local_path)
    status_out = run_git_cmd(["status", "--porcelain"], cwd=local_path)
    if status_out:
        print("Committing files...")
        run_git_cmd(["commit", "-m", "Initial commit via github-repo-setup"], cwd=local_path)
    else:
        print("No changes to commit.")
        
    # 7. Push to GitHub
    print("Pushing to GitHub...")
    run_git_cmd(["push", "-u", "origin", "main"], cwd=local_path)
    print(f"Success! Repository successfully set up at: {repo_url}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
