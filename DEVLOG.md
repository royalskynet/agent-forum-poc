# Dev log (all dates Asia/Taipei, 2026-11-20)

## What was built
A deterministic core: submission validation, scope-mismatch and estimate-divergence detection, criteria-answer checking, a convergence check that decides when to inject a devil's-advocate round, and a decision-record renderer. Standard library only.

## Process
1. Wrote and ran the mismatch detector first against two synthetic fixtures (a product side and an engineering side of a feature-scheduling dispute). Result: 2 tests OK.
2. Mutation check of that first version: replacing the detector's membership test with a constant made the tests fail (`FAILED (failures=1)`, exit code 1).
3. Reviewed the design before extending it and fixed three problems in the plan:
   - A planned similarity threshold for "too fast agreement" was a dead parameter: when there are zero mismatch flags the two sides' in-scope sets are identical, so similarity is always 1. The trigger became "zero flags across all agenda items".
   - An agenda item submitted by only one side was silently skipped by the set intersection. It is now rejected in validation.
   - An estimate of 0 would divide by zero. It is now rejected in validation.
4. The supervising session (an AI coding agent) wrote all tests and fixtures first and recorded their SHA-256 hashes. At that point the suite was red (the new modules did not exist yet).
5. Dispatched implementation to a low-cost LLM executor through a job queue, in two work orders (validation, criteria and convergence; then record and demo). Each order's acceptance command checked that the test and fixture hashes were unchanged and that the tests pass.
6. The supervising session reviewed each diff and re-ran the acceptance command itself instead of trusting the executor's self-report.

## Raw results
After order 1 (26 tests): `Ran 26 tests ... OK`.
After order 2 (full suite): `Ran 35 tests in 0.018s` then `OK`. Test and fixture hashes: 0 mismatches. `python3 -m forum_poc.demo` exits 0 and prints a record with three flags (two scope mismatches, one estimate divergence), one undecided criteria answer, and devil's-advocate trigger "no".

## Mutation checks
Each mutant was run against the full suite or the relevant test modules, with an unmutated control that exited 0.

| Mutation | Result |
|---|---|
| estimate check `<= 0` weakened to `< 0` | tests fail |
| acceptance rule `and` changed to `or` | tests fail |
| convergence check always true | tests fail |
| one-sided agenda item check removed | tests fail |
| record keeps only the first flag | tests fail |
| consensus list ignores flags | tests fail |
| renderer drops the flag content line | tests fail |
| devil's-advocate trigger forced true | tests fail |
| demo reads a wrong fixtures folder | tests fail |

Two mistakes worth recording, both in the mutation harness, not in the code under test:
- First run: no unmutated control, and the full suite was red anyway because the record and demo modules did not exist yet. Every mutant "failed", which proved nothing.
- Second run: restricted to the relevant test modules and added a control, but the control also failed. The shell script passed the module list as one word (zsh does not word-split unquoted variables), so it never ran the tests I meant.
- Third run: module list expanded properly. The control exited 0 and every mutant exited 1, giving the table above. A red result only counts when the control is green.

## Not proven
- Nothing here uses an LLM. Whether an agent can extract the structured fields from real documents, or generate the criteria questions, is untested.
- The estimate-ratio threshold (2.0) has no calibration data.
- Only synthetic fixtures were used. No real case was run.
- Two parties only. No authorization, identity, or prompt-injection handling.
