"""
FashionAI Shop — Universal Runner
Usage:
  python run.py          — start all services
  python run.py backend  — only backend
  python run.py telebot  — only telebot
  python run.py aiogram  — only aiogram
  python run.py train    — train neural network
"""

import subprocess
import sys
import os
import threading
import time
import signal

# Force UTF-8 output on Windows so Cyrillic names display correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVICES = {
    'backend': {
        'cmd': [sys.executable, 'backend/app.py'],
        'label': 'BACKEND ',
        'color': '\033[94m',   # blue
    },
    'telebot': {
        'cmd': [sys.executable, 'bot_telebot/bot.py'],
        'label': 'TELEBOT ',
        'color': '\033[92m',   # green
    },
    'aiogram': {
        'cmd': [sys.executable, 'bot_aiogram/bot.py'],
        'label': 'AIOGRAM ',
        'color': '\033[93m',   # yellow
    },
    'train': {
        'cmd': [sys.executable, 'neural_network/train.py'],
        'label': 'TRAIN   ',
        'color': '\033[95m',   # magenta
    },
}

RESET = '\033[0m'
RED   = '\033[91m'

processes = []


def _read_stream(stream, fmt):
    for line in iter(stream.readline, b''):
        text = line.decode('utf-8', errors='replace').rstrip()
        print(fmt.format(text), flush=True)


def stream_output(proc, label, color):
    t = threading.Thread(
        target=_read_stream,
        args=(proc.stdout, f"{color}[{label}]{RESET} {{}}"),
        daemon=True,
    )
    t.start()


def start_service(name):
    svc = SERVICES[name]
    print(f"{svc['color']}[{svc['label']}]{RESET} Starting...")
    proc = subprocess.Popen(
        svc['cmd'],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    processes.append(proc)
    t = threading.Thread(target=stream_output, args=(proc, svc['label'], svc['color']), daemon=True)
    t.start()
    return proc


def shutdown(sig=None, frame=None):
    print(f"\n{RED}Stopping all services...{RESET}")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(1)
    for p in processes:
        try:
            p.kill()
        except Exception:
            pass
    print("All services stopped.")
    sys.exit(0)


def main():
    args = sys.argv[1:]

    # Default: start backend + both bots
    to_start = args if args else ['backend', 'telebot', 'aiogram']

    # Validate
    for name in to_start:
        if name not in SERVICES:
            print(f"Unknown service: '{name}'. Available: {', '.join(SERVICES)}")
            sys.exit(1)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("=" * 55)
    print("  FashionAI Shop — starting services")
    print(f"  Services: {', '.join(to_start)}")
    if 'backend' in to_start:
        print("  Site:    http://localhost:5000")
        print("  Swagger: http://localhost:5000/apidocs/")
    print("  Press Ctrl+C to stop all")
    print("=" * 55)

    # Stagger starts slightly so backend is up first
    for i, name in enumerate(to_start):
        start_service(name)
        if i < len(to_start) - 1:
            time.sleep(1.5)

    # Keep alive
    running = list(zip(to_start, range(len(processes))))
    try:
        while True:
            for name, i in running:
                if i < len(processes) and processes[i].poll() is not None:
                    print(f"{RED}[{SERVICES[name]['label']}] Crashed (exit {processes[i].returncode}), restarting...{RESET}")
                    processes[i] = start_service(name)
            time.sleep(3)
    except KeyboardInterrupt:
        shutdown()


if __name__ == '__main__':
    main()