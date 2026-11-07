# Tool Hour AI: Autopilot

Runs **every day at 1:45 PM India time (right after the free Gemini quota resets) on GitHub's servers**, so your laptop can be closed.

```
learn  →  plan  →  render  →  host  →  schedule
 │         │        │          │        └─ Buffer API → Instagram Reel + YouTube Short
 │         │        │          └─ GitHub Pages (public video URL Buffer can fetch)
 │         │        └─ real screenshot of the tool's website + branded scenes + AI voice (Gemini TTS) → MP4
 │         └─ Gemini writes the script, steered by what performed best, checked by safety rules
 └─ reads real views/likes/comments/shares from Buffer → data/weights.json + data/REPORT.md
```

## The team (each a focused AI role, all free)
| Role | When | What they do |
|---|---|---|
| **Trend Scout** | weekly | Searches the live web: rising AI tools, questions owners are asking, formats working now, what to avoid → `data/trends.json`, `data/SCOUT.md` |
| **Creative Director** | daily | Pitches 4 concepts in different formats, scores them hard (stop-scroll, curiosity, emotion, clarity, freshness), picks the winner |
| **Scriptwriter** | daily | Writes the winning concept in the brand voice, with safety rules |
| **Script Editor** | daily | Scores hook/pacing/payoff/emotion/clarity; rewrites anything under 8/10 |
| **Fact-Checker** | daily | Verifies every claim with Google Search; fixes or rejects the script |
| **Video Producer** | daily | Real site screenshot, kinetic captions, colour scenes, transitions, music, SFX, clean voice |
| **Publisher** | daily | Hosts the video and queues it in Buffer for Instagram + YouTube (AI label on) |
| **Data Analyst + Growth Analyst** | daily / weekly | Pulls real stats, re-weights formats/tools/hooks, writes insights + next moves |
| **Experiment Manager** | daily | Half the videos test one production choice (voice, music tempo, length) against the current default |
| **Strategist** | weekly | Rewrites `hooks.md`, `past-winners.md`, `next-week-plan.md`; adds/retires formats; promotes experiment winners (needs ≥3 videos and ≥15% lift); sets 1–2 videos/day. Logged in `data/STRATEGY_LOG.md`. Never touches code or safety rules. |
| **Health Monitor** | daily | Alerts you (GitHub issue) when a Buffer post fails or a run doesn't finish |
| **Autopilot Engineer** | weekly (Claude on your Mac) | Reads the runs and alerts, fixes bugs, tests, pushes. Never changes safety rules, posting approval or secrets. |

## Safety Governor (overrides every agent)
- **Auto-posts only when every check passes** (fact-check, sound check, editor ≥6); otherwise the video waits in Buffer as a draft.
- **Warm-up:** 1 post/day for the first 14 days; never more than **2/day** after that.
- **No duplicates:** rejects scripts too similar to the last 60 videos.
- **Clean captions:** max 5 hashtags, no links, AI voiceover + not sponsored disclosure; platform AI labels on.
- **Auto-pause** (and alert you) if 2+ posts fail in a week, or the last 3 posts get almost no views (possible reach limit).

## The company
- **CEO** (weekly): reads every report, writes `data/CEO_MEMO.md` (memo, priorities, engineering requests),
  **hires** specialist agents when there's a gap and **lets go** of ones that don't help → `data/agents/`, `data/ORG_CHART.md`.
- **Hired specialists** advise at one stage (`concept`, `script` or `weekly`). Advice only: no code, posting, spending,
  or rule changes. Limits: max 6 specialists, 1 hire/week, 2 per stage (to stay inside the free AI quota).
- **Autopilot Engineer** (Claude on your Mac, weekly) builds the CEO's engineering requests and fixes bugs.

## Professor Koko (the teaching koala)
- Designed with **Google Gemini** (`assets/koala/koko_design.png`) and animated with **Veo** in the Gemini app (Pro plan, no extra cost).
- Veo clips in `assets/koala/` (hello, explain, point, wow, think, bye...) are keyed off green and play in every scene,
  Koko standing beside the lesson like a teacher. A missing clip falls back to the Gemini design, bobbing to the beat.
- Background music is original **Gemini-made** music in `assets/music/` (synth music only as a fallback).
- Add more clips/tracks any time: drop `<action>.mp4` into `assets/koala/` or an mp3 into `assets/music/`.

## The Auditor (engineering, runs on GitHub after every daily run)
- **Checks** every file compiles, workflows and config are valid, 22 safety tests pass, and an offline test video renders (1080x1920 with sound).
- **Fixes bugs**: reads the failed run's error, asks Gemini for the smallest patch, re-runs every test, and pushes only if all pass. Otherwise it undoes the patch and opens an issue.
- **Builds CEO requests**: at most one unchecked engineering request from `data/CEO_MEMO.md` per week, under the same test gate.
- **Rollback guard**: if the next daily run fails on an Auditor commit, it reverts that commit and opens an issue.
- **Can never edit** `governor.py`, `tests/`, `knowledge/`, the workflows or `config.json`, so it can't weaken safety. Log: `data/AUDIT_LOG.md`.

## Controls (edit `autopilot/config.json`)
| Setting | Meaning |
|---|---|
| `require_approval` | `true` = videos arrive in Buffer as **drafts**; tap *Schedule* in the Buffer app (10 sec). `false` = fully automatic posting. |
| `videos_per_run` | Videos made per day (keep at 1–2 to stay safe from "mass-produced content" flags). |
| `post_to` | `["instagram","youtube"]` |
| `voice_name` | Gemini voice (e.g. Kore, Puck, Charon, Aoede). |
| `explore_rate` | Share of videos that try a new style instead of repeating the current winner. |

## Manual buttons (GitHub → Actions → "Tool Hour AI autopilot" → Run workflow)
- **check**: tests both API keys, posts nothing
- **video-only**: makes a video you can download, posts nothing
- **full**: the normal daily run

## You get notified
- Every **Monday**: a GitHub issue with the performance report (GitHub emails you).
- If a run **fails**: a GitHub issue with the link to the error.

## Secrets (set once, never stored in files)
- `GEMINI_API_KEY`: from https://aistudio.google.com/apikey
- `BUFFER_API_KEY`: from Buffer → Settings → API

## Safety built in
- Scripts are rejected if they contain income claims, prices, or banned phrases (`plan.lint`).
- Max 1 video/day by default, rotating pillars and never repeating a tool within 30 videos.
- Every video and caption says "AI voiceover"; captions say "not sponsored".
- Old video files are deleted from hosting after 21 days (Buffer already published them).
