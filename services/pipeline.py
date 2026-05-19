from services.repo_loader import clone_repo
from services.file_parser import get_python_files, read_file, extract_function_bodies, ast_scan, regex_scan
from services.llm_reviewer import generate_review
from services.llm_reviewer import safe_parse_llm_output
import subprocess
import time

def chunk_code(code, max_chars=3000):
    return [code[i:i+max_chars] for i in range(0, len(code), max_chars)]

def run_pipeline(repo_url: str, logger=None, update_callback=None):
    if logger is None:
        class DummyLogger:
            def log(self, *a, **k): pass
            def success(self, *a, **k): pass
            def error(self, *a, **k): pass
        logger = DummyLogger()
    
    logger.log("Cloning repository...")
    if update_callback: update_callback()
    repo_path = clone_repo(repo_url, logger=logger, update_callback=update_callback)
    if not isinstance(repo_path, str) or not repo_path.startswith("cloned_repos"):
        return {"error": repo_path}
    
    logger.log("Scanning for Python files...")
    if update_callback: update_callback()
    py_files = get_python_files(repo_path)
    if not py_files:
        return {"error": "No Python files detected in repository", "repo_path": repo_path}
    
    logger.success(f"Found {len(py_files)} Python files")
    if update_callback: update_callback()
    
    all_issues = []
    seen = set()
    for fpath in py_files:
        code = read_file(fpath)
        if len(code.strip()) < 120:
            continue
        functions = extract_function_bodies(code)
        file_issues = []
        logger.log(f"Analyzing {fpath.split('/')[-1]}...")
        if update_callback: update_callback()
        
        # 1. AST + Regex pre-scan
        static_issues = ast_scan(code, fpath) + regex_scan(code, fpath)
        for i in static_issues:
            key = (fpath, i.get("line", 0), i.get("title", ""))
            if key not in seen:
                seen.add(key)
                file_issues.append(i)
        
        # 2. Only send suspicious chunks to LLM
        MAX_CHARS = 4000
        chunks = [code[i:i+MAX_CHARS] for i in range(0, len(code), MAX_CHARS)]
        
        for chunk in chunks:
            if any(kw in chunk for kw in ["eval(", "exec(", "pickle", "yaml.load", "requests.get"]):
                time.sleep(4)  # Smart rate limit
                result = generate_review(chunk, fpath)
                parsed = safe_parse_llm_output(result)
                if isinstance(parsed, dict) and "issues" in parsed:
                    parsed = parsed["issues"]
                for issue in parsed:
                    key = (fpath, issue.get("line", 0), issue.get("title", issue.get("message", "")))
                    if key not in seen:
                        seen.add(key)
                        file_issues.append(issue)
        INVALID_TITLES = ["****", "", None]
        file_issues = [i for i in file_issues if i.get("title") not in INVALID_TITLES]
        
        # Reject vague/generic
        file_issues = [
            i for i in file_issues 
            if "add input validation" not in i.get("suggestion", "").lower()
            and i.get("confidence", 80) >= 70
        ]
        all_issues.extend(file_issues[:3])
    logger.success("Analysis complete")
    if update_callback: update_callback()
    summary = {"high": 0, "medium": 0, "low": 0}
    for issue in all_issues:
        if "severity" in issue:
            sev = issue["severity"]
            if sev in summary:
                summary[sev] += 1
    print("TOTAL ISSUES:", len(all_issues))
    print(all_issues[:5])
    return {
        "repo_path": repo_path,
        "files_analyzed": len(py_files),
        "issues_found": all_issues,
        "summary": summary
    }