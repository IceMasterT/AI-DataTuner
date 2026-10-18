# Install AI Data Pipeline on iPhone / iPad

iOS cannot run the desktop app, so this installs a **Home Screen app** that remotely controls the
computer running the pipeline: upload documents, start a run, watch the log, download the results.

## 1. Start the remote on the computer

```bash
# Linux / macOS
backup_cleanup/python_files/launchers/ios/start_ios_remote.sh --host <address>

# Windows
backup_cleanup\python_files\launchers\ios\start_ios_remote.bat --host <address>
```

Which `<address>`:

| Situation | Use |
|-----------|-----|
| Phone and computer both on **Tailscale** (recommended: encrypted, works anywhere) | leave `--host` off; the Tailscale address is picked automatically |
| Same home Wi-Fi, no Tailscale | the computer's LAN address, e.g. `--host 192.168.1.20` (plain HTTP: trusted network only) |
| Testing on the computer itself | nothing (binds to 127.0.0.1) |

It prints a link and a QR code.

## 2. Install on the iPhone

1. Scan the QR code with the Camera app (or open the link in **Safari**; it must be Safari).
2. Tap **Share** then **Add to Home Screen** then **Add**.

The icon on your Home Screen opens the app full-screen. The link carries your access token, so
the Home Screen icon stays signed in. Anyone with the link can use the remote: treat it like a password.

## What it does

- **Upload documents**: PDF, TXT, MD, CSV, JSON, JSONL (up to 100 MB each) into the pipeline's input folder.
- **Process input folder**: runs the same pipeline as `pipeline_cli.py process`.
- **Health check**: runs the operational health check.
- **Log** streams while a job runs; **Results** lists the output files with Download buttons.

## Security

- Every request needs the access token, and repeated wrong tokens lock the client out for a minute.
- The server can only run the two fixed commands above; uploads are restricted by file type and size
  and can never overwrite or escape the input folder; downloads only come from the output folder.
- Traffic is plain HTTP. Over Tailscale it is encrypted by the tunnel; on a LAN it is not.
  Never port-forward this to the internet.
- Reset the token (invalidates every installed icon):
  `python ios_remote_server.py --new-token --show-url`
- Show the link/QR again: `python ios_remote_server.py --show-url`

## Start at login (optional, Linux)

See the comments in `ai-data-pipeline-remote.service` next to this file.

## Alternative: SSH Shortcut

If you prefer no web app: in **Shortcuts**, add **Run Script Over SSH** with
`cd "/path/to/backup_cleanup/python_files" && ./run_pipeline.sh --health-only --smoke`.
