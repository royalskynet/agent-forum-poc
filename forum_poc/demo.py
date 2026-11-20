import json
import os
import sys

from .misalign import find_misalignments
from .record import build_record, render
from .validate import validate_pair, validate_submission


def _load(root, name):
    path = os.path.join(root, "fixtures", f"{name}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    product = _load(root, "product")
    eng = _load(root, "eng")
    criteria = _load(root, "criteria")

    errors = []
    errors.extend(validate_submission(product))
    errors.extend(validate_submission(eng))
    errors.extend(validate_pair(product, eng))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    flags = find_misalignments(product, eng)
    rec = build_record(product, eng, flags, criteria)
    print(render(rec), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
