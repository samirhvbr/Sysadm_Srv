# Sysadm_Srv

This project now uses GitHub as the primary source for agent updates.

## Update source

- Main repository: `https://github.com/samirhvbr/Sysadm_Srv`
- The agent syncs a local clone via `git clone` / `git fetch` / `git checkout`
- `version.json` still exists in the repository for version metadata and hash validation

The agent now queries the configured git repository. In production, the default is `master`.

## Agent configuration

File: `/etc/blue3-agent.conf`

Example:

```ini
TOKEN=seu-token-aqui
UPDATE_BRANCH=master
UPDATE_REPO_URL=https://github.com/samirhvbr/Sysadm_Srv.git
UPDATE_REPO_DIR=/opt/blue3/sysadm-srv
```

Configuration priorities:

1. `BLUE3_TOKEN`, `BLUE3_UPDATE_BRANCH`, `BLUE3_UPDATE_REPO_URL` and `BLUE3_UPDATE_REPO_DIR` via environment
2. `TOKEN`, `UPDATE_BRANCH`, `UPDATE_REPO_URL` and `UPDATE_REPO_DIR` in the `/etc/blue3-agent.conf` file
3. default branch `master`

If the server does not have `git`, the agent tries to install it automatically using the available package manager (`apt-get`, `apt`, `dnf`, `yum`, `apk` or `zypper`).

## Version flow

1. Change `srv.py` and update `CURRENT_VERSION`.
2. Generate the current branch's `version.json` with `./update_version.sh`.
3. Commit `srv.py` and `version.json`.
4. Push to the branch that will be used for testing or production.

Examples:

```bash
./update_version.sh
./update_version.sh testing
```

## Testing flow before promoting

1. Create or use a test branch, for example `testing`.
2. Generate `version.json` pointing to that branch with `./update_version.sh testing`.
3. Push the branch.
4. On the test servers, set `UPDATE_BRANCH=testing` or `BLUE3_UPDATE_BRANCH=testing`.
5. Validate the auto-update.
6. Once approved, merge or replicate the change into `master`, run `./update_version.sh master` and push.

## Migrating already-installed agents

Old agents still query the legacy URL at `files.b3.rs`. To migrate them to git, it is still necessary to deliver version `1.2.86` once via the current channel or manually. After that, subsequent updates start being done by querying the configured git repository, without depending on the local URL.

The base installer must also ensure `git` is present on the server. The [www/files.b3.rs/blue3/blue3_start_script/start.sh](www/files.b3.rs/blue3/blue3_start_script/start.sh#L39) script now includes `git` in the list of base packages.
