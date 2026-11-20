import json
import os
import sys

from .charter import attach_labels, build_chartered_agenda, render_chartered

PARTIES = ("product", "eng", "compliance", "english")


def _load(root, *parts):
    path = os.path.join(root, "fixtures", *parts)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subs = [_load(root, "multi", f"{party}.json") for party in PARTIES]
    labels = _load(root, "charter", "labels.json")
    subs = [
        attach_labels(sub, labels[sub["party"]]) if sub["party"] in labels else sub
        for sub in subs
    ]
    charters = _load(root, "charter", "charters.json")
    commitments = _load(root, "charter", "commitments.json")
    answers = _load(root, "criteria.json")

    record = build_chartered_agenda(subs, charters, answers, commitments)
    print(render_chartered(record), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
