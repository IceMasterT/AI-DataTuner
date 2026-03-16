# Install AI Data Pipeline on iOS (Shortcut App)

iOS cannot run this Python desktop app natively. Use a one-tap iOS Shortcut to trigger your host machine.

1. Open iOS Shortcuts.
2. Add action: Run Script Over SSH.
3. Host: your Linux/Windows machine.
4. Script:

```bash
cd "/path/to/backup_cleanup/python_files" && ./go_live.sh --check-only
```

5. Add shortcut to Home Screen and choose icon/name.

You now have an app-like launcher on iOS.
