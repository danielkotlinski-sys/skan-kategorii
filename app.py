"""
Sprint Brandos — Skan Kategorii
Interfejs webowy (Streamlit)

Uruchomienie:
    streamlit run app.py
"""

import os
import re
import anthropic
import streamlit as st

from scraper import _ensure_playwright_browser
from main import (
    analyze_main_competitor,
    analyze_small_competitor,
    synthesize,
    build_client_profile,
    render_report,
    normalize_url,
)

# ─── Konfiguracja strony ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Skan Kategorii — Sprint Brandos",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* Typografia */
h1 { font-size: 2rem !important; font-weight: 700 !important; }
h2 { font-size: 1.3rem !important; font-weight: 600 !important; margin-top: 1.5rem !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; }

/* Karty konwencji */
.convention-card {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
    background: #fafafa;
}
.convention-card h4 {
    margin: 0 0 0.6rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #1a1a2e;
}

/* Skrypt kategorii */
.category-script {
    border-left: 4px solid #4361ee;
    background: #f0f4ff;
    padding: 1rem 1.2rem;
    border-radius: 0 8px 8px 0;
    font-style: italic;
    color: #333;
    margin: 0.5rem 0 1.5rem 0;
}

/* Chip — tabu */
.tabu-chip {
    display: inline-block;
    background: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.85rem;
    margin: 3px 4px 3px 0;
    color: #5a4000;
}

/* Sekcja profilu */
.profile-block {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.profile-block .label {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    margin-bottom: 0.3rem;
}

/* Napięcie strategiczne — wyróżnione */
.tension-block {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-top: 0.5rem;
}
.tension-block .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #aab4d0;
    margin-bottom: 0.5rem;
}

/* Przycisk główny */
div[data-testid="stFormSubmitButton"] > button {
    background: #4361ee !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
}

