#!/usr/bin/env python3

import json
import subprocess
import requests
import socket
import time
import os
import hashlib
import re
import shutil

CURRENT_VERSION = "1.2.86"
CONFIG_PATH = "/etc/blue3-agent.conf"
GITHUB_OWNER = "samirhvbr"
GITHUB_REPO = "Sysadm_Srv"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}.git"
DEFAULT_UPDATE_BRANCH = "master"
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
DEFAULT_UPDATE_REPO_DIR = os.path.join(SCRIPT_DIR, ".sysadm-srv-repo")
API_URL = "https://sys.blue3.cloud/api/metrics"






# Forçar IPv4
requests.packages.urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET


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


def load_config_value(env_key, config_key, default_value):
    env_value = os.getenv(env_key)
    if env_value:
        return env_value.strip()

    try:
        config = read_config()
    except Exception as e:
        print(f"Erro ao carregar {config_key}:", e)
        return default_value

    return config.get(config_key, default_value).strip() or default_value


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
    return load_config_value("BLUE3_UPDATE_BRANCH", "UPDATE_BRANCH", DEFAULT_UPDATE_BRANCH)


def load_update_repo_url():
    return load_config_value("BLUE3_UPDATE_REPO_URL", "UPDATE_REPO_URL", GITHUB_REPO_URL)


def load_update_repo_dir():
    return load_config_value("BLUE3_UPDATE_REPO_DIR", "UPDATE_REPO_DIR", DEFAULT_UPDATE_REPO_DIR)





# 🔥 Forçar IPv4
def force_ipv4():
    orig_getaddrinfo = socket.getaddrinfo

    def new_getaddrinfo(*args, **kwargs):
        return [res for res in orig_getaddrinfo(*args, **kwargs) if res[0] == socket.AF_INET]

    socket.getaddrinfo = new_getaddrinfo


# 🔐 SHA256
def calculate_sha256(content):
    return hashlib.sha256(content).hexdigest()


def is_newer_version(candidate_version, current_version):
    def normalize(version):
        parts = [int(part) for part in re.findall(r"\d+", version)]
        return tuple(parts or [0])

    return normalize(candidate_version) > normalize(current_version)


def run_command(command, cwd=None):
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )


def ensure_git_available():
    if shutil.which("git"):
        return True

    print("Git não encontrado. Tentando instalar automaticamente...")

    if hasattr(os, "geteuid") and os.geteuid() != 0:
        if not shutil.which("sudo"):
            print("ERRO: git não encontrado e sudo indisponível para instalar automaticamente.")
            return False
        prefix = ["sudo", "-n"]
    else:
        prefix = []

    installers = [
        (["apt-get", "update"], ["apt-get", "install", "-y", "git"]),
        (None, ["apt", "install", "-y", "git"]),
        (None, ["dnf", "install", "-y", "git"]),
        (None, ["yum", "install", "-y", "git"]),
        (None, ["apk", "add", "git"]),
        (None, ["zypper", "--non-interactive", "install", "git"]),
    ]

    for prepare_command, install_command in installers:
        if not shutil.which(install_command[0]):
            continue

        if prepare_command:
            result = run_command(prefix + prepare_command)
            if result.returncode != 0:
                output = result.stdout.strip()
                if output:
                    print(output)
                continue

        result = run_command(prefix + install_command)
        if result.returncode == 0 and shutil.which("git"):
            print("Git instalado com sucesso.")
            return True

        output = result.stdout.strip()
        if output:
            print(output)

    print("ERRO: não foi possível instalar git automaticamente.")
    return False


def run_git_command(args, cwd=None):
    return run_command(["git", *args], cwd=cwd)


