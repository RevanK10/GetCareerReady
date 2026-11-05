import pytest

import scraper
from scraper import ScrapeError, check_url, extract_job_text, scrape_job


@pytest.mark.parametrize("url", [
    "http://localhost/x", "http://127.0.0.1", "http://10.0.0.5", "http://192.168.1.1",
    "http://169.254.169.254/latest", "http://[::1]/", "file:///etc/passwd", "ftp://x.com", "notaurl",
])
def test_check_url_blocks_non_public_addresses(url):
    with pytest.raises(ScrapeError):
        check_url(url)


def test_check_url_allows_public_ip():
    check_url("https://93.184.216.34/jobs")


def test_check_url_unknown_host(monkeypatch):
    import socket

    def fail(*args, **kwargs):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(scraper.socket, "getaddrinfo", fail)
    with pytest.raises(ScrapeError, match="find that website"):
        check_url("https://nowhere.example")


def test_extract_prefers_json_ld():
    html = """<script type="application/ld+json">{"@type":"JobPosting","title":"Data Engineer",
    "hiringOrganization":{"name":"Acme"},"description":"<p>Build <b>pipelines</b></p>"}</script><body>junk</body>"""
    text = extract_job_text(html)
    assert text.startswith("Data Engineer\nAcme")
    assert "pipelines" in text and "junk" not in text


def test_extract_finds_posting_inside_graph():
    html = '<script type="application/ld+json">{"@graph":[{"@type":"WebSite"},{"@type":"JobPosting","title":"T","hiringOrganization":{"name":"C"},"description":"D"}]}</script>'
    assert extract_job_text(html) == "T\nC\n\nD"


def test_extract_fallback_removes_page_chrome_and_survives_bad_json():
    html = ("<script type='application/ld+json'>{bad json</script><nav>Home</nav>"
            "<script>var x=1</script><main><h1>Backend Dev</h1><p>Write Python.</p></main><footer>(c)</footer>")
    assert extract_job_text(html) == "Backend Dev\nWrite Python."


class FakeResponse:
    def __init__(self, status, headers=None, body=b""):
        self.status_code, self.headers, self.encoding, self._body = status, headers or {}, "utf-8", body

    def iter_content(self, size):
        yield self._body


@pytest.fixture
def web(monkeypatch):
    """Fake DNS and HTTP: public.test is public, internal.test resolves to a private address."""
    pages = {}
    monkeypatch.setattr(scraper.socket, "getaddrinfo", lambda host, port: [
        (None, None, None, None, ("10.0.0.1" if host == "internal.test" else "93.184.216.34", 0))])
    monkeypatch.setattr(scraper.requests, "get", lambda url, **kw: pages[url])
    return pages


LONG_PAGE = ("<p>" + "word " * 100 + "</p>").encode()


def test_scrape_follows_redirects(web):
    web["http://public.test/a"] = FakeResponse(302, {"Location": "/b"})
    web["http://public.test/b"] = FakeResponse(200, body=LONG_PAGE)
    assert len(scrape_job("http://public.test/a")) > 200


def test_scrape_blocks_redirect_to_internal_address(web):
    web["http://public.test/a"] = FakeResponse(302, {"Location": "http://internal.test/secret"})
    with pytest.raises(ScrapeError, match="not a public"):
        scrape_job("http://public.test/a")


def test_scrape_redirect_loop(web):
    web["http://public.test/a"] = FakeResponse(302, {"Location": "/a"})
    with pytest.raises(ScrapeError, match="redirects"):
        scrape_job("http://public.test/a")


@pytest.mark.parametrize("status, message", [(403, "blocked"), (404, "404")])
def test_scrape_http_errors(web, status, message):
    web["http://public.test/a"] = FakeResponse(status)
    with pytest.raises(ScrapeError, match=message):
        scrape_job("http://public.test/a")


def test_scrape_tiny_page_suggests_manual_paste(web):
    web["http://public.test/a"] = FakeResponse(200, body=b"<p>hi</p>")
    with pytest.raises(ScrapeError, match="JavaScript"):
        scrape_job("http://public.test/a")
