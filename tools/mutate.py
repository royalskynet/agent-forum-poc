"""Mutation check with a green control. Run from the repo root: python3 tools/mutate.py

Each mutant changes one line in a temporary copy of the repo and re-runs the full test suite.
A mutant is killed when the suite fails. The control (no change) must pass first.
Exit 0 only if the control passes and every mutant not marked equivalent is killed.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (name, file, old, new, equivalent). A mutant marked equivalent changes no observable behavior.
MUTANTS = [
    ("multi M1 explicit-out labelled not-mentioned", "forum_poc/multi.py", 'stances[party] = "明確排除"', 'stances[party] = "未提及"', False),
    ("multi M2 null estimate not filtered", "forum_poc/multi.py", "if value is not None:", "if True:", False),
    ("multi M3 dispute sort removed", "forum_poc/multi.py", 'disputes.sort(key=lambda d: (d["議程項目"], d["種類"], d["內容"]))', "pass", False),
    ("multi M4 devil trigger inverted", "forum_poc/multi.py", '"反方觸發": should_inject_devil(disputes)', '"反方觸發": not should_inject_devil(disputes)', False),
    ("multi M5 estimate threshold x100", "forum_poc/multi.py", "hi / lo > phi:", "hi / lo > phi * 100:", False),
    ("multi M6 undecided criteria not asked", "forum_poc/multi.py", 'if criterion["狀態"] == "未定":', "if False:", False),
    ("multi M7 stance output unsorted", "forum_poc/multi.py", 'for party in sorted(dispute["立場"]):', 'for party in dispute["立場"]:', False),
    ("multi M8 any include counts as dispute", "forum_poc/multi.py", "included >= 1 and included < total", "included >= 1", False),
    ("multi M9 missing agenda item not reported", "forum_poc/multi.py", "for name in sorted(all_names - present):", "for name in []:", False),
    ("charter M1 default label public", "forum_poc/charter.py", 'DEFAULT_LABEL = "內部"', 'DEFAULT_LABEL = "公開"', False),
    ("charter M2 unknown label let through", "forum_poc/charter.py", "if label in allowed:", "if label in allowed or label not in LABELS:", False),
    ("charter M3 cap compare <= to <", "forum_poc/charter.py", "days <= limit", "days < limit", False),
    ("charter M4 forbidden check removed", "forum_poc/charter.py", "if isinstance(forbidden, list) and item_name in forbidden:", "if False:", False),
    ("charter M5 over-cap allowed", "forum_poc/charter.py", "if _is_number(limit) and days <= limit:", "if _is_number(limit):", False),
    ("charter M6 forbidden also asks owner", "forum_poc/charter.py", 'if entry["結果"] == "須回問人":', 'if entry["結果"] != "可承諾":', False),
    ("charter M8 label map kept in output", "forum_poc/charter.py", 'new_item.pop("標籤", None)', "pass", False),
    ("charter M9 redaction list unsorted", "forum_poc/charter.py", "    redactions.sort(", "    (lambda **k: None)(", False),
    ("charter M10 commitment list unsorted", "forum_poc/charter.py", "checked.sort(key=", "(lambda key: None)(key=", False),
    ("charter M11 charter party set unchecked", "forum_poc/charter.py", "if set(charter_by_party) != parties:", "if False:", False),
    ("charter M12 attach skips text existence", "forum_poc/charter.py", "if text not in known_texts:", "if False:", False),
    ("charter M13 attach overwrites not merges", "forum_poc/charter.py", "merged = dict(_item_labels(item))", "merged = {}", False),
    ("charter M14 redaction count always 1", "forum_poc/charter.py", "groups[key] = groups.get(key, 0) + 1", "groups[key] = 1", False),
    ("charter M15 build skips day check", "forum_poc/charter.py", 'if not _is_number(days) or days <= 0:\n            raise ValueError(f"承諾天數不合法', 'if False:\n            raise ValueError(f"承諾天數不合法', True),
    ("charter M16 allowed+forbidden overlap unchecked", "forum_poc/charter.py", "if item_name in caps:\n            errors.append(f\"議程項目不得", "if False:\n            errors.append(f\"議程項目不得", False),
    ("charter M17 duplicate charter accepted", "forum_poc/charter.py", "if charter[\"party\"] in charter_by_party:", "if False:", False),
    ("run_case labels not-dict ignored", "forum_poc/run_case.py", "if not isinstance(labels, dict):", "if False:", False),
    ("run_case unknown label party ignored", "forum_poc/run_case.py", "if unknown:", "if False:", False),
    ("run_case unknown top-level key accepted", "forum_poc/run_case.py", "for key in sorted(str(k) for k in sub if k not in TOP_KEYS):", "for key in []:", False),
    ("run_case unknown item key accepted", "forum_poc/run_case.py", "for key in sorted(str(k) for k in item if k not in ITEM_KEYS):", "for key in []:", False),
    ("run_case reserved name other case accepted", "forum_poc/run_case.py", "if name.lower() in RESERVED and name not in RESERVED:", "if False:", False),
    ("run_case non-list criteria accepted", "forum_poc/run_case.py", "if not isinstance(data, list):", "if False:", False),
    ("run_case duplicate keys accepted", "forum_poc/run_case.py", "        if key in seen:", "        if False:", False),
]


def run_suite(workdir):
    r = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=workdir,
        capture_output=True,
        text=True,
    )
    return r.returncode


def fresh_copy():
    work = tempfile.mkdtemp(prefix="mut-")
    shutil.rmtree(work)
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "task", "__pycache__"))
    return work


def main():
    work = fresh_copy()
    control = run_suite(work)
    shutil.rmtree(work, ignore_errors=True)
    print(f"control rc={control}")
    if control != 0:
        print("control failed: the suite is red before any mutation, results would mean nothing")
        return 1

    survivors = []
    skipped = []
    for name, rel, old, new, equivalent in MUTANTS:
        work = fresh_copy()
        path = os.path.join(work, rel)
        with open(path, encoding="utf-8") as f:
            source = f.read()
        if source.count(old) != 1:
            skipped.append(name)
            print(f"SKIPPED  {name} (pattern found {source.count(old)} times)")
            shutil.rmtree(work, ignore_errors=True)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(source.replace(old, new, 1))
        rc = run_suite(work)
        shutil.rmtree(work, ignore_errors=True)
        if rc != 0:
            print(f"KILLED   {name}")
        else:
            tag = "SURVIVED (marked equivalent)" if equivalent else "SURVIVED"
            print(f"{tag}  {name}")
            if not equivalent:
                survivors.append(name)

    total = len(MUTANTS)
    print(f"{total} mutants, {len(survivors)} unexpected survivors, {len(skipped)} skipped")
    return 1 if survivors or skipped else 0


if __name__ == "__main__":
    sys.exit(main())
