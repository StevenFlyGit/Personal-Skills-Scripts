import argparse
import json
import os
import sys
import subprocess
import time
import urllib.request
import urllib.error
import base64

def check_env():
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                token, _ = winreg.QueryValueEx(key, "GITHUB_PERSONAL_ACCESS_TOKEN")
        except FileNotFoundError:
            pass
    if not token:
        print("Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set.", file=sys.stderr)
        sys.exit(1)
    return token

def github_api_request(url, method, token, data=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }
    
    req_data = None
    if data:
        req_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    # Simple rate limiting
    time.sleep(1)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in [200, 201, 204]:
                if response.status == 204:
                    return {}
                return json.loads(response.read().decode())
            else:
                print(f"Error: HTTP {response.status}", file=sys.stderr)
                sys.exit(1)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTPError: {e.code} - {e.reason}", file=sys.stderr)
        print(f"Response: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

def get_username(token):
    res = github_api_request("https://api.github.com/user", "GET", token)
    return res.get("login")

def create_repo(token, name, description):
    data = {
        "name": name,
        "description": description,
        "private": False,
        "auto_init": False
    }
    res = github_api_request("https://api.github.com/user/repos", "POST", token, data)
    return res.get("html_url"), res.get("clone_url")

def create_readme(token, owner, repo, description):
    body_text = description if description else f"{owner}'s repository."
    content = f"# {repo}\n\n{body_text}\n"
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    
    data = {
        "message": "Initial commit with README",
        "content": encoded_content
    }
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
    github_api_request(url, "PUT", token, data)

def create_gitignore(local_path):
    gitignore_content = """#java
*.class
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
__pycache__/
*.py[cod]
.venv/
venv/
.env

# OS generated files
.DS_Store
Thumbs.db

# VS Code
.vscode/
"""
    os.makedirs(local_path, exist_ok=True)
    with open(os.path.join(local_path, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore_content)

def run_git_commands(local_path, clone_url, token, owner):
    auth_url = clone_url.replace("https://", f"https://{owner}:{token}@")
    
    # Avoid hanging on auth prompts
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "false"
    
    def run_cmd(cmd):
        res = subprocess.run(cmd, cwd=local_path, shell=True, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Git command failed: {cmd}", file=sys.stderr)
            print(res.stderr, file=sys.stderr)
            sys.exit(1)
        return res.stdout

    # Initialize and configure
    if not os.path.exists(os.path.join(local_path, ".git")):
        run_cmd("git init")
    
    # Reset remote origin
    subprocess.run("git remote remove origin", cwd=local_path, shell=True, capture_output=True)
    run_cmd(f"git remote add origin {auth_url}")
    
    run_cmd("git fetch origin")
    run_cmd("git checkout -B main origin/main || git checkout -b main")
    run_cmd("git reset --mixed origin/main")
    
    # Configure user
    run_cmd("git config user.name GitHub-Agent")
    run_cmd("git config user.email agent@example.com")
    
    run_cmd("git add .")
    res = subprocess.run("git commit -m \"Initial automated commit\"", cwd=local_path, shell=True, env=env, capture_output=True, text=True)
    
    run_cmd("git push -u origin main")

def main():
    parser = argparse.ArgumentParser(description="Setup a GitHub repository and push local code.")
    parser.add_argument("command", choices=["setup"], help="Command to run")
    parser.add_argument("--repo-name", required=True, help="Name of the repository")
    parser.add_argument("--description", required=False, default="", help="Description for the repository")
    parser.add_argument("--local-path", required=True, help="Local directory path")
    parser.add_argument("--output", required=True, help="Path to write the JSON result")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        token = check_env()
        print("Authenticating to GitHub...", file=sys.stderr)
        owner = get_username(token)
        
        print(f"Creating repository {args.repo_name}...", file=sys.stderr)
        html_url, clone_url = create_repo(token, args.repo_name, args.description)
        
        print("Creating README.md via API...", file=sys.stderr)
        create_readme(token, owner, args.repo_name, args.description)
        
        print("Setting up local directory...", file=sys.stderr)
        create_gitignore(args.local_path)
        
        print("Running git commands to push to remote...", file=sys.stderr)
        run_git_commands(args.local_path, clone_url, token, owner)
        
        result = {
            "status": "success",
            "repo_url": html_url,
            "local_path": args.local_path,
            "message": f"Successfully setup {args.repo_name} and pushed local changes."
        }
        
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            
        print(f"Success! Data written to: {args.output}")

if __name__ == "__main__":
    main()
