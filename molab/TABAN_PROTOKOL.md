# Untrained Qwen3-8B baseline: pre-registered protocol

Written 2026-10-18, before any baseline output was generated. The goal is one number that answers
"how much of v6 comes from fine-tuning?" under the same conditions as the v6 final evaluation.

## Fixed before the run

| Item | Value |
|---|---|
| Checkpoint | `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218` (the `base_model_name_or_path` of every v6 adapter; `main` has not changed since 2025-07-26, before the v6 run) |
| Adapter | none |
| Inputs | `test_sabit.jsonl` (2,000 rows, sha256 `4ad04cd5…fcc586`) and `eval115.jsonl` (115 rows, sha256 `e9fa2f57…922b12`) from `krxi/asmsense-data` release `v6` (`veri-v6.zip`), the same files v6 was scored on |
| Prompt | the first two messages of each row (system + user) unchanged: same system prompt, assembly, call context and Ghidra pseudocode; no few-shot, no prompt edits |
| Template | `tokenizer.apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)` |
| Decoding | greedy (`do_sample=False`), `max_new_tokens=160`, `use_cache=True`, batch size 1 |
| Precision | bf16, SDPA attention, one GPU |
| Hardware | molab, the environment of the v6 final evaluation (RTX PRO 6000 96 GB); any difference is reported |
| Packages | `transformers==5.3.0` and the rest of the `molab/egit.py` dependency header; the run log records the versions actually loaded |
| Notebook | `molab/taban.py` |

## Scoring

- **Primary score:** exactly the v6 pipeline. `ad_ayikla` (`lora/cikti.py`) parses the output, then name-token
  F1, prefix-stripped F1, F1 = 1 counts and literal exact matches are computed with the same code that
  produced the published v6 numbers (`olcum_v6.py`, `iki_f1.py`). `ad_ayikla` falls back to a partial
  JSON field or the first identifier when the output is not valid JSON; v6 was scored the same way.
- **Secondary (strict) score:** the same, but any row whose output is not valid JSON
  (`gecerli_json = false`) counts as F1 = 0.
- **Reported separately:** invalid-JSON rate, and the share of rows that hit the 160-token limit.
- **Paired differences:** v6 − baseline and v1 − baseline on ID-aligned rows, project-cluster percentile
  bootstrap, 2,000 draws, seed 42, as in `olcum_v6.py`.

Whatever the result, it is published as is, including any metric where the baseline beats v6.
