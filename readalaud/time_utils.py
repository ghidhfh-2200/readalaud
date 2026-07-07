"""
time_utils.py —— 时间格式化工具函数，无任何内部依赖，可被任意模块安全导入。
"""


def format_duration(seconds):
    """将秒数格式化为人类可读的中文时间字符串。

    规则：
      - < 1分钟   → "X秒"
      - < 1小时   → "X分X秒"
      - < 1天     → "X时X分X秒"
      - ≥ 1天     → "X天X时X分X秒"
    """
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}秒"

    mins, sec = divmod(seconds, 60)
    if seconds < 3600:
        return f"{mins}分{sec}秒" if sec else f"{mins}分钟"

    hours, rem = divmod(seconds, 3600)
    mins, sec = divmod(rem, 60)
    parts = [f"{hours}时"]
    if mins or sec:
        parts.append(f"{mins}分")
    if sec:
        parts.append(f"{sec}秒")
    if seconds < 86400:
        return "".join(parts)

    days, rem = divmod(seconds, 86400)
    hours, rem2 = divmod(rem, 3600)
    mins, sec = divmod(rem2, 60)
    parts = [f"{days}天"]
    if hours:
        parts.append(f"{hours}时")
    if mins:
        parts.append(f"{mins}分")
    if sec:
        parts.append(f"{sec}秒")
    return "".join(parts)
