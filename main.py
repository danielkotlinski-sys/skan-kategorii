#!/usr/bin/env python3
"""
Sprint Brandos — Skan Kategorii
Automatyczna analiza konwencji kategorii (kroki 1–4 karty pracy prework).

Użycie:
    python main.py

Wymagane:
    pip install -r requirements.txt
    playwright install chromium   # jednorazowo

Klucz API:
    Ustaw zmienną środowiskową: export ANTHROPIC_API_KEY="sk-ant-..."
    lub podaj przy starcie.
"""

import os
import re
import json
import sys
from datetime import date
from pathlib import Path

import anthropic

from scraper import scrape_competitor, pages_to_text
from prompts import (
    PROMPT_ANALYZE_MAIN_COMPETITOR,
    PROMPT_ANALYZE_SMALL_COMPETITOR,
    PROMPT_SYNTHESIZE_CATEGORY,
    PROMPT_CLIENT_PROFILE,
)

MODEL = "claude-sonnet-4-6"


# ─── Helpers ────────────────────────────────────────────────────────────────

def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        api_key = input("\nKlucz API Anthropic (lub ustaw ANTHROPIC_API_KEY): ").strip()
    return anthropic.Anthropic(api_key=api_key)


def ask_claude(client: anthropic.Anthropic, prompt: str, max_tokens: int = 1500) -> dict:
    """Wyślij prompt, odbierz JSON."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    # 1. Spróbuj wyciągnąć z bloku ```json ... ```
    match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    candidate = match.group(1).strip() if match else raw

    # 2. Jeśli parsowanie się nie uda, szukaj pierwszego { ... } w całym tekście
    for text in [candidate, raw]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # 3. Ostatnia szansa: wyciągnij JSON-obiekt regex-em (pomija tekst przed/po)
    obj_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # 4. Zwróć surowy tekst — caller może to wykryć i pokazać błąd
    return {"_raw": raw}


def normalize_url(url: str) -> str:
    url = url.strip()
    if url and not url.startswith("http"):
        url = "https://" + url
    return url


def collect_urls(prompt_label: str, min_count: int, max_count: int) -> list[str]:
    urls = []
    print(f"\n{prompt_label}")
    while len(urls) < max_count:
        idx = len(urls) + 1
        suffix = " (Enter = koniec)" if len(urls) >= min_count else ""
        raw = input(f"  URL {idx}{suffix}: ").strip()
        if not raw:
            if len(urls) >= min_count:
                break
            print(f"  ⚠ Podaj przynajmniej {min_count} adresów.")
            continue
        urls.append(normalize_url(raw))
    return urls


# ─── Analiza ────────────────────────────────────────────────────────────────

def analyze_main_competitor(url: str, category: str, client: anthropic.Anthropic) -> dict:
    pages = scrape_competitor(url, verbose=True)
    content = pages_to_text(url, pages)
    prompt = PROMPT_ANALYZE_MAIN_COMPETITOR.format(category=category, content=content)
    return ask_claude(client, prompt, max_tokens=1200)


def analyze_small_competitor(url: str, category: str, client: anthropic.Anthropic) -> dict:
    pages = scrape_competitor(url, verbose=True)
    content = pages_to_text(url, pages)
    prompt = PROMPT_ANALYZE_SMALL_COMPETITOR.format(category=category, content=content)
    return ask_claude(client, prompt, max_tokens=500)


def synthesize(
    category: str,
    market: str,
    main_results: list[tuple[str, dict]],
    small_results: list[tuple[str, dict]],
    client: anthropic.Anthropic,
) -> dict:
    # Zbuduj blok tekstowy z analizami
    lines = []
    for i, (url, a) in enumerate(main_results, 1):
        lines.append(f"\n=== GRACZ GŁÓWNY {i}: {url} ===")
        lines.append(f"Dominująca obietnica: {a.get('dominujaca_obietnica', '')}")
        lines.append(f"Słowa klucze: {', '.join(a.get('slowa_klucze', []))}")
        lines.append(f"Do kogo mówią: {a.get('do_kogo_mowia', '')}")
        lines.append(f"Uzasadnienie wartości: {a.get('jak_uzasadniaja_wartosc', '')}")
        lines.append(f"Co przemilczają: {a.get('co_przemilczaja', '')}")
        lines.append(f"Co by frustrowało klienta: {a.get('co_frustrujacego', '')}")

    for i, (url, a) in enumerate(small_results, 1):
        lines.append(f"\n=== MNIEJSZA FIRMA {i}: {url} ===")
        lines.append(f"Co robi inaczej: {a.get('co_robi_inaczej', '')}")
        lines.append(f"Stosunek do konwencji: {a.get('czy_lamie_konwencje', '')}")
        if a.get("jak_lamie"):
            lines.append(f"Jak łamie: {a.get('jak_lamie')}")

    analyses_text = "\n".join(lines)
    prompt = PROMPT_SYNTHESIZE_CATEGORY.format(
        category=category,
        market=market,
        n_main=len(main_results),
        n_small=len(small_results),
        analyses_text=analyses_text,
    )
    return ask_claude(client, prompt, max_tokens=2500)


def build_client_profile(
    category: str,
    synthesis: dict,
    client: anthropic.Anthropic,
) -> dict:
    konwencje_lines = []
    for k in synthesis.get("konwencje", []):
        konwencje_lines.append(
            f"• {k.get('nazwa','')}: {k.get('co_wszyscy_robia','')} "
            f"[kosztuje klienta: {k.get('co_kosztuje_klienta','')}]"
        )

    prompt = PROMPT_CLIENT_PROFILE.format(
        category=category,
        dominujaca_def=synthesis.get("dominujaca_definicja_wartosci", ""),
        konwencje_text="\n".join(konwencje_lines),
        tabu_text="\n".join(f"• {t}" for t in synthesis.get("tabu_kategorii", [])),
        klient_wykluczony=synthesis.get("klient_wykluczony", ""),
    )
    return ask_claude(client, prompt, max_tokens=1800)


# ─── Raport ─────────────────────────────────────────────────────────────────

def render_report(
    category: str,
    market: str,
    main_results: list[tuple[str, dict]],
    small_results: list[tuple[str, dict]],
    synthesis: dict,
    profile: dict,
) -> str:
    today = date.today().strftime("%d.%m.%Y")
    sep = "\n---\n"

    lines = [
        "# SPRINT BRANDOS — Skan Kategorii",
        f"\n**Kategoria:** {category}  \n**Rynek:** {market}  \n**Data:** {today}",
        sep,
        "## KROK 1 — Analiza głównych graczy\n",
        "| # | Firma | Dominująca obietnica | Słowa klucze | Co przemilczają |",
        "|---|-------|---------------------|--------------|----------------|",
    ]

    for i, (url, a) in enumerate(main_results, 1):
        promise = (a.get("dominujaca_obietnica") or "").replace("\n", " ")[:80]
        keys = ", ".join((a.get("slowa_klucze") or [])[:5])
        silent = (a.get("co_przemilczaja") or "").replace("\n", " ")[:80]
        lines.append(f"| {i} | `{url}` | {promise} | {keys} | {silent} |")

    lines.append("\n### Pogłębiona analiza — główni gracze\n")
    for i, (url, a) in enumerate(main_results, 1):
        lines.append(f"**Firma {i} — `{url}`**\n")
        lines.append(f"*Do kogo mówią:* {a.get('do_kogo_mowia','')}\n")
        lines.append(f"*Jak uzasadniają wartość:* {a.get('jak_uzasadniaja_wartosc','')}\n")
        lines.append(f"*Co przemilczają:* {a.get('co_przemilczaja','')}\n")
        lines.append(f"*Co byłoby frustrujące dla klienta:* {a.get('co_frustrujacego','')}\n")

    if small_results:
        lines.append(sep)
        lines.append("## KROK 2 — Mniejsze firmy\n")
        lines.append("| # | Firma | Co robi inaczej | Konwencja |")
        lines.append("|---|-------|----------------|-----------|")
        letters = "abcdefghij"
        for i, (url, a) in enumerate(small_results):
            ltr = letters[i] if i < len(letters) else str(i + 1)
            diff = (a.get("co_robi_inaczej") or "").replace("\n", " ")[:90]
            conv = a.get("czy_lamie_konwencje", "")
            lines.append(f"| {ltr} | `{url}` | {diff} | {conv} |")
        lines.append("")

    lines.append(sep)
    lines.append("## KROK 3 — Synteza: konwencja kategorii\n")

    lines.append("### 3.1 Dominująca definicja wartości\n")
    lines.append(synthesis.get("dominujaca_definicja_wartosci", "") + "\n")

    lines.append("### 3.2 Trzy główne konwencje\n")
    for i, k in enumerate(synthesis.get("konwencje", []), 1):
        lines.append(f"**Konwencja #{i}: {k.get('nazwa','')}**\n")
        lines.append(f"*Co wszyscy robią:* {k.get('co_wszyscy_robia','')}\n")
        lines.append(f"*Skąd się to wzięło:* {k.get('skad_sie_wzelo','')}\n")
        lines.append(f"*Co to kosztuje klienta:* {k.get('co_kosztuje_klienta','')}\n")

    lines.append("### 3.3 Skrypt kategorii\n")
    lines.append(f"> {synthesis.get('skrypt_kategorii','')}\n")

    lines.append("### 3.4 Tabu kategorii\n")
    for t in synthesis.get("tabu_kategorii", []):
        lines.append(f"- {t}")
    lines.append("")

    lines.append("### 3.5 Klient wykluczony\n")
    lines.append(synthesis.get("klient_wykluczony", "") + "\n")

    lines.append(sep)
    lines.append("## KROK 4 — Profil klienta konwencji\n")
    lines.append(
        "*Dla jakiego klienta konwencja kategorii jest atrakcyjna "
        "— i kogo strukturalnie wyklucza?*\n"
    )

    fields = [
        ("czego_naprawde_chce",        "4.1 Czego ten klient naprawdę chce"),
        ("czego_sie_boi",              "4.2 Czego się boi"),
        ("jak_decyduje",               "4.3 Jak decyduje"),
        ("historia_ktora_opowiada_sobie", "4.4 Historia, którą opowiada sobie"),
        ("kogo_strukturalnie_wyklucza", "4.5 Kogo konwencja strukturalnie wyklucza"),
        ("napiecie_strategiczne",       "4.6 Napięcie strategiczne"),
    ]
    for key, label in fields:
        lines.append(f"### {label}\n")
        lines.append((profile.get(key) or "") + "\n")

    return "\n".join(lines)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════════╗")
    print("║   SPRINT BRANDOS — Skan Kategorii           ║")
    print("║   Automatyczna analiza konwencji kategorii  ║")
    print("╚══════════════════════════════════════════════╝\n")

    # 1. Dane wejściowe
    category = input("Kategoria / branża (np. 'agencje SEO', 'coaching kariery'): ").strip()
    market = input("Rynek (np. 'Polska', 'Europa'): ").strip()

    main_urls = collect_urls(
        "Podaj URL-e 5 głównych konkurentów (min. 3, maks. 5):",
        min_count=3,
        max_count=5,
    )

    small_urls = collect_urls(
        "Podaj URL-e mniejszych firm (opcjonalnie, maks. 10, Enter = pomiń):",
        min_count=0,
        max_count=10,
    )

    # 2. Klient API
    client = get_client()

    # 3. KROK 1 — Analiza głównych graczy
    print(f"\n{'='*50}")
    print(f"KROK 1 — Analizuję {len(main_urls)} głównych konkurentów")
    print('='*50)

    main_results: list[tuple[str, dict]] = []
    for i, url in enumerate(main_urls, 1):
        print(f"\n[{i}/{len(main_urls)}] {url}")
        try:
            analysis = analyze_main_competitor(url, category, client)
            main_results.append((url, analysis))
            preview = (analysis.get("dominujaca_obietnica") or "")[:70]
            print(f"  ✓ Obietnica: {preview}...")
        except Exception as e:
            print(f"  ✗ Błąd: {e}")
            main_results.append((url, {}))

    # 4. KROK 2 — Mniejsze firmy
    small_results: list[tuple[str, dict]] = []
    if small_urls:
        print(f"\n{'='*50}")
        print(f"KROK 2 — Analizuję {len(small_urls)} mniejszych firm")
        print('='*50)
        for i, url in enumerate(small_urls, 1):
            print(f"\n[{i}/{len(small_urls)}] {url}")
            try:
                analysis = analyze_small_competitor(url, category, client)
                small_results.append((url, analysis))
                print(f"  ✓ Konwencja: {analysis.get('czy_lamie_konwencje','')}")
            except Exception as e:
                print(f"  ✗ Błąd: {e}")
                small_results.append((url, {}))

    # 5. KROK 3 — Synteza
    print(f"\n{'='*50}")
    print("KROK 3 — Synteza konwencji kategorii")
    print('='*50)
    synthesis = synthesize(category, market, main_results, small_results, client)
    n_conv = len(synthesis.get("konwencje", []))
    n_tabu = len(synthesis.get("tabu_kategorii", []))
    print(f"  ✓ {n_conv} konwencje, {n_tabu} tabu")

    # 6. KROK 4 — Profil klienta
    print(f"\n{'='*50}")
    print("KROK 4 — Profil motywacyjno-behawioralny klienta")
    print('='*50)
    profile = build_client_profile(category, synthesis, client)
    print("  ✓ Gotowe")

    # 7. Raport
    report = render_report(category, market, main_results, small_results, synthesis, profile)

    safe_name = re.sub(r"[^\w\s-]", "", category).strip().replace(" ", "_")
    output_path = Path(__file__).parent / f"raport_{safe_name}.md"
    output_path.write_text(report, encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"✓ Raport zapisany: {output_path.name}")
    print('='*50)

    # Podgląd
    print(f"\n── Dominująca definicja wartości ──")
    print((synthesis.get("dominujaca_definicja_wartosci") or "")[:300])
    print(f"\n── Napięcie strategiczne ──")
    print((profile.get("napiecie_strategiczne") or "")[:300])
    print()


if __name__ == "__main__":
    main()
