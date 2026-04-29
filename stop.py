"""Stop bot via pidfile"""
import os
import signal

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bot.pid")

try:
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    os.kill(pid, signal.SIGKILL)
    print(f"Bot stopped (PID {pid})")
except FileNotFoundError:
    print("Bot is not running (no pidfile)")
except ProcessLookupError:
    print("Bot is not running (stale pidfile)")
    os.remove(PID_FILE)