/* Divider */
hr { margin: 2rem 0 !important; }
</style>
""", unsafe_allow_html=True)


# Instalacja Playwright na Streamlit Cloud (jednorazowo per deploy)
@st.cache_resource
def setup_playwright():
    _ensure_playwright_browser()

setup_playwright()

# ─── Nagłówek ───────────────────────────────────────────────────────────────

st.markdown("# Skan Kategorii")
st.caption("Sprint Brandos · Automatyczna analiza konwencji kategorii i profilu klienta")
st.divider()


# ─── Formularz wejściowy ─────────────────────────────────────────────────────

# Klucz ze Streamlit Secrets (cloud) → env var → pusty
try:
    env_key = st.secrets.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
except Exception:
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
env_key = env_key.strip()

with st.form("analysis_form"):
    col1, col2 = st.columns([3, 2])
    with col1:
        category = st.text_input(
            "Kategoria / branża",
            placeholder="np. agencje SEO, coaching kariery, kancelarie podatkowe",
        )
    with col2:
        market = st.text_input("Rynek", placeholder="np. Polska", value="Polska")

    main_urls_text = st.text_area(
        "Główni konkurenci — URL-e (3–5, jeden na linię)",
        height=120,
        placeholder="https://firma1.pl\nhttps://firma2.pl\nhttps://firma3.pl\nhttps://firma4.pl\nhttps://firma5.pl",
    )

    small_urls_text = st.text_area(
        "Mniejsze / niszowe firmy — opcjonalnie (do 10, jeden na linię)",
        height=90,
        placeholder="https://mala-firma.pl\nhttps://niszowa-firma.pl",
    )

    if not env_key:
        st.markdown(
            """
            <div style="background:#f0f4ff;border:1px solid #c7d2fe;border-radius:8px;
                        padding:0.8rem 1rem;margin-bottom:0.5rem;font-size:0.875rem;color:#374151;">
            <strong>Do działania aplikacji potrzebny jest klucz API Anthropic.</strong><br>
            Utwórz go bezpłatnie na
            <a href="https://console.anthropic.com" target="_blank" style="color:#4361ee;">
            console.anthropic.com</a> → zakładka <em>API Keys</em>.
            Koszt jednej analizy: ok. <strong>$0.50–1.50</strong>.
            Klucz jest używany wyłącznie lokalnie — nie jest nigdzie wysyłany ani zapisywany.
            </div>
            """,
            unsafe_allow_html=True,
        )
        api_key_input = st.text_input(
            "Klucz API Anthropic",
            type="password",
            placeholder="sk-ant-...",
        )
    else:
        api_key_input = env_key
        st.info("🔑 Klucz API wczytany ze zmiennej środowiskowej `ANTHROPIC_API_KEY`")

    submitted = st.form_submit_button(
        "Analizuj →", type="primary", use_container_width=True
    )


# ─── Logika analizy ──────────────────────────────────────────────────────────

if submitted:
    main_urls = [normalize_url(u) for u in main_urls_text.strip().splitlines() if u.strip()]
    small_urls = [normalize_url(u) for u in small_urls_text.strip().splitlines() if u.strip()]
    api_key = api_key_input.strip()

    # Walidacja
    errors = []
    if not category.strip():
        errors.append("Podaj kategorię / branżę.")
    if len(main_urls) < 3:
        errors.append("Podaj co najmniej 3 URL-e głównych konkurentów.")
    if not api_key:
        errors.append("Podaj klucz API Anthropic.")

    for e in errors:
        st.error(e)

    if not errors:
        client = anthropic.Anthropic(api_key=api_key)
        total = len(main_urls) + len(small_urls) + 2
        step = 0

        progress = st.progress(0, text="Startuję...")
        main_results = []
        small_results = []

        with st.status("Analizuję kategorię...", expanded=True) as status:

            # ── Krok 1 ──────────────────────────────────────────────────────
            st.write(f"**Krok 1** — analizuję {len(main_urls)} głównych konkurentów")
            for url in main_urls:
                st.write(f"&nbsp;&nbsp;↳ `{url}`")
                try:
                    analysis = analyze_main_competitor(url, category, client)
                except Exception as exc:
                    st.warning(f"Błąd przy `{url}`: {exc}")
                    analysis = {}
                main_results.append((url, analysis))
                step += 1
                progress.progress(step / total, text=f"Krok 1 · {step}/{len(main_urls)}")

            # ── Krok 2 ──────────────────────────────────────────────────────
            if small_urls:
                st.write(f"**Krok 2** — analizuję {len(small_urls)} mniejszych firm")
                for url in small_urls:
                    st.write(f"&nbsp;&nbsp;↳ `{url}`")
                    try:
                        analysis = analyze_small_competitor(url, category, client)
                    except Exception as exc:
                        st.warning(f"Błąd przy `{url}`: {exc}")
                        analysis = {}
                    small_results.append((url, analysis))
                    step += 1
                    progress.progress(step / total, text=f"Krok 2 · {step - len(main_urls)}/{len(small_urls)}")

            # ── Krok 3 ──────────────────────────────────────────────────────
            st.write("**Krok 3** — synteza konwencji kategorii...")
            try:
                synthesis = synthesize(category, market, main_results, small_results, client)
            except Exception as exc:
                st.error(f"Błąd syntezy: {exc}")
                synthesis = {}
            if "_raw" in synthesis:
                st.error(
                    "⚠ Synteza (Krok 3) zwróciła nieoczekiwany format — "
                    "Claude dodał tekst poza JSONem. Spróbuj ponownie."
                )
                st.code(synthesis["_raw"][:500], language=None)
                synthesis = {}
            step += 1
            progress.progress(step / total, text="Krok 3 · synteza")

            # ── Krok 4 ──────────────────────────────────────────────────────
            st.write("**Krok 4** — profil motywacyjno-behawioralny klienta...")
            try:
                profile = build_client_profile(category, synthesis, client)
            except Exception as exc:
                st.error(f"Błąd profilu: {exc}")
                profile = {}
            if "_raw" in profile:
                st.error("⚠ Profil klienta (Krok 4) zwrócił nieoczekiwany format. Spróbuj ponownie.")
                profile = {}
            progress.progress(1.0, text="Gotowe!")
            status.update(label="✓ Analiza zakończona", state="complete", expanded=False)

        # Zapisz do sesji
        st.session_state["results"] = {
            "category": category,
            "market": market,
            "main_results": main_results,
            "small_results": small_results,
            "synthesis": synthesis,
            "profile": profile,
            "report": render_report(
                category, market, main_results, small_results, synthesis, profile
            ),
        }
        st.rerun()


# ─── Wyświetlanie wyników ────────────────────────────────────────────────────

if "results" in st.session_state:
    r = st.session_state["results"]
    synthesis = r["synthesis"]
    profile = r["profile"]
    main_results = r["main_results"]
    small_results = r["small_results"]
    report_md = r["report"]
    category = r["category"]

    st.divider()
    st.markdown(f"## Wyniki · {category}")

    # ── 3.1 Dominująca definicja wartości + skrypt ───────────────────────────
    st.markdown("### Dominująca definicja wartości")
    st.markdown(
        f'<div class="profile-block">{synthesis.get("dominujaca_definicja_wartosci","")}</div>',
        unsafe_allow_html=True,
    )

    if synthesis.get("skrypt_kategorii"):
        st.markdown("**Skrypt kategorii** — zdania, które brzmią jak opis typowej firmy:")
        st.markdown(
            f'<div class="category-script">„{synthesis["skrypt_kategorii"]}"</div>',
            unsafe_allow_html=True,
        )

    # ── 3.2 Konwencje ────────────────────────────────────────────────────────
    st.markdown("### Konwencje kategorii")
    for i, k in enumerate(synthesis.get("konwencje", []), 1):
        with st.expander(f"Konwencja #{i}: **{k.get('nazwa','')}**", expanded=(i == 1)):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Co wszyscy robią**")
                st.write(k.get("co_wszyscy_robia", ""))
                st.markdown("**Skąd się to wzięło**")
                st.write(k.get("skad_sie_wzelo", ""))
            with col_b:
                st.markdown("**Co to kosztuje klienta**")
                st.write(k.get("co_kosztuje_klienta", ""))

    # ── 3.4 Tabu ─────────────────────────────────────────────────────────────
    tabu = synthesis.get("tabu_kategorii", [])
    if tabu:
        st.markdown("### Tabu kategorii")
        chips = " ".join(
            f'<span class="tabu-chip">⚠ {t}</span>' for t in tabu
        )
        st.markdown(chips, unsafe_allow_html=True)

    # ── 3.5 Klient wykluczony ────────────────────────────────────────────────
    if synthesis.get("klient_wykluczony"):
        st.markdown("### Klient wykluczony przez konwencję")
        st.markdown(
            f'<div class="profile-block">{synthesis["klient_wykluczony"]}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Krok 4 — Profil klienta ──────────────────────────────────────────────
    st.markdown("### Profil klienta konwencji")
    st.caption("Dla kogo ta konwencja jest atrakcyjna — i kogo strukturalnie wyklucza")

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        if profile.get("czego_naprawde_chce"):
            st.markdown(
                '<div class="profile-block">'
                '<div class="label">Czego naprawdę chce</div>'
                f'{profile["czego_naprawde_chce"]}</div>',
                unsafe_allow_html=True,
            )
        if profile.get("jak_decyduje"):
            st.markdown(
                '<div class="profile-block">'
                '<div class="label">Jak decyduje</div>'
                f'{profile["jak_decyduje"]}</div>',
                unsafe_allow_html=True,
            )
    with p_col2:
        if profile.get("czego_sie_boi"):
            st.markdown(
                '<div class="profile-block">'
                '<div class="label">Czego się boi</div>'
                f'{profile["czego_sie_boi"]}</div>',
                unsafe_allow_html=True,
            )
        if profile.get("historia_ktora_opowiada_sobie"):
            st.markdown(
                '<div class="profile-block">'
                '<div class="label">Historia, którą opowiada sobie</div>'
                f'<em>{profile["historia_ktora_opowiada_sobie"]}</em></div>',
                unsafe_allow_html=True,
            )

    if profile.get("kogo_strukturalnie_wyklucza"):
        st.markdown(
            '<div class="profile-block">'
            '<div class="label">Kogo konwencja strukturalnie wyklucza</div>'
            f'{profile["kogo_strukturalnie_wyklucza"]}</div>',
            unsafe_allow_html=True,
        )

    if profile.get("napiecie_strategiczne"):
        st.markdown(
            '<div class="tension-block">'
            '<div class="label">Napięcie strategiczne</div>'
            f'{profile["napiecie_strategiczne"]}</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Dane źródłowe ────────────────────────────────────────────────────────
    with st.expander(f"Dane źródłowe — {len(main_results)} głównych graczy"):
        for url, a in main_results:
            st.markdown(f"**`{url}`**")
            cols = st.columns([2, 2, 2])
            with cols[0]:
                st.markdown("*Obietnica:*")
                st.write(a.get("dominujaca_obietnica", "—"))
            with cols[1]:
                st.markdown("*Do kogo mówią:*")
                st.write(a.get("do_kogo_mowia", "—"))
            with cols[2]:
                st.markdown("*Co przemilczają:*")
                st.write(a.get("co_przemilczaja", "—"))
            st.markdown("---")

    if small_results:
        with st.expander(f"Dane źródłowe — {len(small_results)} mniejszych firm"):
            for url, a in small_results:
                st.markdown(f"**`{url}`** — {a.get('czy_lamie_konwencje','')}")
                st.write(a.get("co_robi_inaczej", "—"))
                if a.get("jak_lamie"):
                    st.caption(f"Jak łamie: {a['jak_lamie']}")
                st.markdown("---")

    # ── Pobieranie raportu ───────────────────────────────────────────────────
    safe_name = re.sub(r"[^\w\s-]", "", category).strip().replace(" ", "_")
    st.download_button(
        label="⬇ Pobierz raport (.md)",
        data=report_md,
        file_name=f"skan_{safe_name}.md",
        mime="text/markdown",
        use_container_width=True,
    )
