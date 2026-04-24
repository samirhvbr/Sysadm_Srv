#!/usr/bin/env python3

import subprocess
import requests
import json
import time
import socket

API_URL = "http://100.64.100.126/api/metrics"
TOKEN = "6173294c7285e7d47864861c81f4cf97070a1814cb7036188c91d8e3aaba06d9"

def run(cmd):
    return subprocess.getoutput(cmd)

def get_php_fpm():
    output = run("pgrep php-fpm")
    return len(output.splitlines()) if output else 0

def get_metrics():
    return {
        "hostname": socket.gethostname(),
        "cpu_load": float(run("cat /proc/loadavg | awk '{print $1}'")),
        "memory_used": int(run("free -m | awk '/Mem:/ {print $3}'")),
        "memory_total": int(run("free -m | awk '/Mem:/ {print $2}'")),
        "disk_usage": int(run("df / | awk 'NR==2 {print int($5)}' | tr -d '%'"))
    }


def send_metrics(data):
    try:
        response = requests.post(
            API_URL,
            json=data,
            headers={
                "Authorization": f"Bearer {TOKEN}"
            },
            timeout=5
        )

        print("STATUS:", response.status_code)
        print("RESPOSTA:", response.text)

        return response.status_code == 200

    except Exception as e:
        print("Erro ao enviar:", e)
        return False

def main():
    metrics = get_metrics()
    ok = send_metrics(metrics)

    if not ok:
        print("Falha ao enviar métricas")
    else:
        print("OK:", metrics)

if __name__ == "__main__":
    main()
