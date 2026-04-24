#!/bin/bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_FILE="$REPO_DIR/srv.py"
VERSION_FILE="$REPO_DIR/version.json"
GITHUB_OWNER="samirhvbr"
GITHUB_REPO="Sysadm_Srv"
DEFAULT_BRANCH="master"

cd "$REPO_DIR"

BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
if [ "$BRANCH" = "HEAD" ] || [ -z "$BRANCH" ]; then
    BRANCH="$DEFAULT_BRANCH"
fi

RAW_BASE_URL="https://raw.githubusercontent.com/$GITHUB_OWNER/$GITHUB_REPO/$BRANCH"
PUBLIC_URL="$RAW_BASE_URL/srv.py"

echo "🧹 Normalizando indentação (tabs → espaços)..."
expand -t 4 "$SCRIPT_FILE" > "$SCRIPT_FILE.tmp" && mv "$SCRIPT_FILE.tmp" "$SCRIPT_FILE"

echo "🔍 Lendo versão do srv.py..."

VERSION=$(grep '^CURRENT_VERSION' "$SCRIPT_FILE" | head -n1 | cut -d '"' -f2)

if [ -z "$VERSION" ]; then
    echo "❌ Não foi possível encontrar CURRENT_VERSION"
    exit 1
fi

echo "✔️ Versão encontrada: $VERSION"

if ! git diff --quiet -- "$SCRIPT_FILE"; then
    echo "⚠️ srv.py possui mudanças locais. Faça commit e push do mesmo conteúdo antes de distribuir esta versão."
fi

echo "🔐 Calculando SHA256..."

SHA256=$(sha256sum "$SCRIPT_FILE" | awk '{print $1}')

echo "✔️ SHA256: $SHA256"

echo "📝 Atualizando version.json..."

printf '{\n  "version": "%s",\n  "branch": "%s",\n  "url": "%s",\n  "sha256": "%s"\n}\n' \
"$VERSION" "$BRANCH" "$PUBLIC_URL" "$SHA256" > "$VERSION_FILE"

echo "🚀 Atualização concluída!"
echo "📄 Novo version.json:"
cat "$VERSION_FILE"
echo "📌 Origem principal: $RAW_BASE_URL"
