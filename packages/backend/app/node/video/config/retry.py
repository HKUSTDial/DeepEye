from __future__ import annotations


def should_retry_on_error(
    error_msg: str,
    attempt: int,
    elapsed_time: float,
    max_general_retries: int = 10,
) -> tuple[bool, str]:
    """Decide whether a transient LLM API error should be retried."""
    error_lower = str(error_msg).lower()

    if any(keyword in error_lower for keyword in ["余额不足", "insufficient", "quota exceeded", "no credit"]):
        return False, "余额不足（永久性错误）"

    if any(keyword in error_lower for keyword in ["401", "403", "unauthorized", "forbidden"]):
        return False, "认证失败（永久性错误）"

    if "400" in error_lower and "format" in error_lower:
        return False, "请求格式错误（永久性错误）"

    if any(keyword in error_lower for keyword in ["context length", "maximum context"]):
        if "exceeded" in error_lower or "too long" in error_lower or "128000" in error_lower:
            return False, "Context length 超出限制（永久性错误，重试会浪费 token）"

    if any(keyword in error_lower for keyword in ["429", "rate limit", "throttling", "too many requests"]):
        max_time = 30 * 60
        if elapsed_time < max_time:
            return True, f"Rate Limit（允许重试至{max_time/60:.0f}分钟）"
        return False, f"Rate Limit 超过最大时间限制（{max_time/60:.0f}分钟）"

    if attempt < max_general_retries:
        return True, f"临时性错误（最多{max_general_retries}次）"

    return False, f"已达到最大重试次数（{max_general_retries}次）"


def calculate_retry_wait_time(error_msg: str, attempt: int) -> int:
    """Calculate exponential backoff wait time for LLM API retries."""
    error_lower = str(error_msg).lower()

    if any(keyword in error_lower for keyword in ["429", "rate limit", "throttling", "too many requests"]):
        return min(2**attempt, 60)

    return 2

