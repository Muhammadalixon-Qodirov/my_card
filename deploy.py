"""MyCard deploy: lokal `git push` -> serverda `git pull`, migrate, collectstatic, restart.

Ishlatish:
    python deploy.py              # push + deploy
    python deploy.py --no-push    # faqat serverni GitHub'dagi holatga keltirish
    python deploy.py --force      # yangi commit bo'lmasa ham migrate/restart qilish

SSH paroli: MYCARD_SSH_PASSWORD muhit o'zgaruvchisi yoki .env.deploy fayli
(gitignore'da), bo'lmasa so'raladi.
"""
import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

import paramiko

HOST = "95.182.118.142"
PORT = 2203
USER = "einvestment"
APP_DIR = "/home/einvestment/mycard"
BRANCH = "main"
SERVICES = "mycard mycard_celery mycard_celery_beat"
HEALTH_URL = "https://mycard.e-investment.uz/admin/login/"

REMOTE_SCRIPT = f"""
exec 2>&1
set -euo pipefail
IFS= read -r SUDO_PW
as_root() {{ printf '%s\\n' "$SUDO_PW" | sudo -S -p '' "$@"; }}
as_www() {{ as_root -u www-data "$@"; }}

cd {APP_DIR}
OLD=$(git rev-parse HEAD)
echo "==> git pull ({BRANCH})"
git pull --ff-only origin {BRANCH}
NEW=$(git rev-parse HEAD)

if [ "$OLD" = "$NEW" ] && [ "__FORCE__" != "1" ]; then
    echo "==> Yangi commit yo'q ($NEW), deploy kerak emas."
    exit 0
fi
git --no-pager log --oneline "$OLD..$NEW"

if ! git diff --quiet "$OLD" "$NEW" -- requirements.txt; then
    echo "==> pip install"
    as_www venv/bin/pip install --no-cache-dir -r requirements.txt
fi

echo "==> migrate"
as_www venv/bin/python manage.py migrate --noinput --settings=config.settings.prod
echo "==> collectstatic"
as_www venv/bin/python manage.py collectstatic --noinput --settings=config.settings.prod | tail -1

echo "==> restart: {SERVICES}"
as_root systemctl restart {SERVICES}
sleep 3
systemctl is-active {SERVICES}
CODE=$(curl -s -o /dev/null -w '%{{http_code}}' --max-time 15 {HEALTH_URL})
echo "==> health: {HEALTH_URL} -> $CODE"
[ "$CODE" = "200" ] || {{ echo "XATO: sayt javob bermayapti. Oldingi commit: $OLD"; exit 1; }}
echo "==> Deploy tugadi: $NEW"
"""


def get_password():
    pw = os.environ.get("MYCARD_SSH_PASSWORD")
    env_file = Path(__file__).with_name(".env.deploy")
    if not pw and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("MYCARD_SSH_PASSWORD="):
                pw = line.split("=", 1)[1]
    return pw or getpass.getpass(f"{USER}@{HOST} paroli: ")


def main():
    parser = argparse.ArgumentParser(description="MyCard deploy")
    parser.add_argument("--no-push", action="store_true", help="git push qilmaslik")
    parser.add_argument("--force", action="store_true", help="yangi commit bo'lmasa ham deploy")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not args.no_push:
        print(f"==> git push origin {BRANCH}")
        subprocess.run(["git", "push", "origin", BRANCH], cwd=Path(__file__).parent, check=True)

    password = get_password()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=password, timeout=30,
                   banner_timeout=60, look_for_keys=False, allow_agent=False)
    try:
        script = REMOTE_SCRIPT.replace("__FORCE__", "1" if args.force else "0")
        stdin, stdout, _ = client.exec_command(script, timeout=900)
        stdin.write(password + "\n")
        stdin.flush()
        stdin.channel.shutdown_write()
        for line in stdout:
            print(line, end="")
        code = stdout.channel.recv_exit_status()
    finally:
        client.close()
    sys.exit(code)


if __name__ == "__main__":
    main()
