# Job Search Claude Project — Setup Guide

Four files make up the project:

| File | Where it goes | What it is |
|---|---|---|
| `project-instructions.md` | Project → **Instructions** (paste the text) | Rules + commands (FIND, RESEARCH, TAILOR, COVER, TRACK, UPDATE, PREP) |
| `career-inventory.md` | Project → **Knowledge** (upload) | Master record of everything you've done. The only source of facts about you |
| `preferences.md` | Project → **Knowledge** (upload) | Targets, dealbreakers, salary, writing voice |
| `Job_Search_Tracker.xlsx` | Keep on your computer as your working tracker; upload a copy to Project → **Knowledge** weekly | Application log with dropdowns, auto follow-up dates, and a dashboard |

## Setup (about 15 minutes)
1. Fill in the `[ADD]` / `[CONFIRM]` items in `career-inventory.md` and `preferences.md`. Metrics matter most.
2. On claude.ai: **Projects → Create project** → name it "Job Search".
3. Paste the part of `project-instructions.md` below the line into **Instructions**.
4. Upload `career-inventory.md`, `preferences.md`, `Job_Search_Tracker.xlsx` to **Knowledge**. If .xlsx isn't accepted, open it in Excel → File → Save As → CSV and upload the CSV.
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
- **Keep what you actually sent:** save every submitted PDF with the naming convention in `preferences.md` and record the filename in the tracker's *Resume File* column. That way you always know which version a company saw before an interview.

## How tracking works
Claude Projects can't edit files, so **your real tracker is `Job_Search_Tracker.xlsx` on your computer**. It has an Applications sheet (dropdowns, follow-up date that turns red when due), a Dashboard (totals, follow-ups due, counts by stage), and a How to Use sheet. The flow:
1. `TRACK applied to Baird FP&A analyst today`. Claude gives you a ready-to-paste row.
2. Click the first empty cell in column A of the Applications sheet and paste. It fills across.
3. About once a week, replace the tracker in Project Knowledge with your current file, then run `TRACK REVIEW` for follow-ups and stale entries.

**Stage values** (keep them consistent so reviews work):
`Found → Researching → Tailoring → Applied → Screening → Interviewing → Offer → Accepted`, or `Rejected / Withdrawn / Ghosted`.

## A typical job, start to finish
1. `FIND FP&A analyst roles in Tampa`. Pick one.
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
