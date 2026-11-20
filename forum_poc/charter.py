import copy

from .multi import LIST_FIELDS, build_agenda, render_agenda, validate_multi

LABELS = ("公開", "內部", "機密")
DEFAULT_LABEL = "內部"
FIELD_ORDER = {name: index for index, name in enumerate(LIST_FIELDS)}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _item_labels(item):
    labels = item.get("標籤") if isinstance(item, dict) else None
    return labels if isinstance(labels, dict) else {}


def attach_labels(sub, mapping):
    if not isinstance(sub, dict):
        raise ValueError("提交必須是 dict")
    if not isinstance(mapping, dict):
        raise ValueError("標籤對應必須是 dict")

    items = sub.get("items")
    if not isinstance(items, dict):
        raise ValueError("items 必須是 dict")

    out = copy.deepcopy(sub)
    for item_name, texts in mapping.items():
        if item_name not in items or not isinstance(items[item_name], dict):
            raise ValueError(f"議程項目不存在：{item_name}")
        if not isinstance(texts, dict):
            raise ValueError(f"{item_name}：標籤對應必須是 dict")

        item = items[item_name]
        known_texts = set()
        for field in LIST_FIELDS:
            values = item.get(field)
            if isinstance(values, list):
                known_texts.update(text for text in values if isinstance(text, str))
        for text, label in texts.items():
            if text not in known_texts:
                raise ValueError(f"{item_name}：文字不在任何欄位內：{text}")
            if label not in LABELS:
                raise ValueError(f"{item_name}：未知標籤：{label}")

        merged = dict(_item_labels(item))
        merged.update(texts)
        out["items"][item_name]["標籤"] = merged

    return out


def validate_charter(charter):
    if not isinstance(charter, dict):
        return ["授權書必須是 dict"]

    errors = []

    party = charter.get("party")
    if not isinstance(party, str) or not party:
        errors.append("party 必須是非空字串")

    if "可揭露" not in charter:
        errors.append("缺少欄位：可揭露")
    else:
        reveal = charter["可揭露"]
        if not isinstance(reveal, list):
            errors.append("可揭露 必須是 list")
        else:
            for label in reveal:
                if label not in LABELS:
                    errors.append(f"可揭露 含未知標籤：{label}")

    if "可承諾" not in charter:
        errors.append("缺少欄位：可承諾")
        caps = {}
    else:
        caps = charter["可承諾"]
        if not isinstance(caps, dict):
            errors.append("可承諾 必須是 dict")
            caps = {}
        else:
            for item_name, cap in caps.items():
                if not isinstance(cap, dict):
                    errors.append(f"可承諾／{item_name} 必須是 dict")
                    continue
                limit = cap.get("估時_天_上限")
                if not _is_number(limit) or limit <= 0:
                    errors.append(f"可承諾／{item_name}：估時_天_上限 必須是大於 0 的數字")

    if "禁止承諾" not in charter:
        errors.append("缺少欄位：禁止承諾")
        forbidden = []
    else:
        forbidden = charter["禁止承諾"]
        if not isinstance(forbidden, list):
            errors.append("禁止承諾 必須是 list")
            forbidden = []

    for item_name in forbidden:
        if item_name in caps:
            errors.append(f"議程項目不得同時可承諾與禁止承諾：{item_name}")

    return errors


def apply_charter(sub, charter):
    if not isinstance(sub, dict) or not isinstance(charter, dict):
        raise ValueError("提交與授權書必須是 dict")
    if sub.get("party") != charter.get("party"):
        raise ValueError(f"party 不符：{sub.get('party')} != {charter.get('party')}")

    reveal = charter.get("可揭露")
    allowed = {label for label in reveal if label in LABELS} if isinstance(reveal, list) else set()

    visible = copy.deepcopy(sub)
    items = sub.get("items") if isinstance(sub.get("items"), dict) else {}
    new_items = {}
    withheld = []

    for item_name, item in items.items():
        if not isinstance(item, dict):
            new_items[item_name] = copy.deepcopy(item)
            continue

        labels = _item_labels(item)
        new_item = copy.deepcopy(item)
        new_item.pop("標籤", None)

        for field in LIST_FIELDS:
            values = item.get(field)
            if not isinstance(values, list):
                new_item[field] = copy.deepcopy(values)
                continue
            kept = []
            for text in values:
                label = labels.get(text, DEFAULT_LABEL)
                if label in allowed:
                    kept.append(text)
                else:
                    withheld.append(
                        {"議程項目": item_name, "欄位": field, "標籤": label}
                    )
            new_item[field] = kept

        new_items[item_name] = new_item

    visible["items"] = new_items
    withheld.sort(
        key=lambda entry: (
            entry["議程項目"],
            FIELD_ORDER.get(entry["欄位"], len(FIELD_ORDER)),
            entry["標籤"],
        )
    )
    return visible, withheld


