# PTorrent — curses GUI

**License:** LGPL-3.0-or-later. A native-`curses` face over
`core/python/ptorrent_core` (ncurses / PDCurses / the platform's own). Stdlib +
the core, no other dependencies. **All on-screen text is Unicode** so equations
read on a single line (`√(pmra² + pmdec²) / max(parallax, 0.001)`, `d⋆ ≤ J < 1`,
`Σ|∇I| / Σ I`). Editable field *values* stay ASCII — the core's `j_expr` parser
wants `sqrt`, `**`, `<=` — and a read-only Unicode echo is shown beside them.

```
python3 -m ptorrent_gui [--engine DIR] [--out DIR] [--wizard]
```

- **shell** — a menu bar (`F1`) over a content area. `File ▸ New` opens the
  wizard; `File ▸ Open` previews an existing `.ptorrent`; `Help ▸ Keys / About`.
- **`--engine DIR`** attaches a live `Engine`: the wizard's User-Information tab
  can verify your ORCID against `pub.orcid.org`, and on save the job can go
  straight to the core (`engine.add`).
- **`--wizard`** skips the shell and opens `File ▸ New` directly.

## Package layout

```
ptorrent_gui/
├── __main__.py          python3 -m ptorrent_gui
├── shell.py             the menu-driven shell (Shell); polls snapshot()/events(),
│                        evaluates section alarms when --engine is attached
├── menu.py              MenuBar — dropdown menu bar widget
├── config.py            ~/.config/ptorrent/gui.json — every console setting
├── settings.py          Settings ▸ Preferences (SettingsScreen)
├── alarms.py            section-alarm rule engine + bell / notify-send firing
├── common/
│   ├── geometry.py      percentage-of-terminal Rect
│   ├── theme.py         legacy-BIOS palette + box drawing
│   ├── mathtext.py      ASCII math → Unicode  (display only)
│   └── dialog.py        message_box · confirm · fault_dialog · tooltip
└── wizard/              ── File ▸ New ──
    ├── wizard.py        WizardScreen · run_embedded() · run_standalone()
    ├── model.py         the four-tab field ladder → answers → .ptorrent
    ├── faults.py        collect(answers) — non-fatal fault list
    ├── profile.py       User-Information persistence (auto-input)
    └── test_wizard.py
```

## The wizard — `File ▸ New`

Rufus-style: every option on screen, laddered, split across four tabs. Legacy
BIOS layout — the field ladder on the left, an **Item Specific Help** panel on
the right that **grows past ~170 columns and collapses under 90** (or on `s`).
All geometry is a percentage of the terminal, so a maximised window and an 80×24
one lay out from the same numbers.

| Tab | Contents |
|-----|----------|
| **Dataset** | name · type · colour · description · tags · output bin · dataset home URL · seed-URL list · license · citation · `distribution.seed_listing` |
| **Crawler options** | the whole `crawl` block — resolution ladder (api-first), follow/scope, politeness (UA, robots policy, delays, concurrency), HTTP (timeout, byte cap, conditional GET, range resume). **Unlocks in-situ evaluation:** pick an algorithm — `j_expr`, a column ratio, a built-in `σ_face_*` tabular reduction, or an `img_*` image reduction (brightness / area / entropy / edge density / gradient energy) — set its params and `max_rows`. The sidebar shows the `d⋆`, `Ω_ZS` constants and the σ-face band table. This is how you evaluate 196 GB you never download: ≈5 000 records = one API rate-limit window. |
| **Cybersecurity** | self-identify what the data (or its output) is — the answers drive `classification`, `level`, `TLP`, and `security.labels` (CWE / CVSS / ATLAS). The **auth-provenance bindings** table ties each sensitive source (an S3 prefix, a host, a local dataset path) to how it is authenticated (`orcid-session` / `oauth` / `institutional` / `api-key`). Report-don't-block byte scan. The derived classification shows live in the sidebar; the core re-derives it authoritatively on `add()`. |
| **User information** | name · ORCID (+ verify) · email · affiliation · default UA · default delay · SMTP. **Save profile** persists to `~/.config/ptorrent/wizard_profile.json` and pre-fills every future launch. |

### Keys

`F1` menu · `n` new · `o` open · `q` quit — in the wizard: `Tab` / `1`–`4`
section · `↑↓` fields · `←→` change · `↵` edit · `Space` toggle · `s` sidebar ·
`t` tooltips · `F8` check · `F9` preview · `F10` build & save · `Esc` back.

### Tooltip mode

`t` toggles floating tooltips — a small popup anchored to the focused field with
its one-line hint, valid values / range, and any fault attached to that field.
Useful when the sidebar is collapsed on a narrow terminal. The preference is
saved with the User-Information profile.

### Faults are handled, never fatal

A malformed field, a contradictory choice, an unparseable `j_expr`, a
`.ptorrent` that will not validate — none of it crashes the wizard. Every fault
is collected and shown in a dialog:

- **`F8`** runs the check on demand.
- **`F10`** (build) runs it first; **errors block the write**, warnings do not —
  the dialog then offers *Fix selected* (jumps to the offending field),
  *Save anyway* (warnings only), or *Dismiss*.
- The footer shows a live `✖ n error(s) ▲ m` count; each offending field row
  carries a `✖` / `▲` marker; in tooltip mode the field's faults appear in its
  popup.

Checks include: empty name, no crawl source, seed URL without a scheme,
evaluation with no J method, `j_expr` syntax errors, `j_expr` columns not in
`j_expr_cols`, malformed `fn_params`, Level-3 without an embargo date or contact
ORCID, bad CWE / CVSS / ORCID formatting, a TLP override that lowers the derived
marking, and unknown auth-provenance kinds — plus every warning the core's own
builder returns.

## Test

```sh
python3 -m unittest ptorrent_gui.wizard.test_wizard
```

Geometry math, the answers → `.ptorrent` mapping (through the core's
authoritative builder), the Unicode helper, and a headless render pass across
tab and window sizes. The interactive UI needs a real terminal.

## Settings ▸ Preferences

`Settings ▸ Preferences` in the menu bar (or `p` at the shell) opens every
user-adjustable console setting — text boxes, on/off toggles, `‹cycle›` choices.
Persisted to `~/.config/ptorrent/gui.json`; `F10` saves, `Esc` backs out (asking
first if there are unsaved changes).

| Group | Settings |
|-------|----------|
| **Notifications** | master enable · channel (`bell` / `desktop` / `both` / `off`) · per-event toggles: job complete, job error, embargo lifted, access request received, grant received, vote received, phonebook entry stale/dead |
| **Section alarms** | the rule list (below) |
| **Display** | theme (`bios-blue` / `mono`) · sidebar (`auto` / `always` / `never`) · tooltips on by default · confirm on quit · Unicode glyphs (`auto` / `on` / `off`) |
| **Defaults for new .ptorrent** | politeness delay · User-Agent — pre-fill the wizard's Crawler tab |
| **Paths** | output directory · engine root · poll interval |
| | **Reset all to defaults** |

### Section alarms (heartbeats)

User-defined periodic / conditional alerts, evaluated against the live
`snapshot()` while the shell is attached to an engine (`--engine`). The shipped
rule **still-alive ping** dings once every 3 hours for as long as any job is
`RUNNING` — a 12-day download keeps telling you it is still going. `↵` on
*Alarm rules* opens the editor: `a` add · `d` delete · `↵` edit a rule.

Per-rule fields:

| field | meaning |
|-------|---------|
| `name` · `enabled` | label · on/off |
| `when` | `periodic_while_running` (ding every *interval* while any/each job runs) · `job_running_longer_than` (fire once past *threshold*, then every *interval* if `repeat`) · `job_idle_for` (progress not advancing for *threshold*) · `error_count_over` (job error items > *count*) · `all_done` (fire once when every job is DONE) |
| `every` (n, unit) | the interval — `minutes` / `hours` / `days` |
| `threshold` (n, unit) | the age / idle bound for the `longer_than` and `idle_for` conditions |
| `count` | the bound for `error_count_over` |
| `scope` | `any_job` (one ding for the fleet) or `each_job` |
| `action` | `bell` (terminal `\a`) · `desktop` (`notify-send` / `kdialog`) · `status` (status-line only) |
| `repeat` | keep firing on the interval, or once |

Alarm `action` and the notification `channel` compose: a `bell` action with
`channel: both` rings *and* pops a desktop notification.

## Coming next

The rest of the console face — job list, live crawl detail, phonebook browser,
seeds, access-request pane — mounting into the shell over the same
`Engine.snapshot()` / `events()` surface.