def sync_update_repository():
    if not ensure_git_available():
        return ""

    repo_dir = UPDATE_REPO_DIR
    repo_parent = os.path.dirname(repo_dir)

    if repo_parent:
        os.makedirs(repo_parent, exist_ok=True)

    if not os.path.exists(repo_dir):
        print(f"Clonando repositório de update em: {repo_dir}")
        result = run_git_command(
            ["clone", "--depth", "1", "--branch", UPDATE_BRANCH, UPDATE_REPO_URL, repo_dir]
        )
        if result.returncode != 0:
            output = result.stdout.strip()
            if output:
                print(output)
            return ""
        return repo_dir

    if not os.path.isdir(repo_dir):
        print(f"ERRO: caminho de update inválido: {repo_dir}")
        return ""

    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        print(f"ERRO: o diretório de update não é um repositório git: {repo_dir}")
        return ""

    for args in (
        ["remote", "set-url", "origin", UPDATE_REPO_URL],
        ["fetch", "origin", UPDATE_BRANCH, "--depth", "1"],
        ["checkout", "-B", UPDATE_BRANCH, f"origin/{UPDATE_BRANCH}"],
    ):
        result = run_git_command(args, cwd=repo_dir)
        if result.returncode != 0:
            output = result.stdout.strip()
            if output:
                print(output)
            return ""

    return repo_dir


def read_script_version(script_path):
    with open(script_path, encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'^CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    return match.group(1) if match else ""


def read_version_metadata(repo_dir):
    version_file = os.path.join(repo_dir, "version.json")

    if not os.path.exists(version_file):
        return {}

    try:
        with open(version_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Aviso: version.json inválido no repositório:", e)
        return {}

    return data if isinstance(data, dict) else {}


# 🔄 Update seguro
def check_update():
    try:
        print(f"Verificando updates via git no ramo: {UPDATE_BRANCH}")

        repo_dir = sync_update_repository()
        if not repo_dir:
            return False

        repo_script_path = os.path.join(repo_dir, "srv.py")
        if not os.path.exists(repo_script_path):
            print(f"ERRO: srv.py não encontrado no repositório local: {repo_script_path}")
            return False

        new_version = read_script_version(repo_script_path)
        if not new_version:
            print("ERRO: não foi possível identificar CURRENT_VERSION no repositório git")
            return False

        if new_version == CURRENT_VERSION:
            return False

        if not is_newer_version(new_version, CURRENT_VERSION):
            print(f"Versão remota {new_version} não é superior à versão atual {CURRENT_VERSION}")
            return False

        print("Nova versão disponível:", new_version)

        with open(repo_script_path, "rb") as f:
            new_script_bytes = f.read()

        # 🔥 proteção HTML
        if b"<html" in new_script_bytes[:200]:
            print("ERRO: HTML detectado no download")
            return False

        # 🔥 valida python
        if not new_script_bytes.startswith(b"#!/usr/bin/env python3"):
            print("ERRO: arquivo inválido (não é script Python)")
            return False

        metadata = read_version_metadata(repo_dir)
        downloaded_hash = calculate_sha256(new_script_bytes)
        expected_hash = ""

        if metadata.get("version") == new_version:
            expected_hash = str(metadata.get("sha256", "")).strip()

        if expected_hash and downloaded_hash != expected_hash:
            print("ERRO: hash inválido! Update abortado.")
            return False

        print("Hash OK, aplicando update via git...")

        if os.path.realpath(repo_script_path) == SCRIPT_PATH:
            print("Repositório local sincronizado com sucesso. Reinicie o processo.")
            return True

        # backup
        with open(SCRIPT_PATH + ".bak", "wb") as f:
            with open(SCRIPT_PATH, "rb") as original:
                f.write(original.read())

        # update
        with open(SCRIPT_PATH, "wb") as f:
            f.write(new_script_bytes)

        print("Script atualizado com sucesso a partir do git. Reinicie o processo.")
        return True

    except Exception as e:
        print("Erro ao verificar update:", e)

    return False


# 🔹 Token
TOKEN = load_token()
UPDATE_BRANCH = load_update_branch()
UPDATE_REPO_URL = load_update_repo_url()
UPDATE_REPO_DIR = load_update_repo_dir()


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
