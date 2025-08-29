# app.py
import re
import time
import pandas as pd
import streamlit as st
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Comparador de Odds — Escanteios", layout="wide")

st.title("📊 Comparador de Odds — Escanteios (raspagem direta)")
st.caption(
    "Cole as URLs do MESMO jogo nas 3 casas e clique em Atualizar. "
    "Prototipo educacional — alguns sites podem bloquear (403)."
)

# ============ utilidades ============

@st.cache_data(ttl=15)
def fetch_text(url: str, timeout_ms=20000) -> str:
    """Abre a página com Playwright (Chromium), espera conteúdo e devolve o texto visível."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(url, wait_until="domcontentloaded")
        # Pequena espera extra para odds renderizarem
        time.sleep(2.5)
        text = page.inner_text("body")
        context.close()
        browser.close()
        return text

def _find_first_odd(text_after: str) -> float | None:
    """
    Acha a primeira odd (formato 1.23 ou 2,75) no trecho de texto.
    Retorna float com ponto.
    """
    m = re.search(r"\b\d{1,2}[.,]\d{1,2}\b", text_after)
    if not m:
        return None
    val = m.group(0).replace(",", ".")
    try:
        return float(val)
    except:
        return None

def extract_markets(text: str, label_over: str, label_under: str, keys: list[str]) -> dict:
    """
    Procura odds de 'Mais de X.X' e 'Menos de X.X' varrendo o texto renderizado.
    keys = ["8.5", "9.5", "10.5", ...]
    Retorna dict: {"Mais de 9.5": 1.90, "Menos de 9.5": 1.95, ...}
    """
    out = {}
    t = " ".join(text.split())  # compacta espaços
    for k in keys:
        # Over
        over_phrase = f"{label_over} {k}"
        i = t.lower().find(over_phrase.lower())
        if i >= 0:
            snippet = t[i:i+120]
            odd = _find_first_odd(snippet)
            if odd:
                out[f"{label_over} {k}"] = odd
        # Under
        under_phrase = f"{label_under} {k}"
        j = t.lower().find(under_phrase.lower())
        if j >= 0:
            snippet = t[j:j+120]
            odd = _find_first_odd(snippet)
            if odd:
                out[f"{label_under} {k}"] = odd
    return out

def extract_for_house(text: str, house: str) -> dict:
    """
    Ajusta labels por casa.
    - Betano/KTO costumam usar 'Mais de' / 'Menos de'
    - Bet365 às vezes usa 'Mais de' / 'Menos de' (pt) ou 'Over'/'Under' (se mudar idioma)
    """
    keys = ["8.5", "9.5", "10.5", "11.5"]
    house = house.lower()
    if "bet365" in house:
        # tenta português primeiro, senão inglês
        d = extract_markets(text, "Mais de", "Menos de", keys)
        if not d:
            d = extract_markets(text, "Over", "Under", keys)
        return d
    else:
        # Betano / KTO (pt)
        return extract_markets(text, "Mais de", "Menos de", keys)

def compare(links: dict) -> pd.DataFrame:
    """
    Para cada link, baixa o texto e extrai odds.
    Monta um DataFrame por mercado (linha) e casa (colunas).
    """
    casas = []
    mercados = set()
    data_por_casa = {}

    for casa, url in links.items():
        if not url.strip():
            continue
        casas.append(casa)
        txt = fetch_text(url)
        d = extract_for_house(txt, casa)
        data_por_casa[casa] = d
        mercados.update(d.keys())

    mercados = sorted(list(mercados), key=lambda x: (float(re.findall(r"\d+\.\d", x)[0]), x) if re.findall(r"\d+\.\d", x) else (999, x))
    rows = []
    for m in mercados:
        row = {"mercado": m}
        for casa in casas:
            row[casa] = data_por_casa.get(casa, {}).get(m, None)
        rows.append(row)
    df = pd.DataFrame(rows)
    return df

# ============ UI ============

colA, colB, colC = st.columns(3)
with colA:
    url_betano = st.text_input("URL Betano", placeholder="https://www.betano.bet.br/...", value="")
with colB:
    url_bet365 = st.text_input("URL Bet365", placeholder="https://www.bet365.bet.br/...", value="")
with colC:
    url_kto = st.text_input("URL KTO", placeholder="https://kto.bet.br/...", value="")

st.divider()
btn = st.button("🔄 Atualizar Odds")

if btn:
    with st.spinner("Buscando e comparando... (até ~15s)"):
        try:
            links = {"Betano": url_betano, "Bet365": url_bet365, "KTO": url_kto}
            df = compare(links)

            if df.empty:
                st.warning("Não encontrei odds de escanteios nos textos das páginas. "
                           "Verifique se as URLs estão no **mercado de escanteios totais** "
                           "e tente novamente.")
            else:
                st.success("Odds atualizadas com sucesso!")
                st.dataframe(df, use_container_width=True)

                st.caption("Obs.: “None” significa que aquela casa não mostrou esse mercado no momento.")
        except Exception as e:
            st.error(f"Erro ao buscar: {e}")
else:
    st.info("Cole as 3 URLs do MESMO jogo e clique em **Atualizar Odds**.")