def check_commitment(charter, item_name, days):
    if not _is_number(days) or days <= 0:
        raise ValueError("天數必須是大於 0 的數字")

    if not isinstance(charter, dict):
        raise ValueError("授權書必須是 dict")

    forbidden = charter.get("禁止承諾")
    if isinstance(forbidden, list) and item_name in forbidden:
        return "禁止"

    caps = charter.get("可承諾")
    if isinstance(caps, dict) and item_name in caps:
        cap = caps[item_name]
        if isinstance(cap, dict):
            limit = cap.get("估時_天_上限")
            if _is_number(limit) and days <= limit:
                return "可承諾"

    return "須回問人"


def _commitment_question(entry):
    return (
        f"主人需確認：{entry['party']} 的 agent 想在「{entry['議程項目']}」"
        f"承諾 {entry['估時_天']} 天，超出授權書範圍，請回覆是否同意？"
    )


def build_chartered_agenda(subs, charters, answers, commitments):
    errors = validate_multi(subs)
    if errors:
        raise ValueError("；".join(errors))

    charter_by_party = {}
    for charter in charters:
        charter_errors = validate_charter(charter)
        if charter_errors:
            raise ValueError("；".join(charter_errors))
        if charter["party"] in charter_by_party:
            raise ValueError(f"同一 party 出現重複授權書：{charter['party']}")
        charter_by_party[charter["party"]] = charter

    parties = {sub["party"] for sub in subs}
    if set(charter_by_party) != parties:
        raise ValueError("授權書的 party 集合必須與提交完全一致")

    party_items = {}
    for sub in subs:
        party_items[sub["party"]] = set(sub.get("items", {}))

    checked = []
    for commitment in commitments:
        party = commitment.get("party")
        item_name = commitment.get("議程項目")
        days = commitment.get("估時_天")
        if party not in charter_by_party:
            raise ValueError(f"承諾的 party 不存在：{party}")
        if item_name not in party_items.get(party, set()):
            raise ValueError(f"承諾的議程項目不存在：{party}／{item_name}")
        if not _is_number(days) or days <= 0:
            raise ValueError(f"承諾天數不合法：{party}／{item_name}")
        result = check_commitment(charter_by_party[party], item_name, days)
        checked.append(
            {
                "party": party,
                "議程項目": item_name,
                "估時_天": days,
                "結果": result,
            }
        )
    checked.sort(key=lambda entry: (entry["party"], entry["議程項目"], entry["估時_天"]))

    visible_subs = []
    groups = {}
    for sub in subs:
        party = sub["party"]
        visible, withheld = apply_charter(sub, charter_by_party[party])
        visible_subs.append(visible)
        for entry in withheld:
            key = (party, entry["議程項目"], entry["欄位"], entry["標籤"])
            groups[key] = groups.get(key, 0) + 1

    redactions = [
        {
            "party": party,
            "議程項目": item_name,
            "欄位": field,
            "標籤": label,
            "數量": count,
        }
        for (party, item_name, field, label), count in groups.items()
    ]
    redactions.sort(
        key=lambda entry: (
            entry["party"],
            entry["議程項目"],
            FIELD_ORDER.get(entry["欄位"], len(FIELD_ORDER)),
            entry["標籤"],
        )
    )

    record = build_agenda(visible_subs, answers)

    questions = list(record["待答題"])
    for entry in checked:
        if entry["結果"] == "須回問人":
            questions.append(_commitment_question(entry))

    record["待答題"] = questions
    record["遮蔽"] = redactions
    record["承諾檢查"] = checked
    return record


def render_chartered(record):
    lines = render_agenda(record).rstrip("\n").split("\n")

    extra = ["遮蔽："]
    redactions = record.get("遮蔽") or []
    if redactions:
        for entry in redactions:
            extra.append(
                f"- {entry['party']}／{entry['議程項目']}／{entry['欄位']}"
                f"／{entry['標籤']}：{entry['數量']}"
            )
    else:
        extra.append("- 無")
    extra.append("")

    extra.append("承諾檢查：")
    checks = record.get("承諾檢查") or []
    if checks:
        for entry in checks:
            extra.append(
                f"- {entry['party']}／{entry['議程項目']}："
                f"{entry['估時_天']} 天 → {entry['結果']}"
            )
    else:
        extra.append("- 無")
    extra.append("")

    insert_at = len(lines)
    for index, line in enumerate(lines):
        if line.startswith("反方觸發："):
            insert_at = index
            break
    lines[insert_at:insert_at] = extra

    return "\n".join(lines) + "\n"
