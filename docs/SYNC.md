# Repository synchronization

Canonical development clone: `/Volumes/ArvectumSSD/Arvectum/repos/musbread` on Mac mini.

- GitHub (authoritative): `https://github.com/arvectum2/musbread.git` (`origin`).
- GitVerse (read-only mirror): `https://gitverse.ru/arvectum/musbread.git` (`gitverse`).
- Local work is committed and pushed only to `origin` (`git push origin main`).
- `.github/workflows/mirror-to-gitverse.yml` mirrors **all ordinary branches and tags** from GitHub to GitVerse on every push and once daily. It uses GitHub Actions secret `GITVERSE_TOKEN`, never stores the secret in the repository.
- The mirror intentionally force-aligns GitVerse branches/tags with GitHub. Do **not** commit directly to GitVerse: it is not the source of truth.
- Mac mini LaunchAgent `com.arvectum.musbread-sync` runs the installed copy at `~/.local/bin/arvectum-musbread-sync.sh` (from `scripts/sync-local.sh`) every five minutes and on login. It fast-forwards `main` **only when the checkout is clean and on `main`**. Non-fast-forward, dirty worktrees and other active branches are never overwritten.
- To check alignment:
  ```sh
  cd /Volumes/ArvectumSSD/Arvectum/repos/musbread
  git rev-parse HEAD
  git ls-remote origin refs/heads/main
  git ls-remote gitverse refs/heads/main
  gh run list -R arvectum2/musbread --workflow mirror-to-gitverse.yml --limit 3
  ```

Note: repository visibility is managed separately on GitHub and GitVerse. Keep credentials, client material and personal data out of commits until both permissions have been reviewed.

To update the installed job after changing the script or plist, copy `scripts/sync-local.sh` to `~/.local/bin/arvectum-musbread-sync.sh`, copy `infra/launchd/com.arvectum.musbread-sync.plist` to `~/Library/LaunchAgents/`, and reload the job with `launchctl bootout`/`bootstrap`.
