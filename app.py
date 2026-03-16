import time
import requests
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ── Config ─────────────────────────────────────────────────────────────────
TICKERS = ["CAT","MRK","GOOGL","MA","PM","AMAT","LLY","GLD","MSTR","NEM","MELI","DE","COST","PEP","PAM"]
RATIOS  = {"CAT":20,"MRK":5,"GOOGL":58,"MA":33,"PM":18,"AMAT":5,"LLY":56,"GLD":50,
           "MSTR":20,"NEM":3,"MELI":120,"DE":40,"COST":48,"PEP":18,"PAM":25}
ARG_ADR = {"PAM"}
PORTFOLIOS = [
    {"DE":11.78,"MRK":6.15,"LLY":18.54,"NEM":43.31,"MSTR":0.80,"COST":7.79,"PEP":5.89,"PAM":5.74},
    {"AMAT":9.83,"MRK":38.07,"CAT":24.42,"GOOGL":16.87,"PM":8.49,"MA":2.31},
]
# Ticker de referencia y nominales iniciales por portfolio (igual que la app web)
PORT_DEFAULTS = [("DE", 9), ("AMAT", 1)]
CACHE_TTL = 300  # segundos

st.set_page_config(page_title="CEDEAR Dashboard", page_icon="📈", layout="wide")

# ── Helpers ─────────────────────────────────────────────────────────────────
def calc_rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    closes = np.array(closes)
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g, avg_l = gains[:n].mean(), losses[:n].mean()
    for g, l in zip(gains[n:], losses[n:]):
        avg_g = (avg_g * (n - 1) + g) / n
        avg_l = (avg_l * (n - 1) + l) / n
    return 100 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)

def rsi_color(r):
    if r is None:   return "gray"
    if r <= 30:     return "green"
    if r >= 70:     return "red"
    return "orange"

def pct(a, b):
    return ((a - b) / abs(b) * 100) if b else None

def fmt(n, dec=1, sign=False):
    if n is None or (isinstance(n, float) and np.isnan(n)): return "—"
    prefix = "+" if sign and n > 0 else ""
    return f"{prefix}{n:.{dec}f}"

# ── Caché de datos ─────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def fetch_dolar():
    try:
        r = requests.get("https://api.bluelytics.com.ar/v2/latest", timeout=8)
        d = r.json()
        return d.get("blue", {}).get("value_sell") or d.get("oficial", {}).get("value_sell")
    except Exception:
        return None

@st.cache_data(ttl=CACHE_TTL)
def fetch_quote(ticker):
    df = yf.Ticker(ticker).history(period="3mo", interval="1h")
    if df.empty:
        return None, None
    closes = df["Close"].dropna().tolist()
    return closes[-1], calc_rsi(closes)

