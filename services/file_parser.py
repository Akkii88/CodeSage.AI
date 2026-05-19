import os
import ast
import re

def get_python_files(repo_path: str):
    print("Scanning repo_path:", repo_path)
    ignore_dirs = {"__pycache__", ".git", "venv", "env", ".idea", "tests", "docs", "_themes"}
    ignore_lower = {d.lower() for d in ignore_dirs}
    py_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d.lower() not in ignore_lower]
        for file in files:
            if file.lower().endswith(".py"):
                py_files.append(os.path.join(root, file))
    print("Total Python files found:", len(py_files))
    if py_files:
        print("First 5 files:", py_files[:5])
    return py_files

def read_file(file_path: str):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def extract_ast_structure(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"functions": [], "classes": [], "imports": []}
    functions = []
    classes = []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
    return {"functions": functions, "classes": classes, "imports": list(set(imports))}

def extract_function_bodies(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [code]
    lines = code.splitlines(keepends=True)
    bodies = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            try:
                body = ast.get_source_segment(code, node)
                if body:
                    bodies.append(body)
            except:
                start = node.lineno - 1
                end = getattr(node, 'end_lineno', start + 10)
                bodies.append(''.join(lines[start:end]))
    if not bodies:
        bodies.append(code)
    return bodies

DANGEROUS_FUNCTIONS = {
    "eval": "Code Injection",
    "exec": "Command Injection",
    "pickle.loads": "Unsafe Deserialization",
    "yaml.load": "Unsafe YAML Load",
    "os.system": "Command Execution",
    "subprocess.call": "Command Execution"
}

def ast_scan(code, file_path):
    issues = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        func_name = f"{node.func.value.id}.{node.func.attr}"
                if func_name in DANGEROUS_FUNCTIONS:
                    issues.append({
                        "severity": "high",
                        "title": DANGEROUS_FUNCTIONS[func_name],
                        "description": f"Detected dangerous call: {func_name}",
                        "file": file_path,
                        "line": node.lineno,
                        "suggestion": "Replace with safer alternative"
                    })
    except Exception as e:
        print("AST ERROR:", e)
    return issues

PATTERNS = {
    "SQL Injection": r"SELECT .* \+",
    "Hardcoded Secret": r"(API_KEY|SECRET|PASSWORD)\s*=",
    "Weak Hash": r"md5\(",
    "SSRF": r"requests\.get\(",
}

def regex_scan(code, file_path):
    findings = []
    for vuln, pattern in PATTERNS.items():
        if re.search(pattern, code):
            findings.append({
                "severity": "medium",
                "title": vuln,
                "description": f"Potential {vuln} detected",
                "file": file_path,
                "suggestion": "Review and sanitize input"
            })
    return findings