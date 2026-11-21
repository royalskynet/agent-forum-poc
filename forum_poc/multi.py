from .convergence import should_inject_devil
from .criteria import check_answer
from .misalign import PHI
from .validate import LIST_FIELDS, _is_number


def _party_label(sub, index):
    if isinstance(sub, dict):
        party = sub.get("party")
        if isinstance(party, str) and party:
            return party
    return f"第 {index + 1} 方"


def validate_multi(subs):
    errors = []
    if not isinstance(subs, list):
        return ["subs 必須是 list"]
    if len(subs) < 2:
        errors.append("至少需要兩個 party")

    parties = []
    seen = set()
    valid_items = []
    for index, sub in enumerate(subs):
        label = _party_label(sub, index)
        if not isinstance(sub, dict):
            errors.append(f"{label}：提交必須是 dict")
            continue

        party = sub.get("party")
        if not isinstance(party, str) or not party:
            errors.append(f"{label}：party 必須是非空字串")
        else:
            if party in seen:
                errors.append(f"party 重複：{party}")
            seen.add(party)
            parties.append(party)

        items = sub.get("items")
        if not isinstance(items, dict) or not items:
            errors.append(f"{label}：items 必須是非空 dict")
            valid_items.append((label, None))
            continue

        valid_items.append((label, items))
        for name, item in items.items():
            if not isinstance(item, dict):
                errors.append(f"{label}／{name}：議程項目必須是 dict")
                continue
            for field in LIST_FIELDS:
                if field not in item:
                    errors.append(f"{label}／{name}：缺少欄位：{field}")
                elif not isinstance(item[field], list):
                    errors.append(f"{label}／{name}：欄位型別錯誤（須為 list）：{field}")
            if "估時_天" not in item:
                errors.append(f"{label}／{name}：缺少欄位：估時_天")
            else:
                estimate = item["估時_天"]
                if estimate is not None:
                    if not _is_number(estimate) or estimate <= 0:
                        errors.append(f"{label}／{name}：估時_天 必須是 None 或大於 0 的數字")
            inc = item.get("含")
            exc = item.get("不含")
            if isinstance(inc, list) and isinstance(exc, list):
                for work in inc:
                    if work in exc:
                        errors.append(f"{label}／{name}：工作項同時在含與不含：{work}")

    all_names = set()
    for _label, items in valid_items:
        if isinstance(items, dict):
            all_names.update(items)
    for label, items in valid_items:
        present = set(items) if isinstance(items, dict) else set()
        for name in sorted(all_names - present):
            errors.append(f"{label} 缺少議程項目：{name}")

    return errors


def _item_names(subs):
    names = set()
    for sub in subs:
        if not isinstance(sub, dict):
            continue
        items = sub.get("items")
        if isinstance(items, dict):
            names.update(items)
    return names


def _item_by_party(subs, name):
    found = {}
    for sub in subs:
        if not isinstance(sub, dict):
            continue
        items = sub.get("items")
        if isinstance(items, dict) and isinstance(items.get(name), dict):
            party = sub.get("party")
            if isinstance(party, str):
                found[party] = items[name]
    return found


def find_disputes(subs, phi=PHI):
    disputes = []
    for name in sorted(_item_names(subs)):
        by_party = _item_by_party(subs, name)

        work_items = set()
        for item in by_party.values():
            inc = item.get("含")
            if isinstance(inc, list):
                work_items.update(inc)

        total = len(by_party)
        for work in sorted(work_items):
            stances = {}
            included = 0
            for party, item in by_party.items():
                inc = item.get("含") if isinstance(item.get("含"), list) else []
                exc = item.get("不含") if isinstance(item.get("不含"), list) else []
                if work in inc:
                    stances[party] = "含"
                    included += 1
                elif work in exc:
                    stances[party] = "明確排除"
                else:
                    stances[party] = "未提及"
            if included >= 1 and included < total:
                disputes.append(
                    {"種類": "範圍錯位", "議程項目": name, "內容": work, "立場": stances}
                )

        estimates = {}
        for party, item in by_party.items():
            value = item.get("估時_天")
            if value is not None:
                estimates[party] = value
        if len(estimates) >= 2:
            lo = min(estimates.values())
            hi = max(estimates.values())
            if lo > 0 and hi / lo > phi:
                disputes.append(
                    {
                        "種類": "估時分歧",
                        "議程項目": name,
                        "內容": f"{lo}天 vs {hi}天",
                        "立場": estimates,
                    }
                )

    disputes.sort(key=lambda d: (d["議程項目"], d["種類"], d["內容"]))
    return disputes


