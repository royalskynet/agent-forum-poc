import json
import os
import sys

from .charter import attach_labels, build_chartered_agenda, render_chartered
from .multi import build_agenda, render_agenda, validate_multi

RESERVED = ("criteria.json", "charters.json", "labels.json", "commitments.json")


def _no_duplicate_keys(pairs):
    seen = set()
    for key, _value in pairs:
        if key in seen:
            raise ValueError(f"重複的鍵：{key}")
        seen.add(key)
    return dict(pairs)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f, object_pairs_hook=_no_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{os.path.basename(path)} 不是合法 JSON：{exc}") from exc
    except ValueError as exc:
        raise ValueError(f"{os.path.basename(path)}：{exc}") from exc


def _read_list(path):
    data = _read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"{os.path.basename(path)} 必須是 list")
    return data


TOP_KEYS = ("party", "items")
ITEM_KEYS = ("含", "不含", "假設", "估時_天", "依賴")


def _check_submission_keys(names, subs):
    for name, sub in zip(names, subs):
        if not isinstance(sub, dict):
            continue
        for key in sorted(str(k) for k in sub if k not in TOP_KEYS):
            raise ValueError(
                f"{name}：不認得的頂層欄位「{key}」（只准 party、items）；標籤請改用 labels.json（需搭配 charters.json）"
            )
        items = sub.get("items")
        if not isinstance(items, dict):
            continue
        for item_name, item in items.items():
            if not isinstance(item, dict):
                continue
            for key in sorted(str(k) for k in item if k not in ITEM_KEYS):
                raise ValueError(
                    f"{name}／{item_name}：不認得的欄位「{key}」（只准 含、不含、假設、估時_天、依賴）；標籤請改用 labels.json（需搭配 charters.json）"
                )


def _submission_files(directory):
    names = sorted(os.listdir(directory))
    for name in names:
        if name.lower() in RESERVED and name not in RESERVED:
            raise ValueError(f"保留檔名大小寫不符：{name}（應為 {name.lower()}）")
    return [
        name
        for name in names
        if name.endswith(".json")
        and name not in RESERVED
        and os.path.isfile(os.path.join(directory, name))
    ]


def run(directory):
    if not os.path.isdir(directory):
        raise ValueError(f"目錄不存在：{directory}")

    names = _submission_files(directory)
    subs = [_read_json(os.path.join(directory, name)) for name in names]
    _check_submission_keys(names, subs)
    if not subs:
        raise ValueError(f"目錄內沒有提交檔：{directory}")

    criteria_path = os.path.join(directory, "criteria.json")
    answers = _read_list(criteria_path) if os.path.exists(criteria_path) else []

    charters_path = os.path.join(directory, "charters.json")
    labels_path = os.path.join(directory, "labels.json")
    commitments_path = os.path.join(directory, "commitments.json")

    if os.path.exists(charters_path):
        labels = _read_json(labels_path) if os.path.exists(labels_path) else {}
        if not isinstance(labels, dict):
            raise ValueError("labels.json 必須是 dict（party → 議程項目 → 文字 → 標籤）")
        known = {sub.get("party") for sub in subs if isinstance(sub, dict)}
        unknown = sorted(str(party) for party in labels if party not in known)
        if unknown:
            raise ValueError("labels.json 含沒有對應提交的 party：" + "、".join(unknown))
        with_labels = []
        for sub in subs:
            party = sub.get("party") if isinstance(sub, dict) else None
            if party in labels:
                with_labels.append(attach_labels(sub, labels[party]))
            else:
                with_labels.append(sub)
        subs = with_labels
        charters = _read_json(charters_path)
        commitments = (
            _read_list(commitments_path) if os.path.exists(commitments_path) else []
        )
        return render_chartered(build_chartered_agenda(subs, charters, answers, commitments))

    for path in (labels_path, commitments_path):
        if os.path.exists(path):
            raise ValueError(
                f"{os.path.basename(path)} 需要搭配 charters.json 才能使用"
            )

    errors = validate_multi(subs)
    if errors:
        raise ValueError("；".join(errors))

    return render_agenda(build_agenda(subs, answers))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.stderr.write("用法：python3 -m forum_poc.run_case <目錄>\n")
        return 2

    try:
        output = run(argv[0])
    except Exception as exc:
        detail = str(exc) or exc.__class__.__name__
        sys.stderr.write(detail.replace("\n", " ") + "\n")
        return 2

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
