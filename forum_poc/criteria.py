import re

QUANTIFIED_KINDS = ("硬性限制", "預算")
QUANTITY_RE = re.compile(r"\d+(\.\d+)?\s*(天|週|小時|分鐘|%|元|萬|人天)")
ARTIFACT_RE = re.compile(r"產物[:：]\s*(.*?)(?=產物[:：]|簽核[:：]|[;；\n]|$)")
SIGNER_RE = re.compile(r"簽核[:：]\s*(.*?)(?=產物[:：]|簽核[:：]|[;；\n]|$)")


def _has_value(pattern, text):
    return any(
        any(char.isalnum() for char in match.group(1))
        for match in pattern.finditer(text)
    )


def check_answer(kind, text):
    if not isinstance(text, str) or not text.strip():
        return ("未定", "答案為空")
    if kind in QUANTIFIED_KINDS:
        if QUANTITY_RE.search(text):
            return ("ok", "含可量化的數字與單位")
        return ("未定", "缺少可量化的數字與單位")
    if kind == "驗收標準":
        if _has_value(ARTIFACT_RE, text) and _has_value(SIGNER_RE, text):
            return ("ok", "同時載明產物與簽核")
        return ("未定", "驗收標準須同時載明產物與簽核")
    return ("未定", "未知的判準類型")
