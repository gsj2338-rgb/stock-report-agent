import logging
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Sources: tried in order; returns from all that succeed
SOURCES = [
    {
        "name": "TrendForce",
        "type": "html",
        "url": "https://www.trendforce.com/news/",
        "article_sel": ".jeg_posts article, .post-item, article.jeg_post",
        "title_sel": ".jeg_post_title a, h2 a, h3 a, .entry-title a",
        "summary_sel": ".jeg_post_excerpt p, .entry-summary p, .post-excerpt p",
    },
    {
        "name": "EE Times Asia — Semiconductors",
        "type": "rss",
        "url": "https://www.eetasia.com/category/semiconductors/feed/",
    },
    {
        "name": "Semiconductor Engineering",
        "type": "rss",
        "url": "https://semiengineering.com/category/semiconductors/feed/",
    },
    {
        "name": "AnandTech",
        "type": "rss",
        "url": "https://www.anandtech.com/rss/news",
    },
]


def _fetch_rss(source: dict) -> list[dict]:
    resp = requests.get(source["url"], headers=HEADERS, timeout=15)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    # Standard RSS 2.0
    for item in root.findall(".//item")[:8]:
        title_el = item.find("title")
        desc_el  = item.find("description")
        link_el  = item.find("link")
        title   = title_el.text.strip() if title_el is not None and title_el.text else ""
        summary = BeautifulSoup(desc_el.text or "", "lxml").get_text()[:300].strip() if desc_el is not None else ""
        url     = link_el.text.strip() if link_el is not None and link_el.text else source["url"]
        if title:
            results.append({"title": title, "url": url, "source": source["name"], "summary": summary})
    return results


def _fetch_html(source: dict) -> list[dict]:
    resp = requests.get(source["url"], headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    results = []
    articles = soup.select(source["article_sel"])[:10]
    for article in articles:
        title_el = article.select_one(source["title_sel"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href  = title_el.get("href", source["url"])
        if href.startswith("/"):
            from urllib.parse import urlparse
            base = f"{urlparse(source['url']).scheme}://{urlparse(source['url']).netloc}"
            href = base + href
        summary_el = article.select_one(source["summary_sel"]) if source.get("summary_sel") else None
        summary = summary_el.get_text(strip=True)[:300] if summary_el else ""
        if title:
            results.append({"title": title, "url": href, "source": source["name"], "summary": summary})
    return results


class SemiCollector:
    def fetch(self, date: str) -> list[dict]:
        """
        Fetch recent semiconductor news from multiple sources.
        Tries TrendForce (HTML scrape) then RSS feeds as fallback.
        Returns list of dicts: title, url, source, summary.
        Returns [] only if every source fails.
        """
        results = []
        for source in SOURCES:
            if len(results) >= 8:
                break
            try:
                if source["type"] == "rss":
                    items = _fetch_rss(source)
                else:
                    items = _fetch_html(source)
                results.extend(items)
                logger.info(f"Semi collector: {len(items)} items from {source['name']}")
            except Exception as e:
                logger.warning(f"Semi collector failed for {source['name']}: {e}")
        return results[:10]
