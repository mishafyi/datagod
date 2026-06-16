"""Google Scholar — rank publications by citation count (vendored scraper).

Vendored and adapted from WittmannF/sort-google-scholar
(https://github.com/WittmannF/sort-google-scholar, MIT License) by Fernando
Marcos Wittmann. The upstream `sortgs` tool scrapes Google Scholar's HTML
search results with requests + BeautifulSoup, builds a pandas DataFrame of
papers (Author, Title, Citations, Year, Publisher, Venue, Content, Source,
PDF, cit/year, Rank), and sorts by a chosen column.

What we keep from upstream: the HTML scraping selectors, the citation/year/
author regex extractors, the DataFrame assembly, the `cit/year` derived metric,
and the sort-by-column logic. What we drop: the Selenium CAPTCHA fallback (it
blocks on an interactive `input()` prompt — unusable in a server), matplotlib
plotting, CSV export, and the argparse CLI.

Google Scholar has **no public API** and aggressively blocks automated access
(CAPTCHA / HTTP 429 / IP block). This source is therefore brittle: without a
clean/residential IP it will frequently return the error-dict or an empty
result set. The blocking scrape runs in a worker thread via asyncio.to_thread()
so the event loop stays free. See docs/SCHOLAR_API.md.
"""

import asyncio
import re
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

from . import UpstreamJSON

SOURCE = "scholar"

# Google Scholar search URL. {} placeholders are start-offset and url-encoded
# keyword; trailing params restrict to the main article index (as_sdt=0,5).
GSCHOLAR_URL = "https://scholar.google.com/scholar?start={}&q={}&hl=en&as_sdt=0,5"
STARTYEAR_URL = "&as_ylo={}"
ENDYEAR_URL = "&as_yhi={}"

# Phrases Google embeds in the page when it serves a robot / CAPTCHA wall.
ROBOT_KW = ("unusual traffic from your computer network", "not a robot",
            "/sorry/", "please show you're not a robot")

# Browser-like UA — bare requests with no UA is blocked faster.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

# Columns of the assembled DataFrame, in upstream order.
COLUMNS = ("Author", "Title", "Citations", "Year", "Publisher", "Venue",
           "Content", "Source", "PDF")


class BlockedError(RuntimeError):
    """Raised when Google Scholar serves a robot/CAPTCHA wall instead of results."""


def _error(exc: BaseException) -> dict:
    """Build the repo's standard error-dict from an exception."""
    upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
    return {"error": True, "source": SOURCE,
            "upstream_status": upstream_status, "message": str(exc)}


def _get_citations(content: str) -> int:
    """Extract the citation count from a result's HTML (`Cited by N`)."""
    match = re.search(r"Cited by (\d+)", content)
    return int(match.group(1)) if match else 0


def _get_year(content: str) -> int:
    """Extract a 4-digit publication year from the `gs_a` byline text."""
    match = re.search(r"\b(19|20)\d{2}\b", content)
    return int(match.group(0)) if match else 0


def _get_author(content: str) -> str:
    """Extract the author string (text before the first ' - ') from the byline."""
    clean = content.replace("\xa0", " ")
    return clean.split(" - ")[0] if clean else ""


def _get_pdf_link(div: Any) -> str:
    """Return the direct PDF link for a result if Google exposes one."""
    pdf_div = div.find("div", {"class": "gs_ggs gs_fl"})
    if pdf_div is not None:
        a_tag = pdf_div.find("a")
        if a_tag is not None and a_tag.get("href"):
            return a_tag.get("href")
    return "No PDF link"


def _build_url(keyword: str, start: int, start_year: int | None,
               end_year: int | None) -> str:
    """Compose the Scholar search URL for one page (offset `start`)."""
    url = GSCHOLAR_URL
    if start_year is not None:
        url = url + STARTYEAR_URL.format(start_year)
    if end_year is not None:
        url = url + ENDYEAR_URL.format(end_year)
    return url.format(str(start), keyword.replace(" ", "+"))


