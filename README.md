# Sysadm_Srv

Este projeto passa a usar o GitHub como origem principal das atualizações do agente.

## Origem de update

- Repositório principal: `https://github.com/samirhvbr/Sysadm_Srv`
- `srv.py` publicado via raw GitHub: `https://raw.githubusercontent.com/samirhvbr/Sysadm_Srv/<branch>/srv.py`
- `version.json` publicado via raw GitHub: `https://raw.githubusercontent.com/samirhvbr/Sysadm_Srv/<branch>/version.json`

O agente agora monta a URL de atualização a partir do ramo configurado. Em produção o padrão é `master`.

## Configuração do agente

Arquivo: `/etc/blue3-agent.conf`

Exemplo:

```ini
TOKEN=seu-token-aqui
UPDATE_BRANCH=master
```

Prioridades de configuração:

1. `BLUE3_TOKEN` e `BLUE3_UPDATE_BRANCH` via ambiente
2. `TOKEN` e `UPDATE_BRANCH` no arquivo `/etc/blue3-agent.conf`
3. ramo padrão `master`

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

Agentes antigos ainda consultam a URL legada em `files.b3.rs`. Para migrá-los para o GitHub, faça um bootstrap uma única vez: publique a nova versão do `srv.py` e do `version.json` legados, para que eles baixem a versão `1.2.85` e passem a consultar o GitHub nas próximas atualizações.
