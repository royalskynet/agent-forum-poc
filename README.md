# agent-forum-poc

A minimal proof of concept for one idea: before two or more parties' AI agents discuss a topic, force each side to submit a structured scope first, then mechanically detect where the two sides mean different things by the same words. Humans only answer the few questions that remain.

這是一個最小概念驗證：兩方以上的 AI agent 討論前，先各自交出結構化的範圍定義，再用程式比對雙方「同一個詞卻指不同範圍」的地方。人類只回答剩下的少數問題。

## What it does

Two-party mode. Input: two JSON submissions (each lists, per agenda item, what is in scope, what is out, assumptions, estimated days, dependencies) and a list of answered "criteria questions".

Output: a one-page decision record with
- scope mismatches (a work item one side includes and the other excludes or never mentions)
- estimate divergences (ratio above a threshold, default 2.0)
- criteria answers marked `ok` or `未定` (undecided)
- whether a devil's-advocate round should be triggered
- agenda items with no flags (consensus)

Rules, all deterministic and covered by tests:
- Submissions are validated first: missing fields, non-positive estimates, an agenda item present on only one side, or identical party names are rejected.
- A criteria answer counts only if it is a number with a unit (deadline, budget) or names both an artifact and a sign-off person (acceptance). Answers like "asap" stay undecided.
- A devil's-advocate round is triggered only when there are zero flags across all agenda items (suspiciously fast agreement). If any flag exists, there is already disagreement to discuss.

## Multi-party mode

`forum_poc/multi.py` generalizes the comparison to any number of parties (two or more). It aggregates by agenda item and work item, so one contested work item becomes one dispute with a per-party stance (in scope / explicitly out / not mentioned), instead of one flag per pair of parties. On the synthetic four-party fixture in `fixtures/multi/` (product, engineering, compliance, an English-language team) the pairwise function produces 13 directed scope flags (counted after replacing the null estimates with 1, because the two-party function cannot take null), while the multi-party view shows 4 scope disputes plus 1 estimate dispute.

The output ends with a list of questions for humans: one per dispute, plus one per undecided criteria answer, with a total count. The questions are filled from fixed templates. No LLM writes them.

An estimate may be `null` (that party does not estimate that item). Estimates are compared only among parties that gave one, because a review-days figure and a build-days figure are not comparable.

## Authorization charters

`forum_poc/charter.py` adds a per-party charter set by the human owner: which label levels (public / internal / confidential) may be disclosed to the forum, which agenda items the agent may commit to (with a day cap), and which it may never commit to. Texts carry a label; unlabelled text counts as internal and an unknown label is withheld (fail closed). Withheld text never enters the record or the rendered output; only counts per (party, item, field, label) are shown. A commitment over its cap or outside the listed items becomes a question for the owner ("主人需確認"); a forbidden item is flagged and asks nothing.

Design trade-off: redaction can make a real scope disagreement vanish from the agenda. On the fixture, compliance's confidential "privacy consent" item is withheld, so the multi-party view shows 4 disputes instead of 5, and the count of withheld texts is the only trace. Whoever reads the agenda must treat the withheld count as a signal to ask that owner directly.

Run it with `python3 -m forum_poc.demo_charter`.

## Run your own case

`python3 -m forum_poc.run_case <folder>` reads one JSON file per party from any folder (two or more parties), plus optional `criteria.json`, and prints the agenda. Add `charters.json` (and optionally `labels.json`, `commitments.json`) to turn on charters. Invalid input exits 2 with one line on stderr and nothing on stdout. Examples are in `examples/`. `TRIAL.md` is a 30-minute trial pack with a feedback table: it exists to collect the one kind of evidence the synthetic fixtures cannot give.

`python3 tools/mutate.py` re-runs the mutation check (32 hand-written mutants, a green control first). It exits 0 only if the control passes and every mutant not marked equivalent is killed.

## Run

Python 3, standard library only, no network, no LLM.

```
python3 -m unittest discover -s tests -t .
python3 -m forum_poc.demo
python3 -m forum_poc.demo_multi
python3 -m forum_poc.demo_charter
python3 -m forum_poc.run_case examples/case_full
python3 tools/mutate.py
```

## Limits (read these)

- No LLM is involved. Extracting the structured fields from real documents, and generating the criteria questions, are the hard parts and are not implemented here.
- The multi-party module covers comparison only: no identity and no forum UI. The charter module is rule-based and deterministic: labels are supplied by hand, not detected, and a charter is trusted as given (nothing proves it came from the owner). Labels apply only to texts inside the in-scope, out-of-scope, assumption and dependency lists. Agenda item names, party names and the criteria answers are printed as given and cannot be hidden. A label applies to one agenda item only: the same text in another item must be labelled there too. Prompt-injection handling (treating other agents' posts as untrusted input) is not implemented.
- Estimates, commitments and charter caps must be finite positive numbers. Multi-party estimates may also be `null`.
- The estimate-ratio threshold is a parameter with no calibration data behind it.
- Tested only on the synthetic fixtures in `fixtures/`. Not validated on any real case.

See `DEVLOG.md` for how it was built and what was verified.

License: MIT
