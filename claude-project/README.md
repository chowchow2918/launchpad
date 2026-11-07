# Job Search Claude Project — Setup Guide

Four files make up the project:

| File | Where it goes | What it is |
|---|---|---|
| `project-instructions.md` | Project → **Instructions** (paste the text) | Rules + commands (FIND, RESEARCH, TAILOR, COVER, TRACK, UPDATE, PREP) |
| `career-inventory.md` | Project → **Knowledge** (upload) | Master record of everything you've done. The only source of facts about you |
| `preferences.md` | Project → **Knowledge** (upload) | Targets, dealbreakers, salary, writing voice |
| `tracker.csv` | Project → **Knowledge** (upload) *and* keep a working copy in Google Sheets/Excel | Application log |

## Setup (about 15 minutes)
1. Fill in the `[ADD]` / `[CONFIRM]` items in `career-inventory.md` and `preferences.md`. Metrics matter most.
2. On claude.ai: **Projects → Create project** → name it "Job Search".
3. Paste the part of `project-instructions.md` below the line into **Instructions**.
4. Upload `career-inventory.md`, `preferences.md`, `tracker.csv` to **Knowledge**.
5. Turn on **web search** in chats (needed for FIND and RESEARCH).
6. Test it with a new chat: `RESEARCH Northwestern Mutual`.

## How the resume stays current
Your resume changes, so the project doesn't store a resume at all. It stores an **inventory** (a superset of everything you've done), and every resume is generated fresh from it.

- **Something new happens** (new job, cert, GPA, project, a number you remembered):
  in any project chat, type `UPDATE started CFA Level I prep, exam Aug 2027`.
  Claude asks follow-ups, then gives you the new section, the changelog line, and the new date.
- **Paste** it into your local `career-inventory.md` → in Project Knowledge, **delete the old file and upload the new one** (project files don't update themselves).
- **Never delete old experience.** Mark it `[archived]`. Claude will leave it off resumes but can still use it for stories.
- **The date stamp is the safety net:** if the inventory is more than 60 days old, Claude will ask whether anything changed.
- **Monthly 5-minute check:** GPA, hours/metrics at current job, certifications in progress.
- **Keep what you actually sent:** save every submitted PDF with the naming convention in `preferences.md` and record the filename in the tracker's *Resume Version* column. That way you always know which version a company saw before an interview.

## How tracking works
Claude Projects can't edit files, so the **real tracker lives in Google Sheets or Excel** (import `tracker.csv`). The flow:
1. `TRACK applied to Baird FP&A analyst today, used tailored resume v1`. Claude gives you a ready-to-paste row.
2. Paste it into your sheet.
3. About once a week, export the sheet as CSV and replace `tracker.csv` in Project Knowledge, then run `TRACK REVIEW` for follow-ups and stale entries.

**Stage values** (keep them consistent so reviews work):
`Found → Researching → Tailoring → Applied → Screening → Interviewing → Offer → Accepted`, or `Rejected / Withdrawn / Ghosted`.

## A typical job, start to finish
1. `FIND FP&A analyst roles within 60 min of Whitewater`. Pick one.
2. `RESEARCH [company] [link]`. Read the brief. Red means skip.
3. `TAILOR [paste job description]`. Edit the draft and correct anything off.
4. `COVER [company]`. Edit it, then check the "double-check" list.
5. Export to PDF yourself and apply yourself.
6. `TRACK applied …` and paste the row.
7. When you get an interview: `PREP [company]`.

## Tips
- **Paste the job description text**, don't just link it. Many job sites block automated reading.
- Start a **new chat per company**. It keeps context clean, and the project files carry over.
- If Claude ever states something about you that isn't in the inventory, call it out. Rule 1 says it shouldn't.
