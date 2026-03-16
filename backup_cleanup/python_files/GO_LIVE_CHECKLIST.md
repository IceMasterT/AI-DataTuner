# Go-Live Checklist

Use this to take the pipeline to production safely.

## 1) Pick provider mode

- Cloud OpenAI:
  - `OPENAI_PROVIDER=openai`
  - `OPENAI_API_KEY=<real_key>`
- Cloud OpenRouter:
  - `OPENAI_PROVIDER=openrouter`
  - `OPENROUTER_API_KEY=<real_key>`
  - optional `OPENROUTER_BASE_URL`
- Local Ollama (no key):
  - `OPENAI_PROVIDER=ollama`
  - `OLLAMA_BASE_URL=http://127.0.0.1:11434/v1`
  - `OPENAI_MODEL=qwen2.5:7b` (or your model)
- Local LM Studio (no key):
  - `OPENAI_PROVIDER=lmstudio`
  - `LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1`
  - `OPENAI_MODEL=local-model`

## 2) Run strict production gate

```bash
cd "/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files"
PYTHON_BIN="/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files/venv/bin/python" ./run_pipeline.sh --health-only --smoke --strict
```

Expected: `HEALTH CHECK: PASS`

## 3) Launch production run

```bash
cd "/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files"
PYTHON_BIN="/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files/venv/bin/python" ./run_pipeline.sh
```

## 4) Verify output contracts

- Phase chain has outputs in:
  - `Phase 1`, `Phase 2`, `Phase 3`, `Phase 4`
- If using ChatGPT target (`openai` or `gpt_jsonl`):
  - check combined file exists in Phase 3, default:
    - `chatgpt_training.jsonl`
  - each line must be JSON with `messages` containing `user` and `assistant` roles.

## 5) Security confirmation

- No real keys in repo files.
- Keep keys in environment only.
- Rotate keys immediately if any were previously exposed.
