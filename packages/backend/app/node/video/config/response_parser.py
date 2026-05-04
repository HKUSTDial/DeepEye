from __future__ import annotations

import json
import re
from typing import Any


def format_response_for_debug(raw: str | None, *, model: str, head: int = 500, tail: int = 300) -> str:
    """Build a helpful diagnostic string for bad JSON responses."""
    if raw is None:
        return f"model={model} raw=None"
    raw_len = len(raw)
    stripped = raw.strip()
    stripped_len = len(stripped)
    if stripped_len == 0:
        return f"model={model} raw_len={raw_len} stripped_len=0 (empty/whitespace)"
    head_txt = stripped[:head]
    tail_txt = stripped[-tail:] if stripped_len > tail else stripped
    return (
        f"model={model} raw_len={raw_len} stripped_len={stripped_len}\n"
        f"--- response_head ---\n{head_txt}\n"
        f"--- response_tail ---\n{tail_txt}\n"
    )


def clean_json_control_chars(json_str: str) -> str:
    """Escape or remove raw control characters that can appear in LLM JSON."""
    json_str = json_str.replace("\n", "\\n")
    json_str = json_str.replace("\r", "\\r")
    json_str = json_str.replace("\t", "\\t")
    json_str = json_str.replace("\b", "\\b")
    json_str = json_str.replace("\f", "\\f")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", json_str)


def _extract_json_object(response: str, *, model: str) -> str:
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        return response[start:end].strip()
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        return response[start:end].strip()

    json_str = None
    brace_count = 0
    start_idx = -1
    for i, char in enumerate(response):
        if char == "{":
            if start_idx == -1:
                start_idx = i
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                json_str = response[start_idx : i + 1]
                break

    if json_str:
        return json_str

    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
    if match:
        return match.group(0)

    raise ValueError(
        "Cannot parse JSON response (no JSON object found).\n"
        + format_response_for_debug(response, model=model)
    )


def _strip_json_comments_and_trailing_commas(json_str: str) -> str:
    json_str_cleaned = re.sub(r",\s*}", "}", json_str)
    json_str_cleaned = re.sub(r",\s*]", "]", json_str_cleaned)
    json_str_cleaned = re.sub(r"//.*?$", "", json_str_cleaned, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", json_str_cleaned, flags=re.DOTALL)


def _apply_common_json_repairs(json_str: str) -> str:
    json_str_fixed = json_str
    repair_patterns = (
        (r"(\d+)\s*\"", r'\1, "'),
        (r"(\d+)\s*\n\s*\"", r'\1,\n"'),
        (r"\"\s*(\d+)", r'", \1'),
        (r"(true|false|null)\s*\"", r'\1, "'),
        (r"([}\])\s*\"", r'\1, "'),
        (r"(\d+)\s*\",", r"\1,"),
        (r"(\d+)\s*\"\s*\n", r"\1,\n"),
    )
    for pattern, replacement in repair_patterns:
        try:
            json_str_fixed = re.sub(pattern, replacement, json_str_fixed)
        except re.error:
            pass

    try:
        json_str_fixed = re.sub(r",\s*}", "}", json_str_fixed)
        json_str_fixed = re.sub(r",\s*]", "]", json_str_fixed)
    except re.error:
        pass

    return json_str_fixed


def _count_preceding_backslashes(value: str, quote_pos: int) -> int:
    backslash_count = 0
    j = quote_pos - 1
    while j >= 0 and value[j] == "\\":
        backslash_count += 1
        j -= 1
    return backslash_count


def _try_fix_unterminated_string(
    json_str_fixed: str,
    *,
    error_pos: int,
    verbose: bool,
) -> Any | None:
    quote_pos = -1
    for i in range(error_pos - 1, max(0, error_pos - 200), -1):
        char = json_str_fixed[i]
        if char == '"' and _count_preceding_backslashes(json_str_fixed, i) % 2 == 0:
            quote_pos = i
            break

    if quote_pos < 0:
        return None

    end_pos = len(json_str_fixed)
    found_closing = False
    for i in range(error_pos, min(len(json_str_fixed), error_pos + 500)):
        char = json_str_fixed[i]
        if char == '"':
            if _count_preceding_backslashes(json_str_fixed, i) % 2 == 0:
                end_pos = i + 1
                found_closing = True
                break
        elif char in ["}", "]", ",", "\n"] and i > quote_pos + 1:
            end_pos = i
            break

    if found_closing or end_pos >= len(json_str_fixed):
        return None

    json_str_fixed = json_str_fixed[:end_pos] + '"' + json_str_fixed[end_pos:]
    if verbose:
        print(f"      🔧 Fixed unterminated string: inserted closing quote at position {end_pos}")
    return json.loads(json_str_fixed)


def parse_llm_json_response(
    response: str,
    usage: dict[str, Any],
    *,
    model: str,
    verbose: bool = True,
) -> tuple[Any, dict[str, Any]]:
    """Parse an LLM response into JSON while preserving legacy repair behavior."""
    try:
        parsed_json = json.loads(response)
        if isinstance(parsed_json, list) and len(parsed_json) == 1:
            if verbose:
                print("      ⚠️  LLM returned array instead of object, auto-extracting first element")
            parsed_json = parsed_json[0]
        return parsed_json, usage
    except json.JSONDecodeError:
        json_str = _extract_json_object(response, model=model)

    if json_str:
        try:
            json_str_cleaned = _strip_json_comments_and_trailing_commas(json_str)
            try:
                parsed_json = json.loads(json_str_cleaned)
                return parsed_json, usage
            except json.JSONDecodeError as e:
                if "Invalid control character" in str(e) or "control character" in str(e):
                    json_str_cleaned = clean_json_control_chars(json_str_cleaned)
                    parsed_json = json.loads(json_str_cleaned)
                    return parsed_json, usage
                raise
        except json.JSONDecodeError as e:
            try:
                json_str_fixed = _apply_common_json_repairs(json_str)
                parsed_json = json.loads(json_str_fixed)
                return parsed_json, usage
            except (json.JSONDecodeError, ValueError) as e2:
                if "Unterminated string" in str(e2) or "Unterminated string" in str(e):
                    try:
                        error_pos = e2.pos if hasattr(e2, "pos") else (e.pos if hasattr(e, "pos") else 0)
                        parsed_json = _try_fix_unterminated_string(
                            json_str_fixed,
                            error_pos=error_pos,
                            verbose=verbose,
                        )
                        if parsed_json is not None:
                            return parsed_json, usage
                    except Exception:
                        pass

                error_pos = e2.pos if hasattr(e2, "pos") else (e.pos if hasattr(e, "pos") else 0)
                context_start = max(0, error_pos - 50)
                context_end = min(len(json_str), error_pos + 50)
                raise ValueError(
                    f"JSON parse error at position {error_pos}: "
                    f"{e2.msg if hasattr(e2, 'msg') else str(e2)}\n"
                    f"Context: {json_str[context_start:context_end]}"
                )

    raise ValueError(
        "Cannot parse JSON response.\n"
        + format_response_for_debug(response, model=model)
    )

