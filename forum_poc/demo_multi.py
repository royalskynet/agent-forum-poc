import json
import os
import sys

from .multi import build_agenda, render_agenda, validate_multi

PARTIES = ("product", "eng", "compliance", "english")


def _load(root, *parts):
    path = os.path.join(root, "fixtures", *parts)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subs = [_load(root, "multi", f"{party}.json") for party in PARTIES]
    answers = _load(root, "criteria.json")

    errors = validate_multi(subs)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    rec = build_agenda(subs, answers)
    print(render_agenda(rec), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
