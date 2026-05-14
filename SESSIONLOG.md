# FugginNAS Session Log

Tracks progress against the planned build order in CONTEXT.md.
Each planned session lists its objective, the tasks completed, and current status.

> **Note:** Actual sessions were broader than planned. Sessions 1–2 covered the
> equivalent of planned Sessions 1–12. The log below is organized by planned
> session so the gap analysis stays honest.

---

## Planned Session 1 — `install.sh` + Flask skeleton + drive discovery + Drive Selection screen

**Actual session:** 1

| Task | Status | File(s) |
|---|---|---|
| `install.sh` — apt packages + pip + systemd unit write | ✅ Written | `install.sh` |
| `install.sh` — Linux runtime tested on real host | ❌ Untested | `install.sh` |
| Flask app factory `create_app()` | ✅ Done | `app.py` |
| Blueprint registration (all routes) | ✅ Done | `app.py` |
| HTTP basic auth gate | ✅ Done | `system/auth.py` |
| `GET /api/drives` — lsblk JSON parser | ✅ Done | `routes/drives.py`, `system/drive_utils.py` |
| Drive Selection screen in SPA | ✅ Done | `static/app.js` |
| Tests: drives, auth, frontend, install.sh | ✅ 64 tests | `tests/test_drives.py`, `test_auth.py`, `test_frontend.py`, `test_install_sh.py` |

**Gap:** `install.sh` has not been run on a real Debian/Ubuntu host. `test_install_sh.py` mocks subprocess calls but no live test.

---

## Planned Session 2 — Storage backend selector screen + backend state routing

**Actual session:** 1–2

| Task | Status | File(s) |
|---|---|---|
| Backend selector screen (NonRAID / SnapRAID / MergerFS-only) | ✅ Done | `static/app.js` |
| Comparison table in UI | ✅ Done | `static/app.js` |
| `POST /api/backend` — saves backend to state | ✅ Done | `routes/backend.py` |
| Backend change warning modal (clears downstream state) | ✅ Done | `static/app.js` (`showModal`) |
| Pool → next screen routing by backend | ✅ Done | `static/app.js` |
| Tests: backend | ✅ 7 tests | `tests/test_backend.py` |

---

## Planned Session 3 — Pool config + mergerfs mount logic + fstab writer

**Actual session:** 1–2

| Task | Status | File(s) |
|---|---|---|
| Pool config screen (pool mount, cache mount, data mounts, write policy) | ✅ Done | `static/app.js` |
| `POST /api/pool` — saves pool config to state | ✅ Done | `routes/pool.py` |
| MergerFS mount string builder | ✅ Done | `system/mergerfs.py` (`build_mount_string`) |
| fstab entry formatter | ✅ Done | `system/apply_utils.py` (`_fstab_entry`) |
| Idempotent fstab append (marker-based) | ✅ Done | `system/apply_utils.py` (`_append_or_update_fstab`) |
| fstab backup before write | ✅ Done | `system/apply_utils.py` (`backup_fstab`) |
| Tests: pool, fstab backup | ✅ 12 tests | `tests/test_pool.py`, `test_apply_backup.py` |

---

## Planned Session 4 — SnapRAID config screen + snapraid.conf + sync/scrub timers

**Actual session:** 1–2

| Task | Status | File(s) |
|---|---|---|
| SnapRAID config screen (parity drive, sync time, scrub schedule) | ✅ Done | `static/app.js` |
| `sync_time` input with default "02:00" | ✅ Done | `static/app.js` |
| `POST /api/snapraid` — saves config to state | ✅ Done | `routes/snapraid.py` |
| `GET /api/snapraid/dry-run` — preview generated conf | ✅ Done | `routes/snapraid.py` |
| `snapraid.conf` generator (single + dual parity) | ✅ Done | `system/snapraid_conf.py` (`generate_conf`) |
| Sync systemd timer + service unit generation | ✅ Done | `system/systemd.py` (`snapraid_sync_units`) |
| Scrub systemd timer + service unit generation | ✅ Done | `system/systemd.py` (`snapraid_scrub_units`) |
| `write_units()` — writes unit files to disk | ✅ Done | `system/systemd.py` |
| Tests: snapraid routes, dry-run, systemd units | ✅ 23 tests | `tests/test_snapraid.py`, `test_snapraid_dryrun.py`, `test_systemd.py` |

---

## Planned Session 5 — NonRAID wizard screen + nonraid_install.py + PPA install + nmdctl SSE wrapper

**Actual session:** 2

