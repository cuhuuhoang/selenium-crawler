# Selenium crawler

Simple Selenium setup to scrape the target VnExpress article using a Dockerized Chrome.

## Quick start (plain Docker)

1) Install deps:
```bash
pip install -r requirements.txt
```

2) Full automated run (build image → start Selenium → download HTML → extract article + comments → stop Selenium):
```bash
bash run.sh [URL]
```
`HTML_FILE` and `OUTPUT_JSON` can be overridden via env vars, e.g. `HTML_FILE=page.html OUTPUT_JSON=article.json bash run.sh`.
`WAIT_SECONDS` sets how long to wait for Selenium readiness before proceeding (default 120s).
`URL` arg overrides the article to fetch; defaults to the requested VnExpress article if omitted.

Manual steps (if preferred):
```bash
docker build -t selenium-chrome .
docker run -d --rm --name selenium-chrome -p 4444:4444 -p 7900:7900 --shm-size=2g selenium-chrome
python3 crawler.py --url <URL> --download --html-file page.html
python3 crawler.py --url <URL> --extract --html-file page.html --output article.json
docker stop selenium-chrome
```

### Windows (Docker Desktop)

1) Install Python (on PATH), Docker Desktop, and `pip install -r requirements.txt`.
2) Run:
```bat
run.bat [URL]
```
Environment overrides: set `HTML_FILE`, `OUTPUT_JSON`, `WAIT_SECONDS` before calling. The `URL` argument is optional; it defaults to the requested VnExpress article.

- The script connects to Selenium at `http://localhost:4444/wd/hub` (override with `SELENIUM_ENDPOINT`).
- `crawler.py --download` saves full HTML (scrolls, clicks “Xem thêm” buttons to load more comments) to a file; `--extract` parses that file for article fields and comments.
- Selectors are tailored to current VnExpress markup (`title-detail`, `fck_detail`, comment blocks under `#list_comment`). Adjust in `crawler.py` if the site changes.
- Concurrency: each Python script/process should create its own `WebDriver`. The provided standalone Chrome container allows one session at a time (requests queue). For true parallelism, run multiple containers or a Selenium Grid with more nodes/sessions.
