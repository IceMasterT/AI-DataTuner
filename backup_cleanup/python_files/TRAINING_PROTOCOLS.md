# Training Protocol Targets

This pipeline now supports per-model-family training protocol presets through Phase 3 setting `training_target`.

## Supported Targets

- `qwen`
  - Output format: `qwen`
  - Required markers: `<|user|>`, `<|assistant|>`
- `llama2`
  - Output format: `llama2`
  - Required markers: `[INST]`, `[/INST]`
- `alpaca`
  - Output format: `alpaca`
  - Required markers: `### Instruction:`, `### Response:`
- `chatml`
  - Output format: `chatml`
  - Required markers: `<|im_start|>`, `<|im_end|>`
- `sharegpt`
  - Output format: `sharegpt`
  - Required markers: `human`, `gpt`
- `openai`
  - Output format: `gpt_jsonl`
  - Required markers: `"messages"`, `"role": "user"`, `"role": "assistant"`
- `gpt_jsonl`
  - Output format: `gpt_jsonl`
  - Required markers: `"messages"`, `"role": "user"`, `"role": "assistant"`
- `claude`
  - Output format: `instruct`
  - Required markers: `Question:`, `Answer:`
- `mistral`
  - Output format: `chatml`
  - Required markers: `<|im_start|>`, `<|im_end|>`
- `gemma`
  - Output format: `alpaca`
  - Required markers: `### Instruction:`, `### Response:`

## Validation

- Enable strict protocol checking with `strict_role_validation: true`.
- Validation runs in Phase 3 before output files are written.
- If validation fails, that sample is marked failed and logged.

## ChatGPT Fine-Tuning Output

For `openai` or `gpt_jsonl` targets, output records use:

`{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}`

Optional Phase 3 settings:

- `emit_combined_jsonl` (`true`/`false`)
- `combined_jsonl_filename` (default: `chatgpt_training.jsonl`)

When enabled, Phase 3 writes a combined newline-delimited JSONL dataset file that is ready to upload for ChatGPT fine-tuning.

## Size Cap Stage (Phase 1)

Pipeline stage order for file controls:

1. Parse/extract input content
2. Clean/sanitize content
3. Apply size cap policy
4. Write output file(s)

Settings:

- `max_clean_file_size_mb` + `size_cap_unit` (`bytes` | `kb` | `mb` | `gb`)
- `size_cap_strategy` (`split` | `truncate` | `summarize` | `reject`)
- `on_cap_exceeded` (`warn` | `fail` | `quarantine`)
- `preserve_sentence_boundaries` (`true`/`false`)
- `compression_mode` (`none` | `minimal_whitespace`)
- `recursive_input_scan` (`true`/`false`)
- `min_clean_chars` (integer)
- `drop_empty_outputs` (`true`/`false`)

When a file is split or capped, a manifest file is written:

- `<source_stem>_size_cap_manifest.json`

Each emitted text file is kept at or under the configured cap.
