"""
Scraper — pobieranie treści stron konkurentów.
Podstawowe narzędzie: Playwright (obsługa JS).
Fallback: requests + BeautifulSoup.
"""

import re
import sys
import subprocess
from typing import Optional

# Instalacja przeglądarki Playwright przy pierwszym uruchomieniu na Streamlit Cloud
def _ensure_playwright_browser():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
            capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0
    except Exception:
        return False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Podstrony do sprawdzenia (w kolejności priorytetu)
SUBPAGES = [
    ("/o-nas", "about"),
    ("/about", "about"),
    ("/about-us", "about"),
    ("/oferta", "offer"),
    ("/uslugi", "offer"),
    ("/services", "offer"),
    ("/co-robimy", "offer"),
]

MAX_CHARS_PER_PAGE = 4000


def clean_text(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{3,}', ' ', text)
    text = re.sub(r'\s*\|\s*', ' | ', text)
    text = text.strip()
    if len(text) > MAX_CHARS_PER_PAGE:
        text = text[:MAX_CHARS_PER_PAGE] + "\n[...treść skrócona]"
    return text


COOKIE_ACCEPT_SELECTORS = [
    # Polskie banery
    "button:has-text('Akceptuję')", "button:has-text('Akceptuj')",
    "button:has-text('Akceptuj wszystkie')", "button:has-text('Zgadzam się')",
    "button:has-text('Zezwól na wszystkie')", "button:has-text('Zezwól')",
    # Angielskie
    "button:has-text('Accept all')", "button:has-text('Accept All')",
    "button:has-text('Accept')", "button:has-text('Agree')",
    "button:has-text('Allow all')", "button:has-text('I agree')",
    # Data atrybuty
    "[data-accept-all]", "[id*='accept']",
]

COOKIE_REMOVE_SELECTORS = [
    "[class*='cookie']", "[id*='cookie']", "[class*='consent']",
    "[id*='consent']", "[class*='gdpr']", "[id*='gdpr']",
    "[class*='popup']", "[class*='overlay']", "[class*='modal']",
]


def _scrape_playwright(url: str) -> Optional[str]:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = ctx.new_page()
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)

            # Próba kliknięcia przycisku akceptacji cookies
            for sel in COOKIE_ACCEPT_SELECTORS:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=400):
                        btn.click(timeout=500)
                        page.wait_for_timeout(600)
                        break
                except Exception:
                    continue

            text = page.evaluate("""(removeSelectors) => {
                // Usuń cookie banery i nakładki
                removeSelectors.forEach(sel => {
                    try {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    } catch(e) {}
                });
                // Usuń standardowe elementy szumu
                ['script','style','noscript','iframe'].forEach(tag => {
                    document.querySelectorAll(tag).forEach(el => el.remove());
                });
                return document.body ? document.body.innerText : '';
            }""", COOKIE_REMOVE_SELECTORS)

            browser.close()
            return clean_text(text) if text else None
    except Exception:
        return None


def _scrape_requests(url: str) -> Optional[str]:
    if not HAS_REQUESTS:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        return clean_text(soup.get_text(separator="\n"))
    except Exception:
        return None


def fetch_page(url: str) -> str:
    """Pobierz stronę. Playwright → requests → błąd."""
    result = None
    if HAS_PLAYWRIGHT:
        result = _scrape_playwright(url)
    if not result and HAS_REQUESTS:
        result = _scrape_requests(url)
    return result or "[Nie udało się pobrać treści strony]"


def scrape_competitor(url: str, verbose: bool = True) -> dict:
    """
    Zwraca słownik z treścią stron: home + opcjonalnie about/offer.
    """
    base = url.rstrip("/")
    pages = {}

    if verbose:
        print(f"    ↳ strona główna...", end=" ", flush=True)
    pages["home"] = fetch_page(url)
    if verbose:
        ok = "✓" if "[Nie udało" not in pages["home"] else "✗"
        print(ok)

    # Próba pobrania podstron
    found_about = False
    found_offer = False

    for path, kind in SUBPAGES:
        if kind == "about" and found_about:
            continue
        if kind == "offer" and found_offer:
            continue

        sub_url = base + path
        if verbose:
            print(f"    ↳ {path}...", end=" ", flush=True)

        content = fetch_page(sub_url)

        if "[Nie udało" not in content and len(content) > 200:
            pages[kind] = content
            if kind == "about":
                found_about = True
            elif kind == "offer":
                found_offer = True
            if verbose:
                print("✓")
        else:
            if verbose:
                print("–")

        # Dość jak mamy obie podstrony
        if found_about and found_offer:
            break

    return pages


def pages_to_text(url: str, pages: dict) -> str:
    """Scal zawartość wszystkich pobranych podstron w jeden blok tekstu."""
    parts = [f"URL: {url}"]
    labels = {"home": "STRONA GŁÓWNA", "about": "O NAS", "offer": "OFERTA/USŁUGI"}
    for key, label in labels.items():
        if key in pages:
            parts.append(f"\n--- {label} ---\n{pages[key]}")
    return "\n".join(parts)
