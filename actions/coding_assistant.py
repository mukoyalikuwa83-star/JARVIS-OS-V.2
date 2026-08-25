"""Coding assistant — write, run, test, and debug code across multiple languages."""

import subprocess
import os
import sys
import time
import tempfile
from pathlib import Path


def _run(cmd, timeout=30, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT|Command took too long", 1
    except Exception as e:
        return str(e), 1


def _detect_language(code: str) -> str:
    code_lower = code.strip().lower()
    if code_lower.startswith("import ") or code_lower.startswith("from ") or "def " in code:
        return "python"
    if code_lower.startswith("public class") or code_lower.startswith("class ") and "{" in code:
        return "java"
    if "#include" in code or "int main" in code:
        return "c_cpp"
    if "function " in code or "=>" in code or "const " in code or "let " in code:
        return "javascript"
    if "<html" in code_lower or "<div" in code_lower:
        return "html"
    if code_lower.startswith("select ") or code_lower.startswith("create table"):
        return "sql"
    if "fn " in code or "println!" in code:
        return "rust"
    return "unknown"


def _write_code(params: dict) -> str:
    """Write code to a file."""
    code = str(params.get("code", "") or "").strip()
    filename = str(params.get("filename", "") or "").strip()
    language = str(params.get("language", "") or "").strip().lower()

    if not code:
        return "ERROR: Provide code to write."

    if not language:
        language = _detect_language(code)

    ext_map = {
        "python": ".py", "javascript": ".js", "java": ".java",
        "c_cpp": ".cpp", "html": ".html", "sql": ".sql", "rust": ".rs",
    }
    ext = ext_map.get(language, ".txt")

    if not filename:
        filename = f"code_{int(time.time())}{ext}"

    workspace = Path(os.environ.get("TEMP", ".")) / "jarvis_code"
    workspace.mkdir(parents=True, exist_ok=True)
    filepath = workspace / filename

    filepath.write_text(code, encoding="utf-8")
    return f"CODE_WRITTEN|{filepath}|Language: {language}|Lines: {len(code.splitlines())}"


def _run_code(params: dict) -> str:
    """Run code in the appropriate interpreter."""
    code = str(params.get("code", "") or "").strip()
    filename = str(params.get("filename", "") or "").strip()
    language = str(params.get("language", "") or "").strip().lower()
    timeout = int(params.get("timeout", 30) or 30)

    if not code and not filename:
        return "ERROR: Provide code or a filename to run."

    if filename and Path(filename).exists():
        filepath = Path(filename)
        code = filepath.read_text(encoding="utf-8")
    elif code:
        if not language:
            language = _detect_language(code)
        ext_map = {
            "python": ".py", "javascript": ".js", "java": ".java",
            "c_cpp": ".cpp", "html": ".html", "sql": ".sql", "rust": ".rs",
        }
        ext = ext_map.get(language, ".txt")
        workspace = Path(os.environ.get("TEMP", ".")) / "jarvis_code"
        workspace.mkdir(parents=True, exist_ok=True)
        filepath = workspace / f"code_{int(time.time())}{ext}"
        filepath.write_text(code, encoding="utf-8")
    else:
        return "ERROR: No code or file to run."

    if not language:
        language = _detect_language(code)

    interpreters = {
        "python": [sys.executable, str(filepath)],
        "javascript": ["node", str(filepath)],
        "java": ["javac", str(filepath), "&&", "java", filepath.stem],
        "c_cpp": ["g++", str(filepath), "-o", str(filepath.with_suffix("")), "&&", str(filepath.with_suffix(""))],
        "rust": ["rustc", str(filepath), "&&", str(filepath.with_suffix(""))],
    }

    if language == "java":
        out, code = _run(["javac", str(filepath)], timeout=timeout)
        if code != 0:
            return f"COMPILE_ERROR|\n{out}"
        out, code = _run(["java", "-cp", str(filepath.parent), filepath.stem], timeout=timeout)
    elif language == "c_cpp":
        exe = filepath.with_suffix(".exe" if os.name == "nt" else "")
        out, code = _run(["g++", str(filepath), "-o", str(exe)], timeout=timeout)
        if code != 0:
            return f"COMPILE_ERROR|\n{out}"
        out, code = _run([str(exe)], timeout=timeout)
    elif language == "rust":
        exe = filepath.with_suffix(".exe" if os.name == "nt" else "")
        out, code = _run(["rustc", str(filepath), "-o", str(exe)], timeout=timeout)
        if code != 0:
            return f"COMPILE_ERROR|\n{out}"
        out, code = _run([str(exe)], timeout=timeout)
    elif language in interpreters:
        out, code = _run(interpreters[language], timeout=timeout)
    else:
        return f"ERROR: Cannot run {language} code."

    status = "RUN_OK" if code == 0 else f"RUN_ERROR (exit {code})"
    output = out[:5000] if out else "(no output)"
    return f"{status}|\n{output}"


def _test_code(params: dict) -> str:
    """Run code and compare output to expected."""
    code = str(params.get("code", "") or "").strip()
    expected = str(params.get("expected", "") or "").strip()
    language = str(params.get("language", "") or "").strip().lower()

    if not code:
        return "ERROR: Provide code to test."
    if not expected:
        return "ERROR: Provide expected output to compare against."

    result = _run_code({"code": code, "language": language})
    if result.startswith("COMPILE_ERROR") or result.startswith("RUN_ERROR"):
        return f"TEST_FAILED|{result}"

    actual = result.split("|", 1)[1].strip() if "|" in result else result.strip()
    expected_clean = expected.strip()
    actual_clean = actual.strip()

    if expected_clean in actual_clean or actual_clean in expected_clean:
        return f"TEST_PASSED|Output matches expected."
    else:
        return f"TEST_FAILED|Expected: {expected_clean}\nGot: {actual_clean}"


def _debug_code(params: dict) -> str:
    """Analyze code for errors and suggest fixes."""
    code = str(params.get("code", "") or "").strip()
    language = str(params.get("language", "") or "").strip().lower()
    error = str(params.get("error", "") or "").strip()

    if not code:
        return "ERROR: Provide code to debug."

    if not language:
        language = _detect_language(code)

    issues = []
    if language == "python":
        if "indent" in error.lower():
            issues.append("Indentation error — check spacing")
        if "syntaxerror" in error.lower():
            issues.append("Syntax error — check colons, parentheses, quotes")
        if "nameerror" in error.lower():
            issues.append("Name not defined — check variable/function names")
        if "import" in error.lower():
            issues.append("Import error — check module name and installation")
        if not issues:
            issues.append("General Python issue — check syntax and logic")

    lines = code.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if language == "python":
            if stripped.endswith(":") and i + 1 < len(lines) and not lines[i + 1].strip():
                issues.append(f"Line {i+1}: Empty block after colon")
            if "=" in stripped and "==" not in stripped and "!=" not in stripped and "<=" not in stripped and ">=" not in stripped:
                if any(kw in stripped for kw in ["import ", "from ", "return ", "print("]):
                    pass
                elif stripped.count("=") == 1 and any(c.isalpha() for c in stripped.split("=")[1]):
                    pass

    if issues:
        return f"DEBUG_REPORT|{' | '.join(issues)}"
    return "DEBUG_REPORT|No obvious issues found. Check logic manually."


def handle(params: dict) -> str:
    """Tool handler."""
    action = str(params.get("action", "write") or "write").lower()
    if action == "write":
        return _write_code(params)
    elif action == "run":
        return _run_code(params)
    elif action == "test":
        return _test_code(params)
    elif action == "debug":
        return _debug_code(params)
    return f"Unknown action: {action}. Valid: write, run, test, debug"
