"""
Sanitize LLM-generated TSX before writing to disk.
Prevents browser compile errors: declare module blocks, unterminated filter strings.
Also provides validate_component_syntax (esbuild + Python fallback) for retry logic.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional


def strip_declare_module_blocks(source: str) -> str:
    """Remove declare module '...' { ... } blocks (supports nested braces)."""
    out = source
    pattern = re.compile(r"declare\s+module\s+['\"][^'\"]+['\"]\s*\{")
    pos = 0
    while True:
        m = pattern.search(out, pos)
        if not m:
            break
        start = m.start()
        brace_start = m.end()
        depth = 1
        i = brace_start
        while i < len(out) and depth > 0:
            if out[i] == "{":
                depth += 1
            elif out[i] == "}":
                depth -= 1
            i += 1
        end = i if depth == 0 else len(out)
        replacement = "/* declare module block removed */\n"
        out = out[:start] + replacement + out[end:]
        pos = start + len(replacement)
    return out


def repair_unterminated_filter_strings(source: str) -> str:
    """Fix truncated .style('filter', 'drop-shadow(0 0 15px rgba(NNN' lines."""
    return re.sub(
        r"\.style\s*\(\s*['\"]filter['\"]\s*,\s*['\"]drop-shadow\s*\(\s*0\s+0\s+15px\s+rgba\s*\(\s*(\d+)[^\n]*$",
        r".style('filter', 'drop-shadow(0 0 15px rgba(\1, 107, 107, 0.8))');",
        source,
        flags=re.MULTILINE,
    )


def repair_invalid_keyof_indexing(source: str) -> str:
    """Downgrade LLM-generated TS keyof index assertions to plain runtime indexing.

    Some generated TSX uses expressions like:
      d[k as keyof typeof d]
      filter[k as keyof typeof filter]
      a.target_data!.data_filter[k as keyof typeof a.target_data!.data_filter]

    These are fragile in generated code and can break Vite/Babel parsing when
    combined with non-null assertions or nested expressions. Runtime logic only
    needs dynamic property access, so rewrite them to plain [k].
    """
    return re.sub(
        r"\[\s*([A-Za-z_$][\w$]*)\s+as\s+keyof\s+typeof\s+[^\]]+\]",
        r"[\1]",
        source,
    )


def _balance_brackets(code: str, open_c: str, close_c: str) -> int:
    """Return final depth (0 = balanced). Skip inside strings and block comments."""
    depth = 0
    i = 0
    while i < len(code):
        c = code[i]
        if c in ("'", '"'):
            q = c
            i += 1
            while i < len(code) and code[i] != q:
                if code[i] == "\\":
                    i += 1
                i += 1
            if i < len(code):
                i += 1
            continue
        if c == "/" and i + 1 < len(code) and code[i + 1] == "*":
            i += 2
            while i + 1 < len(code) and (code[i] != "*" or code[i + 1] != "/"):
                i += 1
            if i + 1 < len(code):
                i += 2
            continue
        if c == "/" and i + 1 < len(code) and code[i + 1] == "/":
            i += 2
            while i < len(code) and code[i] != "\n":
                i += 1
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
        i += 1
    return depth


def validate_component_syntax(tsx_file: Path) -> Tuple[bool, Optional[str]]:
    """
    校验 TSX 语法。优先用 esbuild；无 Node 或失败时用 Python 兜底（括号平衡 + return/};）。
    返回 (True, None) 通过，(False, error_message) 不通过。
    """
    path = Path(tsx_file)
    if not path.exists():
        return False, "文件不存在"
    code = path.read_text(encoding="utf-8", errors="replace")
    if len(code.strip()) < 100:
        return False, "TSX 过短，可能被截断"

    # 1) 尝试 esbuild
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            script_dir = path.resolve().parent
            cmd = [
                "npx", "esbuild",
                str(path.resolve()),
                "--bundle", "--format=esm", "--jsx=automatic",
                f"--outfile={tmp_path}",
                "--log-level=error",
            ]
            r = subprocess.run(
                cmd,
                cwd=script_dir,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                return True, None
            err = (r.stderr or r.stdout or "").strip()
            if err:
                return False, "\n".join(err.split("\n")[:5])
            return False, "esbuild 编译失败"
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except subprocess.TimeoutExpired:
        return False, "esbuild 验证超时"
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 2) Python 兜底：括号平衡 + 必须有 return ( 和 };
    depth_brace = _balance_brackets(code, "{", "}")
    if depth_brace != 0:
        return False, f"大括号未闭合 (深度差: {depth_brace})，可能被截断"
    depth_paren = _balance_brackets(code, "(", ")")
    if depth_paren != 0:
        return False, f"圆括号未闭合 (深度差: {depth_paren})，可能被截断"
    if "return (" not in code and "return(" not in code.replace(" ", ""):
        return False, "缺少 return (，组件可能被截断"
    if "};" not in code:
        return False, "缺少组件结尾 };，可能被截断"
    return True, None


def sanitize_tsx_for_browser(tsx_code: str) -> str:
    """Apply all sanitizations so TSX can be compiled in the browser."""
    code = strip_declare_module_blocks(tsx_code)
    code = repair_unterminated_filter_strings(code)
    code = repair_invalid_keyof_indexing(code)
    return code
