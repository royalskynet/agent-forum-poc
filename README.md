# agent-forum-poc

A minimal proof of concept for one idea: before two parties' AI agents discuss a topic, force each side to submit a structured scope first, then mechanically detect where the two sides mean different things by the same words. Humans only answer the few questions that remain.

這是一個最小概念驗證：兩方的 AI agent 討論前，先各自交出結構化的範圍定義，再用程式比對雙方「同一個詞卻指不同範圍」的地方。人類只回答剩下的少數問題。

## What it does

Input: two JSON submissions (each lists, per agenda item, what is in scope, what is out, assumptions, estimated days, dependencies) and a list of answered "criteria questions".

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

## Run

Python 3, standard library only, no network, no LLM.

```
python3 -m unittest discover -s tests -t .
python3 -m forum_poc.demo
```

## Limits (read these)

- No LLM is involved. Extracting the structured fields from real documents, and generating the criteria questions, are the hard parts and are not implemented here.
- Two parties only. No identity, authorization, or prompt-injection handling. No forum UI.
- The estimate-ratio threshold is a parameter with no calibration data behind it.
- Tested only on the synthetic fixtures in `fixtures/`. Not validated on any real case.

See `DEVLOG.md` for how it was built and what was verified.

License: MIT
