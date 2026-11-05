# CareerReady

A personal job-application helper. Give it a job link or description and it scores your fit, rewrites your resume for the role, drafts a cover letter, and can run a mock interview. Built as a learning project.

## What it does

- **Profile**: save your contact details and resume once (PDF upload or pasted text).
- **Process a job**: paste a description or a link. A pipeline runs four steps and saves each result:
  1. fetch the page (if you gave a link)
  2. score the fit, with strengths, gaps and red flags
  3. tailor the resume, then fact-check it against the original and rewrite if the reviewer finds invented claims (up to two rewrites)
  4. write a cover letter
- **Track jobs**: status per job, retry a failed run, redo just the resume or the letter, view the event log.
- **Export**: resume and cover letter as Word, PDF or text.
- **Mock interview**: an interviewer asks questions for a chosen job, follows up on vague answers, and gives feedback at the end.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then put your OpenRouter key in .env
streamlit run app.py
```

The default model is `openrouter/free`. Set `OPENROUTER_MODEL` in `.env` to use another.

## Tests and evals

```bash
python -m pytest                    # unit tests, no network or API key needed
python -m evals.run_evals           # scoring quality against the real model
python -m evals.run_evals --tailor  # also checks the rewritten resume for invented numbers
```

The unit tests replace the model and the web with fakes. The evals call the real model, so results vary a little between runs.

## How it is put together

```
app.py            page navigation
views/            Jobs, Interview and Profile pages
pipeline.py       the step runner: skips finished steps, retries, logs events
fit.py tailor.py review.py cover.py   one model task each
interviewer.py    interview questions and feedback
scraper.py        fetches job pages, with protection against internal addresses
documents.py      Word and PDF export
db.py             SQLite storage and small migrations
llm_client.py     OpenRouter client with retries and JSON extraction
prompts.py        all prompts
```

Some design choices:

- Each pipeline step saves its result immediately, so a failure later on never loses earlier work, and "Retry" continues where it stopped.
- Model and network errors are retried. Permanent errors (a blocked page) are not. Real bugs are not caught.
- The scraper only fetches public addresses and re-checks every redirect, so the app can't be pointed at the local network.
- Job text, resumes and interview answers are treated as untrusted data in every prompt.

## Limitations

- Free models vary in quality. They can miss an invented claim, or flag a harmless one. Always read the resume before sending it.
- Scanned (image-only) PDFs have no text to extract. Paste the text instead.
- Sites that need JavaScript or a login (LinkedIn, Indeed and similar) can't be fetched. Paste the description.
- PDF export uses built-in fonts, so characters outside Western European languages become `?`. Use the Word export for those.
- Interviews live in the browser session and are lost on refresh.

## How this was built

TODO: write this part yourself, honestly and in your own words. Say what you wrote, what you learned, and which parts you got help with (for example AI assistance, tutorials, or the original project this grew out of).
