import requests
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

SOURCES = [
    {
        "name": "TrendForce",
        "url": "https://www.trendforce.com/news/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a, h3.entry-title a",
        "summary_selector": ".entry-summary p, .entry-content p",
    },
    {
        "name": "SEMI.org",
        "url": "https://www.semi.org/en/blogs-and-news/industry-news",
        "article_selector": ".views-row, .news-item",
        "title_selector": "h3 a, h2 a, .field--name-title a",
        "summary_selector": ".field--name-body p, .summary",
    },
]


class SemiCollector:
    def fetch(self, date: str) -> list[dict]:
        """
        Fetch recent semiconductor news from TrendForce and SEMI.org.
        Returns list of dicts: title, url, source, summary.
        Returns [] on all sources failing.
        """
        results = []
        for source in SOURCES:
            try:
                resp = requests.get(source["url"], headers=HEADERS, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                articles = soup.select(source["article_selector"])[:10]
                for article in articles:
                    title_el = article.select_one(source["title_selector"])
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    url = title_el.get("href", source["url"])
                    if url.startswith("/"):
                        base = source["url"].split("/en/")[0] if "/en/" in source["url"] else source["url"].rstrip("/")
                        url = base + url
                    summary_el = article.select_one(source["summary_selector"])
                    summary = summary_el.get_text(strip=True)[:300] if summary_el else ""
                    results.append({
                        "title": title,
                        "url": url,
                        "source": source["name"],
                        "summary": summary,
                    })
            except Exception as e:
                logger.error(f"Semi collector error for {source['name']}: {e}")
        return results
