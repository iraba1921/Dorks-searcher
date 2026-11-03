
import requests
import csv
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse

GOOGLE = "https://www.google.com/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}


def clean_url(url):
    if not url:
        return None

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    host = (parsed.hostname or "").lower()

    if host in ("google.com", "www.google.com"):
        return None

    if host.endswith(".google.com"):
        return None

    return urlunparse(parsed._replace(fragment=""))


def extract_google_urls(query, maximum):
    session = requests.Session()
    session.headers.update(HEADERS)

    collected = []
    seen = set()
    start = 0

    print("\n[+] Searching Google...\n")

    while len(collected) < maximum:

        params = {
            "q": query,
            "num": 10,
            "start": start,
            "hl": "en"
        }

        try:
            response = session.get(
                GOOGLE,
                params=params,
                timeout=20
            )

            if response.status_code in (403, 429):
                print("[!] Google blocked the request.")
                break

            response.raise_for_status()

        except requests.RequestException as error:
            print(f"[!] Request error: {error}")
            break

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        soup = BeautifulSoup(response.text, "html.parser")

print("\n[DEBUG] HTTP:", response.status_code)
print("[DEBUG] URL:", response.url)
print("[DEBUG] TITLE:",
      soup.title.get_text(strip=True) if soup.title else "No title")

with open("debug.html", "w", encoding="utf-8") as f:
    f.write(response.text)

if "consent.google.com" in response.url:
    print("[!] Google consent page detected.")
    break

if soup.select_one("form#captcha-form"):
    print("[!] CAPTCHA detected.")
    break

page_urls = []

for anchor in soup.select("a:has(h3)"):
    url = anchor.get("href", "")

    if url.startswith("/url?"):
        from urllib.parse import parse_qs, urlparse
        url = parse_qs(urlparse(url).query).get("q", [None])[0]

    url = clean_url(url)

    if url and url not in seen:
        seen.add(url)
        page_urls.append(url)

print("[DEBUG] Extracted:", len(page_urls))

        if not page_urls:
            print("[!] No extractable results.")
            break

        for url in page_urls:
            collected.append(url)
            print(f"[{len(collected)}] {url}")

            if len(collected) >= maximum:
                break

        start += 10

        # Avoid rapid repeated requests.
        time.sleep(5)

    session.close()
    return collected


def save_results(urls):
    with open(
        "results.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write("\n".join(urls))

    with open(
        "results.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["URL"])

        for url in urls:
            writer.writerow([url])

    print("\n[+] Saved results.txt")
    print("[+] Saved results.csv")


def main():
    print("=" * 50)
    print("          GOOGLE URL EXTRACTOR")
    print("                 V2.0")
    print("=" * 50)

    query = input("\n[?] Enter Google Dork / Query: ").strip()

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

    urls = extract_google_urls(
        query,
        maximum
    )

    save_results(urls)

    print("\n" + "=" * 50)
    print(f"[✓] Total URLs: {len(urls)}")
    print("[✓] Extraction finished.")
    print("=" * 50)


if __name__ == "__main__":
    main()
