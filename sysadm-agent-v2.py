#!/usr/bin/env python3

import subprocess
import requests
import socket
import time
import os
import hashlib

def calculate_sha256(content):
    return hashlib.sha256(content).hexdigest()

CURRENT_VERSION = "1.1.0"
VERSION_URL = "https://files.b3.rs/blue3/srv/version.json"

# 🔥 Forçar IPv4
def force_ipv4():
    orig_getaddrinfo = socket.getaddrinfo

    def new_getaddrinfo(*args, **kwargs):
        return [res for res in orig_getaddrinfo(*args, **kwargs) if res[0] == socket.AF_INET]

    socket.getaddrinfo = new_getaddrinfo



def check_update():
    try:
        r = requests.get(VERSION_URL, timeout=3)
        data = r.json()

        if data["version"] != CURRENT_VERSION:
            print("Nova versão disponível:", data["version"])

            response = requests.get(data["url"], timeout=5)
            new_script_bytes = response.content

            # 🔐 valida hash
            downloaded_hash = calculate_sha256(new_script_bytes)

            if downloaded_hash != data["sha256"]:
                print("ERRO: hash inválido! Update abortado.")
                return False

            print("Hash OK, aplicando update...")

            script_path = os.path.realpath(__file__)

            # backup
            with open(script_path + ".bak", "wb") as f:
                with open(script_path, "rb") as original:
                    f.write(original.read())

            # atualiza
            with open(script_path, "wb") as f:
                f.write(new_script_bytes)

            print("Script atualizado com sucesso.")
            return True

    except Exception as e:
        print("Erro ao verificar update:", e)

    return False



# 🔹 Config
API_URL = "https://sys.blue3.cloud/api/metrics"
TOKEN = "6173294c7285e7d47864861c81f4cf97070a1814cb7036188c91d8e3aaba06d9"


def run(cmd):
    return subprocess.getoutput(cmd)


def get_php_fpm():
    output = run("pgrep php-fpm")
    return len(output.splitlines()) if output else 0


def get_metrics():
    try:
        return {
            "hostname": socket.gethostname(),
            "cpu_load": float(run("awk '{print $1}' /proc/loadavg")),
            "memory_used": int(run("free -m | awk '/Mem:/ {print $3}'")),
            "memory_total": int(run("free -m | awk '/Mem:/ {print $2}'")),
            "disk_usage": int(run("df / | awk 'NR==2 {print int($5)}' | tr -d '%'")),
            "php_fpm_processes": get_php_fpm(),
            "timestamp": int(time.time()),
            "agent_version": CURRENT_VERSION
        }
    except Exception as e:
        print("Erro ao coletar métricas:", e)
        return None


def send_metrics(data, retries=3):
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                API_URL,
                json=data,
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=5
            )

            print(f"[Tentativa {attempt}] STATUS:", response.status_code)

            if response.status_code == 200:
                print("OK:", response.text)
                return True
            else:
                print("Erro resposta:", response.text)

        except Exception as e:
            print(f"[Tentativa {attempt}] Erro:", e)

        time.sleep(2)

    return False


def main():
    force_ipv4()

    if check_update():
        return

    metrics = get_metrics()

    if not metrics:
        print("Falha ao coletar métricas")
        return

    ok = send_metrics(metrics)

    if not ok:
        print("Falha ao enviar métricas")
    else:
        print("Envio concluído com sucesso")


if __name__ == "__main__":
    main()
