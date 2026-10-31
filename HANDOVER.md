# Cobham Match Day Cards: handover notes

Live site: https://athenaphysio.github.io/cobham-matchday/
Repo: athenaphysio/cobham-matchday (GitHub Pages, branch main, root folder)

## What it does
A volunteer opens the site each week, picks the fixture, picks or pastes the team,
and presses "Save all four cards". That gives a zip of four 1080 x 1350 PNGs for an
Instagram carousel: Match day, Forwards, Backs, Replacements and staff.

## Where things live
- `index.html`: the whole page. Cards are drawn on a canvas in `renderCard`.
- `data/site.json`: squad, fixtures, clubs (opposition badges), inbox (unnamed photos), settings.
  - squad entry: `{name, first, last, role: "player"|"coach", photo: "img/photos/X.png"}`
  - fixture: `{round, date, opponent, home, ko, venue, competition}`
  - settings.main: badge, backgrounds per card, `subsCount` (3 for 1st XV, 7 for 2nd XV)
- `img/photos/`: named headshots. `img/unnamed/`: cut-outs waiting for a name.
- `img/logos/`: opposition badges (dark lettering badges sit on white rounded tiles).
- `img/bg/`: card backgrounds. bg-1 for Match day and Forwards, bg-2 Backs, bg-3 Replacements.
- Volunteer edits made on the site are saved only in their browser. The Setup tab has
  "Copy changes to send to David", which produces JSON to merge into `data/site.json`.

## Design rules agreed with David
- Century Gothic (falls back to embedded TeX Gyre Adventor).
- First name small in gold above surname in white.
- 1st XV bench is 3 replacements. Up to 5 staff, smaller tiles, one row, labelled STAFF.
- Titles sit level with the badge; tiles kept clear of the 26/27 and the sponsor strip.
- No em or en dashes in any copy.

## Adding new headshots
Run `python3 tools/headshots.py OUT_DIR photos...` (handles white sheet or green screen,
HEIC included), check the result on a dark background, then either save as
`img/photos/SURNAME.png` and set that player's `photo`, or put it in `img/unnamed/`
with an `inbox` entry if the name is not known. Green screen gives the cleanest edges.

## Status at 31 Oct 2026
- 54 names in the squad. 29 cut-outs (photo-01 to photo-29) waiting to be named.
- All 11 opposition badges done. Fixtures from the August league list, 3pm kick-offs.
