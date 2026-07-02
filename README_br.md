# Sysadm_Srv

Este projeto passa a usar o GitHub como origem principal das atualizações do agente.

## Origem de update

- Repositório principal: `https://github.com/samirhvbr/Sysadm_Srv`
- O agente sincroniza um clone local via `git clone` / `git fetch` / `git checkout`
- O `version.json` continua existindo no repositório para metadados de versão e validação de hash

O agente agora consulta o repositório git configurado. Em produção o padrão é `master`.

## Configuração do agente

Arquivo: `/etc/blue3-agent.conf`

Exemplo:

```ini
TOKEN=seu-token-aqui
UPDATE_BRANCH=master
UPDATE_REPO_URL=https://github.com/samirhvbr/Sysadm_Srv.git
UPDATE_REPO_DIR=/opt/blue3/sysadm-srv
```

Prioridades de configuração:

1. `BLUE3_TOKEN`, `BLUE3_UPDATE_BRANCH`, `BLUE3_UPDATE_REPO_URL` e `BLUE3_UPDATE_REPO_DIR` via ambiente
2. `TOKEN`, `UPDATE_BRANCH`, `UPDATE_REPO_URL` e `UPDATE_REPO_DIR` no arquivo `/etc/blue3-agent.conf`
3. ramo padrão `master`

Se o servidor não tiver `git`, o agente tenta instalar automaticamente usando o gerenciador de pacotes disponível (`apt-get`, `apt`, `dnf`, `yum`, `apk` ou `zypper`).

## Fluxo de versão

1. Altere `srv.py` e atualize `CURRENT_VERSION`.
2. Gere o `version.json` do ramo atual com `./update_version.sh`.
3. Faça commit de `srv.py` e `version.json`.
4. Faça push para o ramo que será usado no teste ou produção.

Exemplos:

```bash
./update_version.sh
./update_version.sh testing
```

## Fluxo de teste antes de promover

1. Crie ou use um ramo de teste, por exemplo `testing`.
2. Gere `version.json` apontando para esse ramo com `./update_version.sh testing`.
3. Faça push do ramo.
4. Nos servidores de teste, defina `UPDATE_BRANCH=testing` ou `BLUE3_UPDATE_BRANCH=testing`.
5. Valide o auto-update.
6. Depois de aprovado, mescle ou replique a mudança em `master`, rode `./update_version.sh master` e faça push.

## Migração dos agentes já instalados

Agentes antigos ainda consultam a URL legada em `files.b3.rs`. Para migrá-los para o git, ainda é necessário entregar a versão `1.2.86` uma única vez pelo canal atual ou manualmente. Depois disso, as próximas atualizações passam a ser feitas consultando o repositório git configurado, sem depender do URL local.

O instalador base também deve garantir `git` no servidor. O script [www/files.b3.rs/blue3/blue3_start_script/start.sh](www/files.b3.rs/blue3/blue3_start_script/start.sh#L39) agora inclui `git` na lista de pacotes básicos.