@st.cache_data(ttl=CACHE_TTL)
def fetch_search(ticker):
    df = yf.Ticker(ticker).history(period="3mo", interval="1h")
    if df.empty:
        return None, None, None
    closes = df["Close"].dropna().tolist()
    ars_price = None
    try:
        df_ba = yf.Ticker(ticker + ".BA").history(period="5d", interval="1d")
        if not df_ba.empty:
            ars_price = float(df_ba["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return closes[-1], calc_rsi(closes), ars_price

@st.cache_data(ttl=CACHE_TTL)
def fetch_options(ticker):
    try:
        from datetime import datetime, timedelta
        hoy, limite = datetime.now().date(), (datetime.now() + timedelta(days=90)).date()
        tk     = yf.Ticker(ticker)
        fechas = tk.options
        rows   = []
        for f in fechas:
            fd = datetime.strptime(f, "%Y-%m-%d").date()
            if not (hoy <= fd <= limite): continue
            dias = (fd - hoy).days
            oi = vol = 0
            try:
                chain = tk.option_chain(f)
                oi  = int(chain.calls["openInterest"].sum() + chain.puts["openInterest"].sum())
                vol = int(chain.calls["volume"].fillna(0).sum() + chain.puts["volume"].fillna(0).sum())
            except Exception:
                pass
            rows.append({"ticker": ticker, "fecha": f, "días": dias, "open_interest": oi, "volumen": vol})
        return rows
    except Exception:
        return []

# ── Sección 1: RSI Grid ────────────────────────────────────────────────────
def section_rsi(dolar_blue):
    st.subheader("CEDEARs + ADRs · RSI 14 · 1H · 3 meses")

    cols = st.columns(5)
    for i, ticker in enumerate(TICKERS):
        with cols[i % 5]:
            with st.spinner(""):
                price, rsi = fetch_quote(ticker)

            if price is None:
                st.error(f"**{ticker}** — sin datos")
                continue

            ratio = RATIOS.get(ticker, 1)
            ars   = round(price / ratio * dolar_blue) if dolar_blue else None
            ars_s = f"${ars:,.0f}".replace(",", ".") if ars else "—"
            flag  = " 🇦🇷" if ticker in ARG_ADR else ""
            rsi_s = f"{rsi:.1f}" if rsi is not None else "—"
            color = rsi_color(rsi)

            badge = ""
            if rsi is not None:
                if rsi <= 30:  badge = "🟢 SOBREVENDIDO"
                elif rsi >= 70: badge = "🔴 SOBRECOMPRADO"

            st.metric(label=f"**{ticker}**{flag}", value=ars_s,
                      help=f"USD {price:.2f} · ratio {ratio}:1")
            st.markdown(f"RSI: :{color}[**{rsi_s}**] {badge}")
            st.divider()

# ── Sección 2: Búsqueda ────────────────────────────────────────────────────
def section_search(dolar_blue):
    st.subheader("Consulta otro ticker")
    col1, col2 = st.columns([3, 1])
    ticker = col1.text_input("Ticker", placeholder="AAPL, MSFT, NVDA…", max_chars=10, label_visibility="collapsed").upper()
    buscar = col2.button("Consultar", width="stretch")

    if buscar and ticker:
        with st.spinner(f"Consultando {ticker}…"):
            price, rsi, ars_price = fetch_search(ticker)
        if price is None:
            st.error(f"No se encontró {ticker}")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("USD", f"{price:.2f}")
            c2.metric("ARS", f"${ars_price:,.0f}".replace(",", ".") if ars_price else "—")
            c3.metric("RSI 14", f"{rsi:.1f}" if rsi else "—")

# ── Sección 3: Portfolio ───────────────────────────────────────────────────
def port_error(tickers, prices, portfolio, k, ref):
    total = k * prices[ref] / (portfolio[ref] / 100)
    noms  = [max(1, round(total * portfolio[t] / 100 / prices[t])) for t in tickers]
    tr    = sum(n * prices[tickers[i]] for i, n in enumerate(noms))
    return sum(abs(n * prices[tickers[i]] / tr * 100 - portfolio[tickers[i]]) for i, n in enumerate(noms))

def section_portfolio(dolar_blue):
    st.subheader("Calculadora de portfolio")
    if not dolar_blue:
        st.warning("Sin cotización del dólar, no se puede calcular.")
        return

    # Inicializar session_state solo la primera vez
    for i, (def_ref, def_k) in enumerate(PORT_DEFAULTS):
        st.session_state.setdefault(f"port{i}_ref", def_ref)
        st.session_state.setdefault(f"port{i}_k",   def_k)

    tabs = st.tabs(["Portfolio 1 · DE/MRK/LLY/NEM/MSTR/COST/PEP/PAM",
                    "Portfolio 2 · MRK/CAT/GOOGL/AMAT/PM/MA"])

    for i, (tab, portfolio) in enumerate(zip(tabs, PORTFOLIOS)):
        with tab:
            tickers = list(portfolio.keys())
            prices  = {}
            for t in tickers:
                p, _ = fetch_quote(t)
                if p:
                    prices[t] = p / RATIOS.get(t, 1) * dolar_blue

            if len(prices) < len(tickers):
                st.info("⏳ Cargando precios…")
                continue

            col1, col2 = st.columns([2, 1])
            ref = col1.selectbox("Referencia", tickers, key=f"port{i}_ref")
            k   = col2.number_input("Nominales", min_value=1, key=f"port{i}_k")

            # Sugerencia
            for k_sug in range(1, 301):
                if port_error(tickers, prices, portfolio, k_sug, ref) < 5:
                    if k_sug != k:
                        st.caption(f"Sugerido: {k_sug} nominales de {ref}")
                    break

            total = k * prices[ref] / (portfolio[ref] / 100)
            rows  = []
            for t in tickers:
                nom    = max(1, round(total * portfolio[t] / 100 / prices[t]))
                val    = nom * prices[t]
                _, rsi = fetch_quote(t)
                rows.append({"Ticker": t, "Nominales": nom,
                             "Obj %": f"{portfolio[t]:.1f}%",
                             "Real %": f"{val/total*100:.1f}%",
                             "RSI": f"{rsi:.1f}" if rsi else "—",
                             "ARS": f"${round(val):,}".replace(",", ".")})

            total_real = sum(r["Nominales"] * prices[r["Ticker"]] for r in rows)
            err        = port_error(tickers, prices, portfolio, k, ref)
            err_color  = "green" if err < 5 else "orange" if err < 15 else "red"

            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.markdown(f"Total: **${round(total_real):,}** ARS · Error aprox.: :{err_color}[**{err:.1f}%**]")

# ── Sección 4: Opciones ────────────────────────────────────────────────────
def section_options():
    st.subheader("Vencimientos de opciones · próximos 90 días")

    if st.button("⟳ Consultar vencimientos"):
        with st.spinner("Consultando opciones… puede tardar ~30s"):
            all_rows = []
            for t in TICKERS:
                all_rows.extend(fetch_options(t))
            st.session_state["opt_data"] = all_rows

    if "opt_data" not in st.session_state or not st.session_state["opt_data"]:
        st.caption("Presioná el botón para cargar.")
        return

    rows = st.session_state["opt_data"]
    df   = pd.DataFrame(rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total registros", len(df))
    next_row = df.nsmallest(1, "días").iloc[0] if len(df) else None
    c2.metric("Próximo vencimiento", next_row["fecha"] if next_row is not None else "—",
              delta=f"{next_row['ticker']} · {next_row['días']}d" if next_row is not None else "")
    top = df.groupby("ticker").size().idxmax()
    c3.metric("Ticker más activo", top)
    c4.metric("Ventana cubierta", f"{df['días'].max()}d")

    sort_by = st.selectbox("Ordenar por", ["días", "open_interest", "volumen"], label_visibility="collapsed")
    st.dataframe(df.sort_values(sort_by, ascending=(sort_by == "días")).reset_index(drop=True),
                 hide_index=True, width="stretch")

# ── Sección 5: Valuación ───────────────────────────────────────────────────
def q_label(offset):
    from datetime import datetime
    now = datetime.now()
    q, yr = (now.month - 1) // 3 + 1, now.year
    for _ in range(offset):
        q -= 1
        if q < 1: q, yr = 4, yr - 1
    return f"Q{q}-{yr % 100:02d}"

def section_valuation():
    st.subheader("Valuación por quarters")

    # Import CSV
    uploaded = st.file_uploader("Importar CSV", type="csv", label_visibility="collapsed")
    if uploaded:
        df_csv = pd.read_csv(uploaded)
        df_csv.columns = df_csv.columns.str.lower().str.strip()
        alias = {"ocf": ["ocf","ocf_m","operating_cash_flow","fcf"],
                 "sh":  ["shares","shares_m","diluted_shares","acciones"],
                 "sp":  ["price","stock_price","sp","precio"],
                 "bb":  ["buyback","buyback_pct","buyback_%","bb","recompra"]}
        mapped = {}
        for key, names in alias.items():
            for n in names:
                if n in df_csv.columns:
                    mapped[key] = n; break
        if "ticker" in df_csv.columns:
            st.session_state["val_ticker"] = str(df_csv["ticker"].iloc[0]).upper()
        for i in range(min(5, len(df_csv))):
            row = df_csv.iloc[i]
            lbl = str(row.get("label", row.get("quarter", row.get("q", "")))).strip() or q_label(i)
            st.session_state[f"q{i}_label"] = lbl
            for key, col in mapped.items():
                st.session_state[f"q{i}_{key}"] = float(row[col]) if row[col] else 0.0

    ticker = st.text_input("Ticker", key="val_ticker", placeholder="AMAT").upper()

    # Inputs de quarters
    quarters = []
    cols = st.columns(5)
    for i, col in enumerate(cols):
        with col:
            lbl = st.text_input("Quarter", value=st.session_state.get(f"q{i}_label", q_label(i)),
                                key=f"q{i}_label_input", label_visibility="visible")
            ocf = st.number_input("OCF (M)",   value=st.session_state.get(f"q{i}_ocf", 0.0), key=f"q{i}_ocf", step=0.1)
            sh  = st.number_input("Shares (M)", value=st.session_state.get(f"q{i}_sh",  0.0), key=f"q{i}_sh",  step=0.1)
            sp  = st.number_input("Stock Price", value=st.session_state.get(f"q{i}_sp", 0.0), key=f"q{i}_sp",  step=0.1)
            bb  = st.number_input("Buyback %",  value=st.session_state.get(f"q{i}_bb",  0.0), key=f"q{i}_bb",  step=0.1)
            quarters.append({"label": lbl, "ocf": ocf, "sh": sh, "sp": sp, "bb": bb or None})

    # Gráfico
    filled = [q for q in reversed(quarters) if q["ocf"] and q["sh"] and q["sp"]]
    if filled:
        fig = go.Figure()
        labels = [q["label"] for q in filled]
        fig.add_trace(go.Scatter(x=labels, y=[q["sp"] for q in filled],
                                 name="Stock Price", yaxis="y1",
                                 line=dict(color="#cc241d", width=2), fill="tozeroy",
                                 fillcolor="rgba(204,36,29,.1)"))
        fig.add_trace(go.Scatter(x=labels, y=[q["ocf"]/q["sh"] for q in filled],
                                 name="OCF/Share", yaxis="y2",
                                 line=dict(color="#458588", width=2)))
        bb_vals = [q["bb"] for q in filled if q["bb"]]
        if bb_vals:
            fig.add_trace(go.Scatter(x=[q["label"] for q in filled if q["bb"]],
                                     y=bb_vals, name="Buyback %", yaxis="y3",
                                     line=dict(color="#d79921", width=2, dash="dot")))
        fig.update_layout(
            title=f"{ticker} · OCF/Share · Stock Price · Buyback" if ticker else "",
            yaxis=dict(title="Price", side="left"),
            yaxis2=dict(title="OCF/Share", overlaying="y", side="right"),
            yaxis3=dict(title="Buyback %", overlaying="y", side="right", anchor="free", position=1),
            legend=dict(orientation="h", y=-0.2),
            height=380, margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, width="stretch")

        # Export CSV
        df_exp = pd.DataFrame([{"ticker": ticker, **q} for q in quarters])
        st.download_button("⬇ CSV", df_exp.to_csv(index=False),
                           file_name=f"{ticker.lower()}_valuacion.csv", mime="text/csv")

    # Informe
    if len(filled) >= 2:
        section_informe(filled, ticker)

def section_informe(filled, ticker):
    st.subheader(f"Informe & Veredicto · {ticker}")

    newest, oldest = filled[-1], filled[0]
    ocfps_n = newest["ocf"] / newest["sh"]
    ocfps_o = oldest["ocf"] / oldest["sh"]

    price_chg  = pct(newest["sp"], oldest["sp"])
    ocfps_chg  = pct(ocfps_n, ocfps_o)
    share_chg  = pct(newest["sh"], oldest["sh"])
    drift      = (price_chg - ocfps_chg) if price_chg is not None and ocfps_chg is not None else None
    pocf_n     = newest["sp"] / ocfps_n
    pocf_o     = oldest["sp"] / ocfps_o
    pocf_chg   = pct(pocf_n, pocf_o)
    bb_vals    = [q["bb"] for q in filled if q["bb"]]
    avg_bb     = sum(bb_vals) / len(bb_vals) if bb_vals else None

    # Métricas
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cambio precio",        f"{fmt(price_chg, 1, True)}%")
    c2.metric("OCF/Share Δ",          f"{fmt(ocfps_chg, 1, True)}%",
              delta=f"{ocfps_o:.3f} → {ocfps_n:.3f}")
    c3.metric("Acciones Δ",           f"{fmt(share_chg, 1, True)}%")
    c4.metric("P/OCF múltiplo",       f"{pocf_n:.1f}x",
              delta=f"era {pocf_o:.1f}x")
    c5.metric("Drift precio vs OCF",  f"{fmt(drift, 1, True)}%")

    if avg_bb is not None:
        st.metric("Buyback promedio", f"{fmt(avg_bb, 2, True)}%",
                  delta=f"último: {fmt(filled[-1]['bb'], 2, True)}%" if filled[-1]["bb"] else "")

    # Escenarios
    scenarios = [
        ("Subida justificada",       price_chg is not None and ocfps_chg is not None and abs(drift) < 20 and ocfps_chg > 0,  "✅"),
        ("Expansión de múltiplo",    drift is not None and (drift > 30 or (pocf_chg or 0) > 40),                               "⚠️"),
        ("Oportunidad potencial",    ocfps_chg is not None and ocfps_chg > 10 and drift is not None and drift < -10,           "✅"),
        ("Dilución perjudicial",     share_chg is not None and share_chg > 5 and (ocfps_chg is None or ocfps_chg < (price_chg or 0)/2), "❌"),
        ("Recompra + crecimiento",   share_chg is not None and share_chg < -3 and ocfps_chg is not None and ocfps_chg > 10,   "✅"),
        ("Precio deprimido, OCF↑",   price_chg is not None and price_chg < -5 and ocfps_chg is not None and ocfps_chg > 0,    "🔵"),
    ]
    active = [(name, icon) for name, cond, icon in scenarios if cond]
    if active:
        st.markdown("**Escenarios activos:** " + "  ·  ".join(f"{icon} {name}" for name, icon in active))

    # Veredicto
    score, notes = 50, []
    if ocfps_chg is not None:
        if ocfps_chg > 30:   score += 20; notes.append(f"✅ OCF/share +{ocfps_chg:.1f}% — crecimiento sólido")
        elif ocfps_chg > 10: score += 10; notes.append(f"✅ OCF/share +{ocfps_chg:.1f}% — tendencia positiva")
        elif ocfps_chg > 0:  score += 3;  notes.append(f"· OCF/share creció levemente ({ocfps_chg:.1f}%)")
        else:                 score -= 15; notes.append(f"❌ OCF/share {ocfps_chg:.1f}% — deterioro operativo")
    if drift is not None:
        if drift > 50:        score -= 20; notes.append(f"❌ Precio corrió {drift:.1f}% más que OCF — expansión agresiva")
        elif drift > 20:      score -= 8;  notes.append(f"⚠️ Precio creció {drift:.1f}% más que fundamentos")
        elif abs(drift) <= 15:score += 8;  notes.append(f"✅ Precio alineado con OCF (drift: {drift:.1f}%)")
        elif drift < -15:     score += 12; notes.append("✅ Precio rezagado vs OCF — posible subvaluación")
    if share_chg is not None:
        if share_chg < -5:    score += 15; notes.append(f"✅ Recompra significativa: {share_chg:.1f}%")
        elif share_chg < 0:   score += 5;  notes.append(f"✅ Leve reducción de acciones ({share_chg:.1f}%)")
        elif share_chg < 3:                notes.append(f"· Acciones estables (+{share_chg:.1f}%)")
        elif share_chg < 8:   score -= 8;  notes.append(f"⚠️ Dilución moderada: +{share_chg:.1f}%")
        else:                  score -= 18; notes.append(f"❌ Dilución importante: +{share_chg:.1f}%")
    if pocf_chg is not None:
        if pocf_chg > 50:     score -= 10; notes.append(f"⚠️ P/OCF se expandió {pocf_chg:.1f}% (ahora {pocf_n:.1f}x)")
        elif pocf_chg < -20:  score += 8;  notes.append(f"✅ P/OCF se contrajo {pocf_chg:.1f}% — acción más barata")

    score = max(0, min(100, score))
    label = ("Fundamentos sólidos" if score >= 75 else "Perspectiva favorable" if score >= 60
             else "Señal mixta" if score >= 45 else "Precaución" if score >= 30 else "Fundamentos débiles")
    color = "green" if score >= 60 else "orange" if score >= 40 else "red"

    st.markdown(f"### Veredicto: :{color}[**{score:.0f}/100 — {label}**]")
    for note in notes:
        st.markdown(f"- {note}")

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    st.title("📈 CEDEAR Dashboard · RSI Monitor")

    dolar_blue = fetch_dolar()
    if dolar_blue:
        st.caption(f"💱 Dólar Blue (venta): **${dolar_blue:,.2f}**")
    else:
        st.caption("💱 Dólar Blue: no disponible")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "RSI Monitor", "Búsqueda", "Portfolio", "Opciones", "Valuación"
    ])

    with tab1: section_rsi(dolar_blue)
    with tab2: section_search(dolar_blue)
    with tab3: section_portfolio(dolar_blue)
    with tab4: section_options()
    with tab5: section_valuation()

if __name__ == "__main__":
    main()