def _scope_question(dispute):
    groups = {}
    for party, stance in dispute["立場"].items():
        groups.setdefault(stance, []).append(party)
    parts = []
    for stance in ("含", "明確排除", "未提及"):
        if stance in groups:
            names = "、".join(sorted(groups[stance]))
            parts.append(f"{stance}：{names}")
    detail = "；".join(parts)
    return (
        f"議程項目「{dispute['議程項目']}」的工作項「{dispute['內容']}」範圍不一致"
        f"（{detail}），請確認是否納入？"
    )


def _estimate_question(dispute):
    detail = "、".join(
        f"{party}={value}" for party, value in sorted(dispute["立場"].items())
    )
    return (
        f"議程項目「{dispute['議程項目']}」的估時分歧為 {dispute['內容']}"
        f"（{detail}），請確認以哪個口徑為準？"
    )


def _dispute_question(dispute):
    if dispute["種類"] == "估時分歧":
        return _estimate_question(dispute)
    return _scope_question(dispute)


def _criterion_question(criterion):
    return (
        f"判準未定：「{criterion['題']}」（{criterion['類型']}）"
        f"目前答案「{criterion['答']}」無法判定，請補充可驗證的答案。"
    )


def _parties(subs):
    names = set()
    for sub in subs:
        if isinstance(sub, dict):
            party = sub.get("party")
            if isinstance(party, str) and party:
                names.add(party)
    return sorted(names)


def build_agenda(subs, answers, phi=PHI):
    disputes = find_disputes(subs, phi)
    flagged = {d["議程項目"] for d in disputes}
    consensus = sorted(_item_names(subs) - flagged)

    criteria = []
    for entry in answers:
        status, reason = check_answer(entry["類型"], entry["答"])
        criteria.append(
            {
                "題": entry["題"],
                "類型": entry["類型"],
                "答": entry["答"],
                "狀態": status,
                "原因": reason,
            }
        )

    questions = [_dispute_question(d) for d in disputes]
    for criterion in criteria:
        if criterion["狀態"] == "未定":
            questions.append(_criterion_question(criterion))

    return {
        "共識項": consensus,
        "爭議": disputes,
        "判準": criteria,
        "待答題": questions,
        "反方觸發": should_inject_devil(disputes),
        "各方": _parties(subs),
    }


def _parties_for_render(rec):
    parties = rec.get("各方")
    if isinstance(parties, list) and parties:
        return sorted(parties)
    names = set()
    for dispute in rec.get("爭議", []):
        stances = dispute.get("立場")
        if isinstance(stances, dict):
            names.update(stances)
    return sorted(names)


def render_agenda(rec):
    lines = ["多方議會比對", ""]

    parties = _parties_for_render(rec)
    if parties:
        lines.append(f"各方：{'、'.join(parties)}")
        lines.append("")

    lines.append("爭議：")
    disputes = rec.get("爭議", [])
    if disputes:
        for dispute in disputes:
            lines.append(f"- 種類：{dispute['種類']}")
            lines.append(f"  議程項目：{dispute['議程項目']}")
            lines.append(f"  內容：{dispute['內容']}")
            lines.append("  立場：")
            for party in sorted(dispute["立場"]):
                lines.append(f"    {party}：{dispute['立場'][party]}")
    else:
        lines.append("- 無")
    lines.append("")

    lines.append("共識項：")
    if rec.get("共識項"):
        for name in rec["共識項"]:
            lines.append(f"- {name}")
    else:
        lines.append("- 無")
    lines.append("")

    lines.append("判準：")
    if rec.get("判準"):
        for criterion in rec["判準"]:
            lines.append(f"- 題：{criterion['題']}")
            lines.append(f"  類型：{criterion['類型']}")
            lines.append(f"  答：{criterion['答']}")
            lines.append(f"  狀態：{criterion['狀態']}")
            lines.append(f"  原因：{criterion['原因']}")
    else:
        lines.append("- 無")
    lines.append("")

    lines.append("待答題：")
    if rec.get("待答題"):
        for index, question in enumerate(rec["待答題"], 1):
            lines.append(f"{index}. {question}")
    else:
        lines.append("- 無")
    lines.append("")

    lines.append(f"待答題總數：{len(rec.get('待答題', []))}")
    lines.append("")

    lines.append(f"反方觸發：{'是' if rec.get('反方觸發') else '否'}")

    return "\n".join(lines) + "\n"
