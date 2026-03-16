# iOS Launcher Setup

iOS cannot run this Python desktop app natively. Use a one-tap Shortcut that remotely triggers your Linux/Windows host.

## Option A: SSH Shortcut (Recommended)

1. In iOS **Shortcuts**, create a new shortcut.
2. Add action: **Run Script Over SSH**.
3. Host: your machine running AI Data Pipeline.
4. Script:

```bash
cd "/path/to/backup_cleanup/python_files" && ./run_pipeline.sh --health-only --smoke
```

5. Add to Home Screen and name it `AI Data Pipeline`.

## Option B: Web Trigger

If you expose a secure internal endpoint that executes the launcher, create an iOS Home Screen web shortcut to that endpoint.

Security note: use VPN/Tailscale + key auth, never expose raw SSH publicly.
