# Tool Hour AI: Autopilot

Runs **every day at 9:00 AM India time on GitHub's servers**, so your laptop can be closed.

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
