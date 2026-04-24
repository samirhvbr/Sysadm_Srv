#!/bin/bash

chown -R www-data:www-data *

set -e

BASE_DIR="/srv/web/www/files.b3.rs/BLUE3/srv"
SCRIPT_FILE="$BASE_DIR/srv.py"
VERSION_FILE="$BASE_DIR/version.json"

PUBLIC_URL="https://files.b3.rs/blue3/srv/srv.py"

echo "🧹 Normalizando indentação (tabs → espaços)..."
expand -t 4 "$SCRIPT_FILE" > "$SCRIPT_FILE.tmp" && mv "$SCRIPT_FILE.tmp" "$SCRIPT_FILE"

echo "🔍 Lendo versão do srv.py..."

VERSION=$(grep '^CURRENT_VERSION' "$SCRIPT_FILE" | head -n1 | cut -d '"' -f2)

if [ -z "$VERSION" ]; then
    echo "❌ Não foi possível encontrar CURRENT_VERSION"
    exit 1
fi

echo "✔️ Versão encontrada: $VERSION"

echo "🌐 Baixando arquivo via HTTP (sem cache)..."

curl -s -H "Cache-Control: no-cache" "$PUBLIC_URL" -o /tmp/srv_remote.py

echo "🔐 Calculando SHA256..."

SHA256=$(sha256sum /tmp/srv_remote.py | awk '{print $1}')

echo "✔️ SHA256: $SHA256"

echo "📝 Atualizando version.json..."

printf '{\n  "version": "%s",\n  "url": "%s",\n  "sha256": "%s"\n}\n' \
"$VERSION" "$PUBLIC_URL" "$SHA256" > "$VERSION_FILE"

echo "🚀 Atualização concluída!"
echo "📄 Novo version.json:"
cat "$VERSION_FILE"