def _parse_div(div: Any, fallback_url: str) -> dict[str, Any]:
    """Parse one Google Scholar result `<div class="gs_or">` into a record dict.

    Mirrors the upstream field extraction. Each field is defensively extracted
    because Scholar's markup varies per result (missing bylines, no citations,
    etc.); a missing field gets the upstream's sentinel string rather than
    failing the whole page.
    """
    a = div.find("h3")
    a = a.find("a") if a is not None else None
    link = a.get("href") if a is not None and a.get("href") else "Look manually at: " + fallback_url
    title = a.text if a is not None else "Could not catch title"

    citations = _get_citations(str(div))

    gs_a = div.find("div", {"class": "gs_a"})
    byline = gs_a.text if gs_a is not None else ""
    year = _get_year(byline) if byline else 0
    author = _get_author(byline) if byline else "Author not found"
    publisher = byline.split("-")[-1] if byline else "Publisher not found"
    if byline and len(byline.split("-")) >= 2:
        venue = " ".join(byline.split("-")[-2].split(",")[:-1])
    else:
        venue = "Venue not found"

    content_div = div.find("div", {"class": "gs_rs"})
    content = content_div.text if content_div is not None else "Content not found"

    return {"Author": author, "Title": title, "Citations": citations,
            "Year": year, "Publisher": publisher, "Venue": venue,
            "Content": content, "Source": link, "PDF": _get_pdf_link(div)}


def _scrape(keyword: str, nresults: int, sort_by: str,
            start_year: int | None, end_year: int | None) -> pd.DataFrame:
    """Blocking scrape: fetch Scholar result pages, parse, rank. Runs off-loop.

    Raises BlockedError on a robot/CAPTCHA wall and requests exceptions on
    HTTP failures; `_run` converts both into the error-dict.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    records: list[dict[str, Any]] = []

    for start in range(0, nresults, 10):
        url = _build_url(keyword, start, start_year, end_year)
        page = session.get(url, timeout=30)
        page.raise_for_status()
        body = page.content.decode("ISO-8859-1", errors="ignore")
        if any(kw in body for kw in ROBOT_KW):
            raise BlockedError(
                "Google Scholar served a robot/CAPTCHA wall (no clean IP). "
                f"Fetched {len(records)} results before the block at offset {start}."
            )

        soup = BeautifulSoup(page.content, "html.parser", from_encoding="utf-8")
        divs = soup.findAll("div", {"class": "gs_or"})
        for div in divs:
            records.append(_parse_div(div, url))
            if len(records) >= nresults:
                break
        if len(records) >= nresults:
            break

    rank = list(range(1, len(records) + 1))
    data = pd.DataFrame(records, columns=list(COLUMNS), index=rank)
    data.index.name = "Rank"

    if not data.empty:
        # Citations per year, clipping Year to end_year to avoid future-dated divisors.
        upper = end_year if end_year is not None else pd.Timestamp.now().year
        denom = (upper + 1) - data["Year"].clip(upper=upper)
        data["cit/year"] = (data["Citations"] / denom).round(0).astype(int)
        try:
            data = data.sort_values(by=sort_by, ascending=False)
        except KeyError:
            data = data.sort_values(by="Citations", ascending=False)

    return data


def _df_to_records(data: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert the ranked DataFrame to records (Rank as a field, NaN -> None)."""
    if data.empty:
        return []
    data = data.reset_index()
    data.columns = [str(c) for c in data.columns]
    return data.astype(object).where(data.notna(), None).to_dict(orient="records")


async def search(keyword: str, nresults: int, sort_by: str,
                 start_year: int | None, end_year: int | None) -> UpstreamJSON:
    """Search Google Scholar and return papers ranked by `sort_by`.

    Args:
        keyword: search query (Scholar operators like OR / "exact phrase" work).
        nresults: number of papers to fetch (rounded up to multiples of 10 by
            Scholar's pagination; high values trigger blocking sooner).
        sort_by: DataFrame column to sort by, descending. "Citations" (default
            caller value) or "cit/year"; unknown columns fall back to Citations.
        start_year: lower publication-year bound, or None for no lower bound.
        end_year: upper publication-year bound, or None for the current year.

    Returns:
        {"results": [...records...], "count": N, "keyword": <keyword>} on success,
        or the standard error-dict if Google blocks the scrape (CAPTCHA/429/IP
        block) or any request fails. Never raises.
    """
    def _do() -> dict[str, Any]:
        data = _scrape(keyword, nresults, sort_by, start_year, end_year)
        records = _df_to_records(data)
        return {"results": records, "count": len(records), "keyword": keyword}

    try:
        return await asyncio.to_thread(_do)
    except Exception as exc:
        return _error(exc)