| Task | Status | File(s) |
|---|---|---|
| NonRAID config screen (parity mode, filesystem, LUKS, turbo write, check schedule) | ✅ Done | `static/app.js` |
| Install status badge in UI | ✅ Done | `static/app.js` |
| nmdctl research — confirmed `create` is interactive-only | ✅ Done | `CONTEXT.md` |
| `GET /api/nonraid/status` → `nmdctl status -o json` | ✅ Done | `routes/nonraid.py` |
| `GET /api/nonraid/install` → `is_nonraid_installed()` | ✅ Done | `routes/nonraid.py` |
| `POST /api/nonraid/install` — PPA add + apt install (SSE stream) | ✅ Done | `routes/nonraid.py` |
| `POST /api/nonraid/config` — saves parity_mode, filesystem, luks, turbo_write | ✅ Done | `routes/nonraid.py` |
| `POST /api/nonraid/start/stop/mount/unmount` | ✅ Done | `routes/nonraid.py` |
| `POST /api/nonraid/check` — SSE stream `nmdctl check` | ✅ Done | `routes/nonraid.py` |
| `GET /api/nonraid/check/status` — parses `/proc/nmdstat` | ✅ Done | `routes/nonraid.py` |
| nmdctl wrappers module | ✅ Done | `system/nonraid_utils.py` |
| Tests: nonraid routes, nmdctl utils | ✅ 38 tests | `tests/test_nonraid.py`, `test_nonraid_utils.py` |

---

## Planned Session 6 — NonRAID array create flow (sgdisk guidance, mkfs per slot, nmdctl create/start/mount)

**Actual session:** 2 (partial) + 3

| Task | Status | File(s) |
|---|---|---|
| `POST /api/nonraid/create` — SSE stream `nmdctl create` | ✅ Done | `routes/nonraid.py` |
| Install button streams create output in UI | ✅ Done | `static/app.js` |
| Drive role assignment screen (`#nonraid-roles`) | ✅ Done | `static/app.js` |
| `POST /api/nonraid/roles` — validates + persists parity/data assignments | ✅ Done | `routes/nonraid.py` |
| sgdisk per-disk guidance in UI (`#nonraid-prep`) | ✅ Done | `static/app.js` |
| mkfs per-slot commands shown before `nmdctl create` | ✅ Done | `static/app.js` |
| `nmdctl create` command shown with interactive-mode note | ✅ Done | `static/app.js` |
| Confirmation checkbox gates Proceed button | ✅ Done | `static/app.js` |
| Browser E2E test of full NonRAID create flow | ❌ Not tested | — |
| Tests: role assignment route | ✅ 9 tests | `tests/test_nonraid.py` |

**Remaining gap:** Browser E2E test only. All wizard steps and API routes are implemented.

---

## Planned Session 7 — Cache mover config + mover script + systemd timer

**Actual session:** 1–2

| Task | Status | File(s) |
|---|---|---|
| Mover config screen (schedule time, age hours, min free pct) | ✅ Done | `static/app.js` |
| `POST /api/mover` — saves mover config to state | ✅ Done | `routes/mover.py` |
| Mover shell script generator | ✅ Done | `system/mover.py` (`generate_mover_script`) |
| Mover systemd timer + service unit generation | ✅ Done | `system/systemd.py` (`mover_units`) |
| Back button routing (backend-aware) | ✅ Done | `static/app.js` |
| Tests: mover | ✅ 7 tests | `tests/test_mover.py` |

---

## Planned Session 8 — Docker setup wizard screen + daemon.json writer + Docker install logic

**Actual session:** Skipped (explicit decision)

| Task | Status |
|---|---|
| All Docker setup tasks | ❌ Skipped — deferred indefinitely |

---

## Planned Session 9 — Docker dashboard panel (container list, stack list, log streaming)

**Actual session:** Skipped (explicit decision)

| Task | Status |
|---|---|
| All Docker dashboard tasks | ❌ Skipped — deferred indefinitely |

---

## Planned Session 10 — Share setup (Samba + NFS config writers)

**Actual session:** 1–2

| Task | Status | File(s) |
|---|---|---|
| Shares config screen (name, path, protocol, SMB guest, NFS hosts) | ✅ Done | `static/app.js` |
| `POST /api/shares` — saves shares list to state | ✅ Done | `routes/shares.py` |
| Samba `smb.conf` block generator | ✅ Done | `system/samba.py` (`generate_smb_block`) |
| NFS `exports` line generator | ✅ Done | `system/nfs.py` (`generate_export_line`) |
| Tests: shares | ✅ 12 tests | `tests/test_shares.py` |

---

## Planned Session 11 — Summary/Apply screen + SSE streaming terminal pane

**Actual session:** 2

