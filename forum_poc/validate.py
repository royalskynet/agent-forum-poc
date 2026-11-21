import math

LIST_FIELDS = ("含", "不含", "假設", "依賴")


def _is_number(value):
    if isinstance(value, int):
        return not isinstance(value, bool)
    return isinstance(value, float) and math.isfinite(value)


def _validate_item(item):
    errors = []
    for field in LIST_FIELDS:
        if field not in item:
            errors.append(f"缺少欄位：{field}")
        elif not isinstance(item[field], list):
            errors.append(f"欄位型別錯誤（須為 list）：{field}")
    if "估時_天" not in item:
        errors.append("缺少欄位：估時_天")
    else:
        estimate = item["估時_天"]
        if not _is_number(estimate) or estimate <= 0:
            errors.append("估時_天 必須是大於 0 的數字")
    return errors


def validate_submission(sub):
    errors = []
    if not isinstance(sub, dict):
        return ["提交必須是 dict"]
    party = sub.get("party")
    if not isinstance(party, str) or not party:
        errors.append("party 必須是非空字串")
    items = sub.get("items")
    if not isinstance(items, dict) or not items:
        errors.append("items 必須是非空 dict")
        return errors
    for name, item in items.items():
        if not isinstance(item, dict):
            errors.append(f"議程項目必須是 dict：{name}")
            continue
        for error in _validate_item(item):
            errors.append(f"{name}：{error}")
    return errors


def validate_pair(a, b):
    errors = []
    pa = a.get("party") if isinstance(a, dict) else None
    pb = b.get("party") if isinstance(b, dict) else None
    if not pa or not pb or pa == pb:
        errors.append("雙方 party 必須不同")
    items_a = a.get("items", {}) if isinstance(a, dict) else {}
    items_b = b.get("items", {}) if isinstance(b, dict) else {}
    if not isinstance(items_a, dict):
        items_a = {}
    if not isinstance(items_b, dict):
        items_b = {}
    names_a = set(items_a)
    names_b = set(items_b)
    for name in sorted(names_a - names_b):
        errors.append(f"只有一方有的議程項目：{name}")
    for name in sorted(names_b - names_a):
        errors.append(f"只有一方有的議程項目：{name}")
    return errors
