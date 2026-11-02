import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

TIMEOUT = 15
MAX_BYTES = 2_000_000
MAX_CHARS = 12_000
MAX_REDIRECTS = 3
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CareerReady/1.0)"}


class ScrapeError(RuntimeError):
    """Raised for any problem fetching or reading a job page."""


def check_url(url):
    """Allow only public http(s) addresses, so the app can't be pointed at your own network."""
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ScrapeError("Enter a full http(s) link, like https://company.com/jobs/123")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 443)
    except socket.gaierror:
        raise ScrapeError("Could not find that website.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ScrapeError("That address is not a public website.")


def fetch_html(url):
    for _ in range(MAX_REDIRECTS + 1):
        check_url(url)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                                allow_redirects=False, stream=True)
        except requests.exceptions.RequestException:
            raise ScrapeError("Could not reach that page.")

        if resp.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, resp.headers.get("Location", ""))
            continue
        if resp.status_code in (401, 403, 429):
            raise ScrapeError("The site blocked the request. Paste the description manually.")
        if resp.status_code != 200:
            raise ScrapeError(f"The page returned an error ({resp.status_code}).")

        content = b""
        for chunk in resp.iter_content(65536):
            content += chunk
            if len(content) > MAX_BYTES:
                break
        return content.decode(resp.encoding or "utf-8", errors="replace")
    raise ScrapeError("Too many redirects.")


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


def job_from_json_ld(soup):
    """Many job boards embed the posting as structured data. Use it when it's there."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except ValueError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data])
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                company = item.get("hiringOrganization") or {}
                if isinstance(company, dict):
                    company = company.get("name", "")
                description = html_to_text(item.get("description", ""))
                return f"{item.get('title', '')}\n{company}\n\n{description}".strip()
    return ""


def extract_job_text(html):
    soup = BeautifulSoup(html, "html.parser")
    text = job_from_json_ld(soup)
    if not text:
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_CHARS]


def scrape_job(url):
    text = extract_job_text(fetch_html(url))
    if len(text) < 200:
        raise ScrapeError(
            "Found very little text. The page probably needs JavaScript or a login. "
            "Paste the description manually."
        )
    return text