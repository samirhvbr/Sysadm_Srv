#!/usr/bin/env bash
# release.sh — every version in version.md gets a git tag named after it and a
# published GitHub Release.
#
# WHY THIS EXISTS: GitHub never infers a version from a commit subject. A repo
# whose history is full of `2.110.161 - …` still shows "No releases published",
# and `git diff 2.110.160..2.110.161` is impossible because neither name exists
# as a ref. The tag is what pins a version number to the exact code it named.
#
# The version is THE FIRST SEMVER IN version.md — not the whole file. Two shapes
# live in this fleet and both must read the same:
#     1.76.108                            (bare, e.g. EOP, SHVIA-WEB, repodocs)
#     # Versão — X\n**Versão atual:** `0.17.1`   (markdown, e.g. the BLUE3-ISP repos)
# That is the rule those repos already document and that config/app.php already
# implements with preg_match('/\d+\.\d+\.\d+/').
#
# Tags carry NO `v` prefix: the tag is byte-for-byte what version.md says.
#
# Idempotent and resumable by construction — anything that already exists is
# skipped, so re-running is free and an interrupted run just continues.
#
#   ./tools/release.sh --dry-run              # print the table, create nothing
#   ./tools/release.sh                        # tag+release the current version
#   ./tools/release.sh --backfill --dry-run   # the whole history, as a table
#   ./tools/release.sh --backfill             # the whole history, for real
#
# Norm: docs/versioning.md · docs/decisions.md ADR-011
set -uo pipefail

MODE=current
DRY=0
REPO=""
SLEEP=0.35          # throttle: ~2.8 req/s, well under GitHub's ceiling
RATE_FLOOR=200      # stop and report rather than exhausting the budget
REF=""             # --ref: which history to walk (default: HEAD). Use
                    # origin/master where the local checkout is behind and a
                    # pull is refused by in-flight work — backfilling from a
                    # stale HEAD silently omits every version pushed since.
QUIET=0             # -q: totals only, one line per repo — for fleet-wide sweeps

die() { printf 'release.sh: %s\n' "$1" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --backfill) MODE=backfill ;;
    --current)  MODE=current ;;
    --dry-run|-n) DRY=1 ;;
    --quiet|-q) QUIET=1 ;;
    --repo) REPO="${2:-}"; shift ;;
    --ref)  REF="${2:-}"; shift ;;
    --sleep) SLEEP="${2:-}"; shift ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument '$1' (try --help)" ;;
  esac
  shift
done

git rev-parse --git-dir >/dev/null 2>&1 || die "not inside a git repository"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT" || die "cannot cd to repo root"

[ -f version.md ] || die "no version.md at $ROOT — the fleet's version authority is missing"

# --- the version is the FIRST semver in the file, whatever shape it has -------
first_semver() { grep -oE '[0-9]+\.[0-9]+\.[0-9]+' "$1" 2>/dev/null | head -n 1; }

# THE RULE: the version.md ON GITHUB is what the Releases ON GITHUB must match.
# The local checkout does not enter the calculation — it can be behind, ahead or
# mid-work, and none of that is published. So the authority is the remote branch
# when we can see it, and HEAD only when we cannot (which is the CI case, where
# HEAD *is* the pushed commit).
if [ -z "$REF" ]; then
  REF="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
  [ -z "$REF" ] && REF="origin/$(git symbolic-ref --quiet --short HEAD 2>/dev/null)"
  git rev-parse --verify --quiet "$REF" >/dev/null 2>&1 || REF="HEAD"
fi
git rev-parse --verify --quiet "$REF" >/dev/null || die "ref '$REF' does not exist"

CURRENT="$(git show "$REF:version.md" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)"
[ -n "$CURRENT" ] || die "version.md at $REF holds no X.Y.Z anywhere"

# Informational only: a local tree that disagrees is normal mid-work, and it is
# deliberately NOT published.
LOCAL_V="$(first_semver version.md)"
if [ -n "$LOCAL_V" ] && [ "$LOCAL_V" != "$CURRENT" ]; then
  printf 'release.sh: note — local version.md says %s; publishing %s from %s (the remote is the authority).\n' \
    "$LOCAL_V" "$CURRENT" "$REF" >&2
fi

if [ -z "$REPO" ]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)"
fi
[ -n "$REPO" ] || die "cannot determine owner/name — pass --repo owner/name"

BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo master)"

