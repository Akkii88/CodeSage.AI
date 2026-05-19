import os
import subprocess
from git.exc import GitCommandError, InvalidGitRepositoryError

def clone_repo(repo_url: str, logger=None, update_callback=None):
    if logger is None:
        class Dummy: 
            def log(self,*a,**k): pass
        logger = Dummy()
    
    if not repo_url.startswith("https://github.com/"):
        return "Invalid URL: must start with https://github.com/"
    parts = repo_url.rstrip("/").replace(".git", "").split("/")
    if len(parts) < 5 or not parts[-2] or not parts[-1]:
        return "Invalid GitHub repo URL: expected https://github.com/owner/repo"
    repo_name = parts[-1]
    base_dir = "cloned_repos"
    local_path = os.path.join(base_dir, repo_name)
    os.makedirs(base_dir, exist_ok=True)
    if os.path.exists(local_path):
        logger.log("Using cached repository")
        if update_callback: update_callback()
        return local_path
    
    try:
        logger.log(f"Cloning {repo_name}...")
        if update_callback: update_callback()
        
        process = subprocess.Popen(
            ["git", "clone", "--progress", repo_url, local_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.log(line)
                if update_callback: update_callback()
        
        process.wait()
        if process.returncode == 0:
            logger.success("Clone successful")
            if update_callback: update_callback()
            return local_path
        else:
            return f"Clone failed with code {process.returncode}"
    except Exception as e:
        return f"Clone failed: {str(e)}"