| Task | Status | File(s) |
|---|---|---|
| Summary screen — file manifest preview | ✅ Done | `static/app.js` |
| `GET /api/summary` — returns `{files: [{path, content}]}` | ✅ Done | `routes/summary.py` |
| `build_file_manifest()` — collects all files to write | ✅ Done | `system/apply_utils.py` |
| `POST /api/apply` — SSE streaming terminal pane | ✅ Done | `routes/apply.py` |
| `apply_all()` — writes every file to disk | ✅ Done | `system/apply_utils.py` |
| SSE: fstab backup notification | ✅ Done | `routes/apply.py` |
| SSE: `snapraid-sync.timer` + `snapraid-scrub.timer` systemctl enable | ✅ Done | `routes/apply.py` |
| SSE: `FugginNAS-mover.timer` systemctl enable | ✅ Done | `routes/apply.py` |
| Auto-navigate to `#status` on "Apply complete" | ✅ Done | `static/app.js` |
| Tests: summary, apply SSE | ✅ 9 tests | `tests/test_summary_apply.py`, `test_apply_backup.py` |

---

## Planned Session 12 — Status dashboard (pool + parity panel + docker + shares)

**Actual session:** 2

| Task | Status | File(s) |
|---|---|---|
| Status screen layout | ✅ Done | `static/app.js` |
| `GET /api/status` | ✅ Done | `routes/status.py` |
| Pool panel: mount point, mounted/unmounted, used %, available bytes | ✅ Done | `system/status.py` |
| SnapRAID panel: last sync, sync result, errors, scrub, dirty files | ✅ Done | `system/status.py` |
| Run Sync Now / Run Scrub Now buttons | ✅ Done | `static/app.js` |
| NonRAID panel: nmdctl status in dashboard | ✅ Done | `system/status.py` |
| Docker panel | ❌ Skipped (Docker deferred) | — |
| Shares panel: live share status | ✅ Done | `system/status.py` |
| Tests: status | ✅ 5 tests | `tests/test_status.py` |

**Gap:** `GET /api/status` does not include NonRAID/nmdctl state. The status dashboard shows pool + SnapRAID when backend=snapraid, but no equivalent block for NonRAID backend.

---

## Planned Session 12 (continued) — NonRAID status panel

**Actual session:** 3

| Task | Status | File(s) |
|---|---|---|
| `GET /api/status` includes `nonraid` block when `backend=nonraid` | ✅ Done | `system/status.py` |
| NonRAID panel: live `state` from `nmdctl_status()` | ✅ Done | `system/status.py` |
| NonRAID panel: `parity_disks` and `data_disks` from stored state | ✅ Done | `system/status.py` |
| Tests: nonraid status panel | ✅ 5 tests | `tests/test_status.py` |

---

## Planned Session 13 — Theme system (CSS variable schema, 12 themes, theme picker)

**Actual session:** 3

| Task | Status | File(s) |
|---|---|---|
| CSS variable schema (9 custom properties on `:root`) | ✅ Done | `static/style.css` |
| 14 theme definitions (12 planned + tron-blue + tron-red) | ✅ Done | `static/style.css` |
| Theme picker component — fixed bottom-right, persists across screens | ✅ Done | `static/app.js` |
| `applyTheme()` — sets `data-theme` attribute on `<html>` | ✅ Done | `static/app.js` |
| `loadTheme()` — fetches saved theme on page load | ✅ Done | `static/app.js` |
| `GET /api/theme` — returns current theme (default: `"default"`) | ✅ Done | `routes/theme.py` |
| `POST /api/theme` — validates + persists theme name to state | ✅ Done | `routes/theme.py` |
| Theme persistence in state | ✅ Done | `routes/theme.py`, `system/state.py` |
| Tests: theme API | ✅ 8 tests | `tests/test_theme.py` |

---

## Summary Table

| Planned Session | Objective | Status |
| --- | --- | --- |
| 1 | install.sh + Flask skeleton + drive discovery | ✅ Done (install.sh untested on Linux) |
| 2 | Backend selector screen | ✅ Done |
| 3 | Pool config + mergerfs + fstab writer | ✅ Done |
| 4 | SnapRAID config + snapraid.conf + timers | ✅ Done |
| 5 | NonRAID wizard + PPA install + nmdctl wrappers | ✅ Done |
| 6 | NonRAID create flow (sgdisk + mkfs + nmdctl create) | ⚠️ Partial — E2E browser test only remaining |
| 7 | Mover config + script + timer | ✅ Done |
| 8 | Docker setup wizard | ❌ Skipped |
| 9 | Docker dashboard | ❌ Skipped |
| 10 | Shares — Samba + NFS | ✅ Done |
| 11 | Summary/Apply + SSE terminal | ✅ Done |
| 12 | Status dashboard | ✅ Done |
| 13 | Theme system | ✅ Done (14 themes) |

**Tests:** 214 passing, 0 failing (as of Session 3)

---

## Remaining Open Items

1. **Browser E2E test** — full NonRAID create flow (Session 6 last gap)
2. **install.sh live test** — run on a real Debian host or in a VM/container
3. **Docker** — if decision changes from "skipped"
