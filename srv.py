#!/usr/bin/env python3

import subprocess
import requests
import socket
import time
import os
import hashlib

CURRENT_VERSION = "1.2.85"
CONFIG_PATH = "/etc/blue3-agent.conf"
GITHUB_OWNER = "samirhvbr"
GITHUB_REPO = "Sysadm_Srv"
DEFAULT_UPDATE_BRANCH = "master"
API_URL = "https://sys.blue3.cloud/api/metrics"






# Forçar IPv4
requests.packages.urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET


def build_raw_url(branch, file_name):
    return f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{branch}/{file_name}"


def read_config():
    if not os.path.exists(CONFIG_PATH):
        return {}

    with open(CONFIG_PATH) as f:
        content = f.read().strip()

    if not content:
        return {}

    if "=" not in content:
        return {"TOKEN": content}

    config = {}

    for line in content.splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        config[key.strip()] = value.strip().strip('"').strip("'")

    return config


def write_config(config):
    lines = []

    for key in sorted(config):
        value = str(config[key]).strip()
        if not value:
            continue
        lines.append(f"{key}={value}")

    with open(CONFIG_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    os.chmod(CONFIG_PATH, 0o600)


def coletar_dados():
    hostname = os.uname().nodename

    uptime = subprocess.getoutput("uptime -p")

    return {
        "hostname": hostname,
        "uptime": uptime,
        "version": CURRENT_VERSION
    }


def enviar_dados(data):
    try:
        response = requests.post(
            API_URL,
            json=data,
            timeout=(10, 30)
        )

        print("Status:", response.status_code)
        print("Resposta:", response.text)

    except Exception as e:
        print("Erro ao enviar:", e)







# 🔐 Carregar token
def load_token():
    # 🔹 1. ENV tem prioridade
    env_token = os.getenv("BLUE3_TOKEN")
    if env_token:
        print("🔐 Usando token via ENV")
        return env_token.strip()

    try:
        # 🔹 2. Se não existe, cria interativamente
        if not os.path.exists(CONFIG_PATH):
            print(f"⚠️ Arquivo não encontrado: {CONFIG_PATH}")

            token = input("🔑 Informe o TOKEN do agente: ").strip()

            if not token or len(token) < 20:
                print("❌ Token inválido ou muito curto")
                return ""

            try:
                write_config({"TOKEN": token})

                print(f"✅ Arquivo criado: {CONFIG_PATH}")

            except Exception as e:
                print("❌ Erro ao salvar token:", e)
                return ""

            return token

        # 🔹 3. Se existe, lê
        config = read_config()
        token = config.get("TOKEN", "").strip()

        if not token:
            print("❌ Arquivo de token vazio")
            return ""

        return token

    except Exception as e:
        print("Erro ao carregar token:", e)

    return ""


def load_update_branch():
    env_branch = os.getenv("BLUE3_UPDATE_BRANCH")
    if env_branch:
        return env_branch.strip()

    try:
        config = read_config()
    except Exception as e:
        print("Erro ao carregar config de update:", e)
        return DEFAULT_UPDATE_BRANCH

    return config.get("UPDATE_BRANCH", DEFAULT_UPDATE_BRANCH).strip() or DEFAULT_UPDATE_BRANCH





# 🔥 Forçar IPv4
def force_ipv4():
    orig_getaddrinfo = socket.getaddrinfo

    def new_getaddrinfo(*args, **kwargs):
        return [res for res in orig_getaddrinfo(*args, **kwargs) if res[0] == socket.AF_INET]

    socket.getaddrinfo = new_getaddrinfo


# 🔐 SHA256
def calculate_sha256(content):
    return hashlib.sha256(content).hexdigest()


# 🔄 Update seguro
def check_update():
    try:
        print(f"Verificando updates no ramo: {UPDATE_BRANCH}")

        r = requests.get(
            VERSION_URL,
            timeout=3,
            headers={"Cache-Control": "no-cache"}
        )

        data = r.json()

        if data["version"] == CURRENT_VERSION:
            return False

        print("Nova versão disponível:", data["version"])

        script_url = data.get("url") or build_raw_url(data.get("branch", UPDATE_BRANCH), "srv.py")

        response = requests.get(
            script_url,
            timeout=5,
            headers={"Cache-Control": "no-cache"}
        )

        if response.status_code != 200:
            print("ERRO ao baixar script:", response.status_code)
            return False

        new_script_bytes = response.content

        # 🔥 proteção HTML
        if b"<html" in new_script_bytes[:200]:
            print("ERRO: HTML detectado no download")
            return False

        # 🔥 valida python
        if not new_script_bytes.startswith(b"#!/usr/bin/env python3"):
            print("ERRO: arquivo inválido (não é script Python)")
            return False

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

        # update
        with open(script_path, "wb") as f:
            f.write(new_script_bytes)

        print("Script atualizado com sucesso. Reinicie o processo.")
        return True

    except Exception as e:
        print("Erro ao verificar update:", e)

    return False


# 🔹 Token
TOKEN = load_token()
UPDATE_BRANCH = load_update_branch()
VERSION_URL = build_raw_url(UPDATE_BRANCH, "version.json")


def run(cmd):
    return subprocess.getoutput(cmd)


def get_php_fpm():
    output = run("pgrep php-fpm")
    return len(output.splitlines()) if output else 0


def get_disk_usage(path):
    if not os.path.exists(path):
        return None

    try:
        output = run(f"df {path} | awk 'NR==2 {{print int($5)}}' | tr -d '%'")
        return int(output)
    except:
        return None


def get_memory():
    meminfo = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":")
            meminfo[key] = int(value.strip().split()[0])

    total = meminfo.get("MemTotal", 0) // 1024
    free = meminfo.get("MemAvailable", 0) // 1024

    used = total - free

    return total, used





def get_metrics():
    try:
        mem_total, mem_used = get_memory()

        cpu_raw = run("awk '{print $1}' /proc/loadavg").strip()
        cpu_load = float(cpu_raw) if cpu_raw else 0.0

        return {
            "hostname": socket.gethostname(),
            "cpu_load": cpu_load,
            "memory_used": mem_used,
            "memory_total": mem_total,
            "disk_root": get_disk_usage("/"),
            "disk_var_log": get_disk_usage("/var/log"),
            "disk_srv": get_disk_usage("/srv"),
            "php_fpm_processes": get_php_fpm(),
            "timestamp": int(time.time()),
            "agent_version": CURRENT_VERSION
        }

    except Exception as e:
        print("Erro ao coletar métricas:", e)
        return None




def send_metrics(data, retries=3):
    if not TOKEN:
        print("❌ TOKEN vazio!")
        return False

    headers = {
        "Authorization": f"Bearer {TOKEN.strip()}",
        "Content-Type": "application/json"
    }

    for attempt in range(1, retries + 1):
        try:
            print(f"DEBUG TOKEN: '{TOKEN}'")

            response = requests.post(
                API_URL,
                json=data,
                headers=headers,
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

    if not TOKEN:
        print("ERRO: TOKEN não carregado!")
        return

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
