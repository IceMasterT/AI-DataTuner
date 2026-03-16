# AI Data Pipeline Operator Runbook

This is the day-to-day quick guide for running the pipeline safely.

## 1) Open and run

```bash
cd "/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files"
./go_live.sh --check-only
./go_live.sh
```

If `--check-only` fails, do not run production.

## 2) Pick provider mode

### Free local mode (recommended baseline)

```bash
export OPENAI_PROVIDER=ollama
export OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
export OPENAI_MODEL=qwen2.5:7b
```

### OpenAI cloud mode

```bash
export OPENAI_PROVIDER=openai
export OPENAI_API_KEY="<REAL_KEY>"
export OPENAI_MODEL=gpt-4o
```

### OpenRouter cloud mode

```bash
export OPENAI_PROVIDER=openrouter
export OPENROUTER_API_KEY="<REAL_KEY>"
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_MODEL=openrouter/auto
```

### LM Studio local mode

```bash
export OPENAI_PROVIDER=lmstudio
export LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
export OPENAI_MODEL=local-model
```

## 3) Input/output folders

Default chain:

- `input`
- `Phase 1`
- `Phase 2`
- `Phase 3`
- `Phase 4`

Do not manually bypass phases unless troubleshooting.

## 4) Common GUI workflow

1. Open app.
2. In **AI Settings**, choose provider preset.
3. In **Processing**, choose output format (use `GPT JSONL` for ChatGPT fine-tuning).
4. In **Phases**, verify all required phases enabled.
5. Start pipeline.

## 5) ChatGPT fine-tuning output

Use Phase 3 target `openai` or `gpt_jsonl`.

Expected record format:

```json
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

Combined dataset file (if enabled):

- `chatgpt_training.jsonl`

## 6) Health checks only

```bash
./run_pipeline.sh --health-only --smoke
./run_pipeline.sh --health-only --smoke --strict
```

- `--strict` is required for production gate.

## 7) Failure response

- If strict check fails on creds:
  - verify provider env vars and real keys.
- If strict check fails on deps:
  - run `python3 setup.py --install-type full --yes` in `backup_cleanup/python_files`.
- If local provider fails:
  - confirm Ollama/LM Studio process is running and endpoint is reachable.

## 8) Security rules

- Never place real keys in tracked files.
- Use environment variables only.
- Rotate keys immediately if accidentally exposed.

## 9) Launcher shortcuts

Interactive launcher installer (asks desktop/menu options):

```bash
cd "/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files"
python3 install_app.py
```

- Linux desktop icon: `~/Desktop/AI Data Pipeline.desktop`
- Linux command: `~/.local/bin/ai-data-pipeline-launcher`
- Windows scripts: `backup_cleanup/python_files/run_pipeline.bat`
- iOS shortcut guide: `backup_cleanup/python_files/launchers/ios/IOS_LAUNCHER_SETUP.md`
