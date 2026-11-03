
import requests
import csv
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import (
    urlparse, urlunparse, parse_qs, unquote
)

GOOGLE_URL = "https://www.google.com/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}

OUTPUT_DIR = Path("results")
OUTPUT_DIR.mkdir(exist_ok=True)


def clean_url(url):
    if not url:
        return None

    url = unquote(url.strip())

    if url.startswith("//"):
        url = "https:" + url

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    host = (parsed.hostname or "").lower()

    blocked_domains = (
        "google.com",
        "googleusercontent.com",
        "gstatic.com",
        "googleapis.com"
    )

    if any(
        host == domain or host.endswith("." + domain)
        for domain in blocked_domains
    ):
        return None

    if not host or "." not in host:
        return None

    return urlunparse(parsed._replace(fragment=""))


def unwrap_google_url(url):
    if not url.startswith("/url?"):
        return url

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    for key in ("q", "url"):
        value = params.get(key, [None])[0]
        if value:
            return value

    return None


def detect_block(page, response):
    final_url = response.url.lower()
    text = page.get_text(" ", strip=True).lower()

    if "consent.google.com" in final_url:
        return "Google consent page detected"

    if (
        "sorry/index" in final_url
        or "unusual traffic" in text
        or page.select_one("form#captcha-form")
        or "recaptcha" in final_url
    ):
        return "Google CAPTCHA / automated traffic block"

    if response.status_code in (403, 429):
        return f"HTTP {response.status_code}: request blocked"

    return None


def extract_page_urls(page):
    urls = []

    # Google organic results commonly contain an H3
    # inside the result link.
    anchors = page.select("a:has(h3)")

    # Fallback for alternative Google HTML layouts.
    if not anchors:
        anchors = page.select("div.MjjYud a[href]")

    for anchor in anchors:
        raw_url = anchor.get("href", "")

        raw_url = unwrap_google_url(raw_url)

        url = clean_url(raw_url)

        if url:
            urls.append(url)

    return urls


def save_results(urls):
    txt_file = OUTPUT_DIR / "urls.txt"
    csv_file = OUTPUT_DIR / "urls.csv"

    with open(txt_file, "w", encoding="utf-8") as file:
        for url in urls:
            file.write(url + "\n")

    with open(
        csv_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["URL"])

        for url in urls:
            writer.writerow([url])

    print("\n[+] TXT saved:", txt_file)
    print("[+] CSV saved:", csv_file)


def google_search(query, maximum):

    session = requests.Session()
    session.headers.update(HEADERS)

    collected = []
    seen = set()

    start = 0
    page_number = 1

    print("\n[+] Connecting to Google...")
    print("[+] Query:", query)
    print("[+] Target:", maximum)

    while len(collected) < maximum:

        print("\n" + "-" * 45)
        print(f"[*] Page {page_number}")
        print("-" * 45)

        params = {
            "q": query,
            "num": 10,
            "start": start,
            "hl": "en"
        }

        try:
            response = session.get(
                GOOGLE_URL,
                params=params,
                timeout=25
            )

        except requests.RequestException as error:
            print("[!] Connection error:", error)
            break

        print("[DEBUG] HTTP:", response.status_code)
        print("[DEBUG] URL:", response.url)

        if response.status_code != 200:
            print("[!] Google did not return HTTP 200.")
            break

        page = BeautifulSoup(
            response.text,
            "html.parser"
        )

        title = (
            page.title.get_text(strip=True)
            if page.title else "No title"
        )

        print("[DEBUG] TITLE:", title)

        block_reason = detect_block(page, response)

        if block_reason:
            print("[!] " + block_reason)
            break

        page_urls = extract_page_urls(page)

        print("[DEBUG] Extracted:", len(page_urls))

        new_count = 0

        for url in page_urls:

            if url not in seen:
                seen.add(url)
                collected.append(url)
                new_count += 1

                print(
                    f"[+] {len(collected)}. {url}"
                )

                if len(collected) >= maximum:
                    break

        if new_count == 0:
            print("[!] No new extractable results.")
            break

        start += 10
        page_number += 1

        # Respect Google's request limits.
        if len(collected) < maximum:
            time.sleep(5)

    session.close()

    return collected


def main():

    print("=" * 55)
    print("           GOOGLE URL EXTRACTOR")
    print("                  V2.1")
    print("=" * 55)

    query = input(
        "\n[?] Enter Google Dork / Search: "
    ).strip()

    if not query:
        print("[!] Empty search query.")
        return

    try:
        maximum = int(
            input("[?] Maximum URLs: ")
        )

        if maximum <= 0:
            raise ValueError

    except ValueError:
        print("[!] Enter a positive number.")
        return

    urls = google_search(query, maximum)

    save_results(urls)

    print("\n" + "=" * 55)
    print("[✓] EXTRACTION FINISHED")
    print("[✓] Total URLs:", len(urls))
    print("[✓] Results folder:", OUTPUT_DIR.resolve())
    print("=" * 55)


if __name__ == "__main__":
    main()
