# Trial pack: run one real case through the forum harness

Purpose: get the one kind of evidence the synthetic fixtures cannot give. A real (anonymised) case, run by a real person, with a verdict on whether the questions were useful.

Time needed: about 30 minutes for two or more parties. Needs Python 3, nothing else. No network, no LLM.

## 1. Each party fills one file

Copy `examples/case_basic/product.json` as a starting point. One file per party, named after the party, in one new folder.

```json
{
  "party": "your-team-name",
  "items": {
    "<agenda item>": {
      "含": ["work items you include"],
      "不含": ["work items you explicitly exclude"],
      "假設": ["what you assume"],
      "估時_天": 5,
      "依賴": ["what you depend on"]
    }
  }
}
```

Rules the tool checks:
- Every party must list every agenda item (an empty list means no opinion).
- `估時_天` is a number above 0, or `null` if that party does not estimate this item.
- A work item cannot be in both `含` and `不含`.
- Submit before reading anyone else's file. The point is a blind first round.

Optional: add `criteria.json` (copy `examples/case_basic/criteria.json`) with the questions you want answered with a checkable number or a named artifact plus a sign-off.

## 2. Run

```
python3 -m forum_poc.run_case <your-folder>
```

Exit code 2 and one line on stderr mean the input is invalid. Nothing is printed on stdout in that case.

## 3. Charters (optional)

Add `charters.json`, `labels.json`, `commitments.json` as in `examples/case_full/` to hide confidential text and to check commitments against an owner-set cap. Withheld text is shown only as a count, so read the count as a sign to ask that owner directly.

## 4. Feedback (the part that matters)

For each question in the output, mark one:

| # | Question | Useful and new | Already known | Wrong or confusing | Missing question we needed |
|---|---|---|---|---|---|

Then answer, in one line each:
1. How long would the same alignment have taken in a meeting?
2. Which dispute did the tool miss?
3. Which question would you not have thought to ask?
4. Would you run it again on the next case, yes or no, and why?

Send the filled table back as is. Negative results are as useful as positive ones. Do not include confidential text in what you send back.
