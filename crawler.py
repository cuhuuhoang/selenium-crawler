import argparse
import json
import os
import time
from pathlib import Path
from typing import List, Tuple

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_URL = "https://vnexpress.net/tuoi-35-lam-sep-nhung-so-khong-xin-duoc-viec-neu-that-nghiep-dot-xuat-4866122.html"
SELENIUM_ENDPOINT = os.getenv("SELENIUM_ENDPOINT", "http://localhost:4444/wd/hub")


def build_driver() -> webdriver.Remote:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    return webdriver.Remote(command_executor=SELENIUM_ENDPOINT, options=options)


def load_article_html(driver: webdriver.Remote, url: str, wait_seconds: int = 15) -> str:
    driver.get(url)
    wait = WebDriverWait(driver, wait_seconds)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article.fck_detail")))

    # Scroll to bottom a few times to trigger lazy/comment loading.
    for _ in range(4):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

    load_more_comments(driver, wait)

    return driver.page_source


def load_more_comments(driver: webdriver.Remote, wait: WebDriverWait, max_clicks: int = 10) -> None:
    """Attempt to expand all comments by clicking 'Xem thêm' or similar buttons."""

    def try_click(e):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", e)
            driver.execute_script("arguments[0].click();", e)
            return True
        except Exception:
            return False

    selectors = [
        "a.view_more_comment",
        "a.view_more",
        ".view_more_cmt a",
        ".comment_more a",
        "a.view-all-comment",
        "a.view_all_comment",
        "a.show_more_comment",
        "a.view_all_reply",
    ]

    for _ in range(max_clicks):
        clicked = False

        # CSS selectors
        for sel in selectors:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed() and el.is_enabled():
                    if try_click(el):
                        clicked = True
                        time.sleep(1.5)
                        break
            if clicked:
                break

        # Text-based fallback (Vietnamese "Xem thêm")
        if not clicked:
            xpath = "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'xem thêm')]"
            for el in driver.find_elements(By.XPATH, xpath):
                if el.is_displayed() and el.is_enabled():
                    if try_click(el):
                        clicked = True
                        time.sleep(1.5)
                        break

        if not clicked:
            break

    # Ensure at least first batch is present
    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#list_comment .comment_item, .comment_item")
            )
        )
    except Exception:
        pass


def extract_article_from_soup(soup: BeautifulSoup, url: str) -> Tuple[dict, List[str]]:
    def text_sel(selector: str) -> str:
        node = soup.select_one(selector)
        return node.get_text(strip=True) if node else ""

    body_paragraphs = [
        p.get_text(strip=True) for p in soup.select("article.fck_detail p") if p.get_text(strip=True)
    ]
    tags = [a.get_text(strip=True) for a in soup.select("footer .tag_item a, div.list-tag a")]

    article = {
        "url": url,
        "title": text_sel("h1.title-detail"),
        "description": text_sel("p.description"),
        "published_at": text_sel("span.date"),
        "author": text_sel("p.Normal strong, p.author_mail strong"),
        "body": body_paragraphs,
        "tags": tags,
    }
    return article


def extract_comments_from_soup(soup: BeautifulSoup) -> List[dict]:
    comments = []
    for item in soup.select("#list_comment .comment_item, .comment_item"):
        name_node = item.select_one(".nickname, .txt-name")
        content_node = item.select_one("p.full_content, p.content_more, p.content_less")
        time_node = item.select_one(".time-com")

        author = name_node.get_text(strip=True) if name_node else ""
        content = content_node.get_text(" ", strip=True) if content_node else ""
        timestamp = time_node.get_text(strip=True) if time_node else ""

        if not (author or content):
            continue

        comments.append(
            {
                "author": author,
                "content": content,
                "time": timestamp,
            }
        )
    return comments


def download_html(html_path: Path, url: str) -> None:
    driver = build_driver()
    try:
        html = load_article_html(driver, url)
        html_path.write_text(html, encoding="utf-8")
    finally:
        driver.quit()


def extract_from_file(html_path: Path, url: str) -> dict:
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    article = extract_article_from_soup(soup, url)
    comments = extract_comments_from_soup(soup)
    article["comments"] = comments
    return article


def main():
    parser = argparse.ArgumentParser(description="Download and extract VnExpress article + comments.")
    parser.add_argument("--html-file", default="page.html", help="Path to save/read the raw HTML.")
    parser.add_argument("--download", action="store_true", help="Download the article HTML to --html-file.")
    parser.add_argument("--extract", action="store_true", help="Extract data from --html-file.")
    parser.add_argument("--output", help="Path to save extracted JSON. Defaults to stdout.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Article URL to fetch.")
    args = parser.parse_args()

    html_path = Path(args.html_file)
    article_url = args.url

    # If neither flag is provided, do both.
    if not args.download and not args.extract:
        args.download = True
        args.extract = True

    if args.download:
        download_html(html_path, article_url)

    if args.extract:
        data = extract_from_file(html_path, article_url)
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(json_data, encoding="utf-8")
        else:
            print(json_data)


if __name__ == "__main__":
    main()
