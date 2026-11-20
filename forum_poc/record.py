from .convergence import should_inject_devil
from .criteria import check_answer


def build_record(a, b, flags, answers):
    flagged_items = {f[1] for f in flags}
    common = sorted(set(a["items"]) & set(b["items"]))
    consensus = [name for name in common if name not in flagged_items]

    divergences = []
    for f in flags:
        divergences.append(
            {
                "種類": f[0],
                "議程項目": f[1],
                "內容": f[2],
                "細節": list(f[3:]),
            }
        )

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

    return {
        "共識項": consensus,
        "分歧": divergences,
        "判準": criteria,
        "反方觸發": should_inject_devil(flags),
    }


def render(rec):
    lines = ["決議記錄", ""]

    lines.append("分歧：")
    if rec["分歧"]:
        for d in rec["分歧"]:
            lines.append(f"- 種類：{d['種類']}")
            lines.append(f"  議程項目：{d['議程項目']}")
            lines.append(f"  內容：{d['內容']}")
    else:
        lines.append("- 無")
    lines.append("")

    lines.append("判準：")
    if rec["判準"]:
        for c in rec["判準"]:
            lines.append(f"- 題：{c['題']}")
            lines.append(f"  答：{c['答']}")
            lines.append(f"  狀態：{c['狀態']}")
    else:
        lines.append("- 無")
    lines.append("")

    lines.append(f"反方觸發：{'是' if rec['反方觸發'] else '否'}")
    lines.append("")

    lines.append("共識項：")
    if rec["共識項"]:
        for name in rec["共識項"]:
            lines.append(f"- {name}")
    else:
        lines.append("- 無")

    return "\n".join(lines) + "\n"
