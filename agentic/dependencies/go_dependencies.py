import os
import subprocess
import json
from pathlib import Path

def get_module_path(go_mod_path):
    """Extract the module path from a go.mod file."""
    try:
        with open(go_mod_path, 'r') as f:
            for line in f:
                if line.startswith('module '):
                    return line.split()[1].strip()
    except Exception:
        pass
    return None

def get_go_modules(repo_path):
    """Return a list of (module, version) tuples for all external dependencies."""
    repo_path = Path(repo_path)
    # First, check if go.mod and go.sum exist directly in repo_path
    go_mod = repo_path / "go.mod"
    go_sum = repo_path / "go.sum"
    if go_mod.exists() and go_sum.exists():
        found_path = repo_path
    else:
        found_path = None
        for root, dirs, files in os.walk(repo_path):
            if "go.mod" in files and "go.sum" in files:
                found_path = Path(root)
                break
        if not found_path:
            print(f"No go.mod/go.sum found in {repo_path} or its subdirectories, skipping dependency extraction.")
            return []
    try:
        result = subprocess.run(
            ["go", "list", "-m", "-json", "-mod=mod", "all"],
            cwd=str(found_path),
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Error running 'go list -m -json all':")
        print(e.stderr)
        return []
    modules = {}
    # Get the internal prefix from the main module path
    mod_path_full = get_module_path(go_mod if go_mod.exists() else found_path / "go.mod")
    # Extract just the github.com/org/ part for internal marking
    internal_prefix = None
    if mod_path_full and mod_path_full.startswith("github.com/"):
        parts = mod_path_full.split("/")
        if len(parts) >= 3:
            internal_prefix = "/".join(parts[:2]) + "/"
        else:
            internal_prefix = mod_path_full + "/"
    else:
        internal_prefix = mod_path_full
    # The output is a sequence of JSON objects, not a JSON array
    for obj in result.stdout.split('\n}\n'):
        obj = obj.strip()
        if not obj:
            continue
        if not obj.endswith('}'):
            obj += '}'
        try:
            mod_info = json.loads(obj)
            mod = mod_info.get('Path')
            ver = mod_info.get('Version')
            if mod and ver and not mod.startswith('golang.org'):
                dep_type = "internal" if internal_prefix and mod.startswith(internal_prefix) else "external"
                modules[mod] = {
                    'module': mod,
                    'version': ver,
                    'type': dep_type
                }
        except Exception:
            continue
    return modules