# --- release notes ------------------------------------------------------------
# Preference: the CHANGELOG section for this version → the commit subjects that
# carried it → GitHub's own generated notes. EOP has no CHANGELOG.md at all, so
# the fallback is not theoretical.
#
# Two heading shapes exist in this fleet, and both are matched:
#   ## 1.1.0 - título
#   ### `0.17.0` — 2026-08-24 — título
notes_for() {
  local ver="$1" sha="$2" out="$3" body=""
  if [ -f CHANGELOG.md ]; then
    body="$(awk -v ver="$ver" '
      # Returns the heading level (2..4), or 0 for a non-heading line.
      function hlevel(line,   m) {
        if (match(line, /^#{2,4}[ \t]/)) { m = substr(line, 1, RLENGTH); gsub(/[ \t]/, "", m); return length(m) }
        return 0
      }
      # Does this heading name our version? Backticks are stripped because the
      # fleet writes both `## 1.1.0 - x` and "### `0.17.0` - 2026-08-24 - x".
      function is_ours(line,   s) {
        s = line; sub(/^#+[ \t]*/, "", s); gsub(/`/, "", s)
        return index(s, ver) == 1
      }
      { lv = hlevel($0)
        if (!flag) { if (lv && is_ours($0)) { flag = 1; open_lv = lv } ; next }
        # Only a heading at the SAME level or higher ends the section — the
        # entry keeps its own ### subsections, which is where the substance is.
        if (lv && lv <= open_lv) exit
        print }
    ' CHANGELOG.md)"
  fi
  if [ -z "$(printf '%s' "$body" | tr -d '[:space:]')" ]; then
    body="$(git log --format='- %s' --grep="^$(printf '%s' "$ver" | sed 's/\./\\./g') - " "$sha" 2>/dev/null | head -n 40)"
    [ -n "$body" ] && body="## Commits$(printf '\n\n')$body"
  fi
  printf '%s\n' "$body" > "$out"
  [ -s "$out" ] && [ -n "$(tr -d '[:space:]' < "$out")" ]
}

# --- rate limit ---------------------------------------------------------------
rate_left() { gh api rate_limit --jq '.resources.core.remaining' 2>/dev/null || echo 9999; }

# --- what is already published ------------------------------------------------
# Fetched ONCE per repo, not once per version. Asking `gh release view` for each
# version would cost one API call per version just to look — 2,764 calls
# fleet-wide before creating anything.
EXISTING="$(mktemp)"
trap 'rm -f "$EXISTING"' EXIT
gh release list --repo "$REPO" --limit 1000 --json tagName --jq '.[].tagName' > "$EXISTING" 2>/dev/null || : > "$EXISTING"
EXISTING_N="$(grep -c . "$EXISTING" || true)"
# A version counts as published under EITHER name. Some repos in this fleet
# published Releases with a `v` prefix before the bare-number rule existed, and
# SSHVTERM-DESKTOP's carry 178 installer assets with 10k downloads. Creating a
# bare-tag Release for a version that already has a `v` one would not "fix" the
# naming — it would duplicate the version and leave the copy WITHOUT the
# binaries. The old Release stays; nothing is duplicated.
already() { grep -Fxq "$1" "$EXISTING" || grep -Fxq "v$1" "$EXISTING"; }

# --- one version --------------------------------------------------------------
CREATED=0; SKIPPED=0; FAILED=0; CONSEC_FAIL=0
publish() {
  local ver="$1" sha="$2" is_last="$3"
  if already "$ver"; then
    [ "${QUIET:-0}" = "1" ] || printf '  %-14s %s  already published — skipped\n' "$ver" "${sha:0:7}"
    SKIPPED=$((SKIPPED+1)); return 0
  fi
  if [ "$DRY" = "1" ]; then
    [ "${QUIET:-0}" = "1" ] || printf '  %-14s %s  WOULD CREATE\n' "$ver" "${sha:0:7}"
    CREATED=$((CREATED+1)); return 0
  fi

  local left; left="$(rate_left)"
  if [ "$left" -lt "$RATE_FLOOR" ] 2>/dev/null; then
    printf 'release.sh: STOPPING — only %s API calls left. Re-run later; it resumes.\n' "$left" >&2
    return 9
  fi

  local nf; nf="$(mktemp)"
  local args=(release create "$ver" --repo "$REPO" --target "$sha" --title "$ver")
  if notes_for "$ver" "$sha" "$nf"; then args+=(--notes-file "$nf"); else args+=(--generate-notes); fi
  [ "$is_last" = "1" ] && args+=(--latest)

  # Creating a release is a "content-creating" request, which GitHub throttles
  # far more tightly than reads — a secondary limit that answers 403 with a
  # "retry after" rather than a plain quota number. A backfill of thousands
  # WILL meet it, so meeting it politely is part of the job: back off and retry
  # rather than hammer, because hammering earns a longer block.
  local attempt=0 ok=0
  while [ "$attempt" -lt 5 ]; do
    if gh "${args[@]}" >/dev/null 2>"$nf.err"; then ok=1; break; fi
    if grep -qi 'secondary rate limit\|abuse detection\|rate limit' "$nf.err"; then
      attempt=$((attempt+1))
      local wait=$((attempt * 60))
      printf '  %-14s secondary rate limit — waiting %ss (attempt %s/5)\n' "$ver" "$wait" "$attempt" >&2
      sleep "$wait"
    else
      break
    fi
  done
  if [ "$ok" = "1" ]; then
    printf '  %-14s %s  published\n' "$ver" "${sha:0:7}"
    printf '%s\n' "$ver" >> "$EXISTING"
    CREATED=$((CREATED+1))
  else
    printf '  %-14s %s  FAILED: %s\n' "$ver" "${sha:0:7}" "$(head -n1 "$nf.err")" >&2
    FAILED=$((FAILED+1))
    # Three failures in a row is a wall, not a fluke — stop and let the operator
    # look, instead of burning the remaining budget against it.
    CONSEC_FAIL=$((CONSEC_FAIL+1))
    [ "$CONSEC_FAIL" -ge 3 ] && { printf 'release.sh: STOPPING after 3 consecutive failures.\n' >&2; return 9; }
    return 0
  fi
  CONSEC_FAIL=0
  rm -f "$nf" "$nf.err"
  sleep "$SLEEP"
}

[ "$QUIET" = "1" ] || printf 'repo:    %s\nbranch:  %s\nversion: %s (first semver in version.md at %s)\nmode:    %s%s\nalready: %s Release(s) published\n\n' \
  "$REPO" "$BRANCH" "$CURRENT" "$REF" "$MODE" "$([ "$DRY" = 1 ] && echo '  [DRY RUN — nothing is created]')" "$EXISTING_N"

if [ "$MODE" = "current" ]; then
  # Tag the commit the version actually lives on, on the remote. Uncommitted or
  # unpushed bumps are not published — GitHub cannot tag a commit it does not
  # have, and a Release for a version nobody can fetch is a lie.
  publish "$CURRENT" "$(git rev-parse "$REF")" 1
else
  # Oldest first, so the newest version is created last and ends up "Latest".
  # For each distinct version, the tag points at the LAST commit that carried
  # it — the finished state of that version, not its first commit. Several
  # commits sharing one version is expected and allowed (ADR-003).
  MAP="$(git log --reverse --format='%H%x09%s' "$REF" | awk -F'\t' '
    { if (match($2, /^[0-9]+\.[0-9]+\.[0-9]+/)) {
        v = substr($2, RSTART, RLENGTH)
        if (!(v in seen)) { order[++n] = v; seen[v] = 1 }
        last[v] = $1 } }
    END { for (i = 1; i <= n; i++) print order[i] "\t" last[order[i]] }')"
  TOTAL="$(printf '%s\n' "$MAP" | grep -c . || true)"
  [ "$QUIET" = "1" ] || printf '%s distinct version(s) in history of %s\n\n' "$TOTAL" "$REF"
  i=0
  while IFS=$'\t' read -r ver sha; do
    [ -n "$ver" ] || continue
    i=$((i+1))
    publish "$ver" "$sha" "$([ "$i" = "$TOTAL" ] && echo 1 || echo 0)" || break
  done <<< "$MAP"
fi

if [ "$QUIET" = "1" ]; then
  printf '%-34s %-12s versions=%-5s todo=%-5s have=%s\n' "$REPO" "$CURRENT" "$((CREATED+SKIPPED))" "$CREATED" "$SKIPPED"
else
  printf '\ncreated/would-create: %s   skipped: %s   failed: %s\n' "$CREATED" "$SKIPPED" "$FAILED"
fi
[ "$DRY" = 1 ] || git fetch --tags --quiet 2>/dev/null || true
[ "$FAILED" -eq 0 ]
