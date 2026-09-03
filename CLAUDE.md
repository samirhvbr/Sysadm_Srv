# sysadm-server — Instructions for Claude Code

<!--
  The content below the H1 is duplicated between CLAUDE.md (read by Claude Code)
  and AGENTS.md (read by other tooling, agents.md standard) — keep the two
  byte-identical below the H1. If you edit one, edit the other.
-->

> This repository follows the samirhvbr/Blue3 documentation and versioning
> standard. The norm lives once, at
> **[samirhvbr/repodocs](https://github.com/samirhvbr/repodocs)** — read it
> there; do not copy it here.
>
> Commits: `versão - comentário em português`, with the version coming from
> `version.md` and bumped in the same commit. Conventional Commits prefixes
> (`feat:`, `fix:`, `chore:`) and vague messages are forbidden.

---

<!-- RELEASES-RULE:repodocs -->

## Releases — the `version.md` on GitHub is what the Releases show

> Marked echo. The single source is **[samirhvbr/repodocs](https://github.com/samirhvbr/repodocs/blob/master/docs/versioning.md)**
> — change it there, not here. This block is regenerated.

**The `version.md` of the default branch, on GitHub, is what the GitHub Releases
must show.** The local checkout does not enter the calculation: it can be behind,
ahead or mid-work, and none of that is published — GitHub cannot tag a commit it
does not have.

**The bump and the Release are one act.** A commit that bumps `version.md` is not
finished until that version has a tag, a published Release, and the **`Latest`
badge on it** — the same push, not "later". A badge sitting on an older release
tells whoever looks that the project is at a version it is not.

- `.github/workflows/release.yml` does it on any push that touches `version.md`.
- `./tools/release.sh` does it by hand. It is **idempotent and self-healing**:
  it publishes whatever is missing and moves a drifted badge back. Running it is
  always safe, so it is both the check and the fix.

A PR publishes nothing while it is a PR. The moment it merges, the push moves
`version.md` on the default branch and the Release becomes that version.

Tag and Release title are the **bare version — no `v` prefix**.

<!-- /RELEASES-RULE -->
