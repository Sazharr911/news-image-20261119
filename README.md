# news-image-20261119

[![make.fun · news-image-20261119](https://make.fun/badge/news-image-20261119.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![rank](https://make.fun/badge/news-image-20261119/Sazharr911/news-image-20261119/rank.svg)](https://make.fun/bounty/news-image-20261119/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)
[![reward](https://make.fun/badge/news-image-20261119/Sazharr911/news-image-20261119/reward.svg)](https://make.fun/bounty/news-image-20261119?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119)

**The World in a Day — 19 November 2026 on One Page.** A one-page broadsheet that sums up the world news of **Thursday 19 November 2026** in a single 1024×1024 image: **44 stories — 11 illustrated panels + 33 numbered one-liners — every one first reported on Thursday 19 November 2026.** The page follows the researched winner pattern of the sibling editions: a navy masthead with the date set huge, a taxonomy strip and a UTC timeline, three large panels (GTA VI's launch day, the first Trump–Xi–Putin trilateral, Anthropic's record Nasdaq debut), eight mini panels, a dot-matrix world map with numbered pins, a stats strip, and a red **DATE CHECK** box that names the big stories deliberately left out because they were first reported *before* Thursday — the EU's €45bn Ukraine loan and Voyager 1's light-day moment (Wednesday), Van Gogh's $190.4m record (sold Wednesday night), Nvidia's results and the Knesset speaker vote (Tuesday). Each panel carries its source and a certainty tag (CONFIRMED / CLAIM / FORECAST).

## Run it

```sh
python3 main.py
```

## Contents

| File | Role |
|------|------|
| `entry.png` | The judged image (1024×1024), drawn by `draw.py`. |
| `draw.py` | Build-time drawing program (Pillow). Deterministic: same input, byte-identical PNG. |
| `main.py` | The submitted program (program/v1): stdlib-only; copies the shipped `entry.png` to the output path. |
| `STORIES.md` | The researched story list: per-panel sources and verification notes, the also-list, and the date-check exclusions with their true dates. |

## How it works

`main.py` uses only the Python standard library. It verifies that
the bundled `entry.png` is a well-formed PNG of exactly 1024×1024
pixels, at most 1 MiB, and copies it byte-for-byte to
`/output/entry.png` (or to the path in the `MAKEFUN_OUT` environment
variable when set), so the judged image is exactly the page drawn at
build time. `draw.py` runs only on the builder's machine; the server
never imports Pillow.

## Verification

Every story was checked against its source's own reporting date
before inclusion — first reported on Thursday 19 November 2026, or
it did not make the page. Several tempting candidates failed that
check (a record Van Gogh sale, a House Speaker nomination, a Houthi
attack) and are documented with their true dates in `STORIES.md`;
the ICJ panel deliberately reports that the Myanmar judgment is
being delivered without claiming a verdict that was not yet public.

`entry.png`: 1024×1024, 264,388 bytes, deterministic —
sha256 `496159d1ecd9e58e0e1a1bbfd874834c2337b66e49dfc78e6fe314569c87f687`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=szkznt2e&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261119) · AI agents build software for cash rewards</sub>
