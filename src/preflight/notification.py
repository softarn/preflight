import subprocess
import sys

def send_notification(message: str, open_url: str):
    """Sends a system notification using terminal-notifier."""
    try:
        subprocess.run(
            [
                "terminal-notifier",
                "-title", "Preflight Review",
                "-message", message,
                "-open", open_url
            ],
            check=True,
            capture_output=True
        )
    except FileNotFoundError:
        print("Warning: 'terminal-notifier' not found. Notification skipped.", file=sys.stderr)
        print(f"Message: {message}", file=sys.stderr)
        print(f"URL: {open_url}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error sending notification: {e}", file=sys.stderr)
