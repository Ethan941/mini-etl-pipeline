"""Crypto Pulse : dashboard du mini-etl-pipeline. Lancer : streamlit run dashboard/app.py"""
import json
import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB = ROOT / os.getenv("DUCKDB_PATH", "data/crypto.duckdb")

COLORS = {
    "bitcoin": "#FFB547",
    "ethereum": "#8B5CF6",
    "solana": "#2DE2A6",
    "cardano": "#38BDF8",
    "ripple": "#FF5C9A",
}
FALLBACK = ["#F97316", "#A3E635", "#22D3EE", "#E879F9", "#FACC15"]
GREEN, RED = "#2DE2A6", "#FF4D6D"
# id: (symbole, prix de départ €, offre en circulation, volume 24h €)
DEMO = {
    "bitcoin": ("BTC", 69000, 19.8e6, 3e10),
    "ethereum": ("ETH", 2060, 120e6, 1.5e10),
    "solana": ("SOL", 82, 440e6, 3e9),
    "cardano": ("ADA", 0.17, 36e9, 4e8),
    "ripple": ("XRP", 1.14, 57e9, 1.2e9),
}
METRICS = {"Prix": "current_price", "Capitalisation": "market_cap", "Volume": "total_volume"}
PERIODS = {"24 h": pd.Timedelta(hours=24), "7 j": pd.Timedelta(days=7), "30 j": pd.Timedelta(days=30), "Tout": None}


def color(cid, i=0):
    return COLORS.get(cid, FALLBACK[i % len(FALLBACK)])


@st.cache_data(ttl=60)
def load_real():
    if not DB.exists():
        return pd.DataFrame()
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(
            "select id, symbol, current_price, market_cap, total_volume,"
            " price_change_percentage_24h as change_24h, last_updated as ts"
            " from main.stg_prices order by ts"
        ).df()
    except duckdb.Error:  # dbt n'a pas encore tourné
        return pd.DataFrame()
    finally:
        con.close()


@st.cache_data
def make_demo():
    """Historique simulé (marche aléatoire, 60 jours, 1 point par heure) : sert à montrer le rendu."""
    rng = np.random.default_rng(42)
    idx = pd.date_range(end=pd.Timestamp.now().floor("h"), periods=24 * 60, freq="h")
    frames = []
    for cid, (sym, p0, supply, vol) in DEMO.items():
        r = rng.normal(0.0002, 0.012, len(idx))
        price = p0 * np.exp(np.cumsum(r) - r.sum())
        volume = vol * (1 + 0.3 * np.sin(np.arange(len(idx)) / 30) + rng.normal(0, 0.05, len(idx)))
        d = pd.DataFrame({"id": cid, "symbol": sym, "current_price": price, "market_cap": price * supply,
                          "total_volume": volume, "ts": idx})
        d["change_24h"] = d["current_price"].pct_change(24) * 100
        frames.append(d)
    return pd.concat(frames).sort_values("ts").reset_index(drop=True)


def style():
    st.markdown(
        """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp { background:
  radial-gradient(900px 500px at 8% -5%, rgba(139,92,246,.30), transparent 60%),
  radial-gradient(800px 500px at 95% 10%, rgba(45,226,166,.16), transparent 60%),
  radial-gradient(700px 600px at 50% 110%, rgba(255,92,154,.16), transparent 60%), #0B0B1A;
  background-size: 140% 140%; animation: drift 18s ease-in-out infinite alternate; }
@keyframes drift { to { background-position: 12% 8%, 90% 0%, 40% 100%, 0 0; } }
#MainMenu, footer, .stAppDeployButton { visibility: hidden; } header { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1250px; }
.hero h1 { font-size: 3rem; font-weight: 800; margin: 0; letter-spacing: -1px;
  background: linear-gradient(90deg, #8B5CF6, #38BDF8, #2DE2A6, #FFB547, #FF5C9A, #8B5CF6);
  background-size: 300% 100%; -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: shimmer 8s linear infinite; }
@keyframes shimmer { to { background-position: 300% 0; } }
.hero p { color: #9A9AB8; margin: .2rem 0 0; }
.badge { display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; padding: 6px 14px;
  border-radius: 999px; font-size: .78rem; font-weight: 600; color: #EAEAF5;
  background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #2DE2A6; box-shadow: 0 0 0 0 rgba(45,226,166,.7);
  animation: pulse 1.8s infinite; }
.dot.demo { background: #FFB547; box-shadow: 0 0 0 0 rgba(255,181,71,.7); animation-name: pulse2; }
@keyframes pulse { 70% { box-shadow: 0 0 0 10px rgba(45,226,166,0); } 100% { box-shadow: 0 0 0 0 rgba(45,226,166,0); } }
@keyframes pulse2 { 70% { box-shadow: 0 0 0 10px rgba(255,181,71,0); } 100% { box-shadow: 0 0 0 0 rgba(255,181,71,0); } }
[data-testid="stPlotlyChart"] { background: linear-gradient(145deg, rgba(255,255,255,.05), rgba(255,255,255,.015));
  border: 1px solid rgba(255,255,255,.08); border-radius: 20px; padding: 10px;
  animation: up .9s cubic-bezier(.2,.9,.2,1) both; transition: transform .3s, box-shadow .3s, border-color .3s; }
[data-testid="stPlotlyChart"]:hover { transform: translateY(-4px); border-color: rgba(139,92,246,.6);
  box-shadow: 0 18px 50px -18px rgba(139,92,246,.7); }
@keyframes up { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: none; } }
h3 { font-weight: 800 !important; letter-spacing: -.3px; }
[data-testid="stSidebar"] { background: rgba(20,20,43,.85); backdrop-filter: blur(14px);
  border-right: 1px solid rgba(255,255,255,.08); }
</style>""",
        unsafe_allow_html=True,
    )


KPI_HTML = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
*{box-sizing:border-box;margin:0;font-family:Inter,sans-serif}
body{background:transparent;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;padding:8px 2px 14px}
.card{--c:#fff;position:relative;padding:18px 18px 10px;border-radius:20px;overflow:hidden;
  background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.1);opacity:0;transform:translateY(26px) scale(.95);
  animation:in .7s cubic-bezier(.2,.9,.2,1) forwards;animation-delay:calc(var(--i)*110ms);
  transition:transform .25s,box-shadow .25s,border-color .25s}
.card:hover{transform:translateY(-7px) scale(1.03);border-color:var(--c);box-shadow:0 16px 44px -14px var(--c)}
.card:before{content:"";position:absolute;top:-70px;left:-60px;width:170px;height:170px;border-radius:50%;
  background:var(--c);filter:blur(60px);opacity:.30;animation:float 6s ease-in-out infinite alternate}
@keyframes in{to{opacity:1;transform:none}}
@keyframes float{to{transform:translate(90px,50px)}}
.top{position:relative;display:flex;justify-content:space-between;align-items:center}
.sym{font-weight:800;font-size:1.05rem;letter-spacing:.5px}
.name{color:#9A9AB8;font-size:.72rem;text-transform:capitalize}
.pill{font-size:.72rem;font-weight:700;padding:3px 9px;border-radius:999px}
.up{color:#2DE2A6;background:rgba(45,226,166,.14)}.down{color:#FF4D6D;background:rgba(255,77,109,.14)}
.price{position:relative;font-size:1.55rem;font-weight:800;margin:12px 0 2px;letter-spacing:-.5px}
svg{position:relative;width:100%;height:46px;display:block;margin-top:2px}
.line{fill:none;stroke:var(--c);stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;
  stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.6s ease forwards;animation-delay:calc(var(--i)*110ms + 400ms)}
.area{fill:var(--c);opacity:0;animation:fade 1s ease forwards;animation-delay:calc(var(--i)*110ms + 1400ms)}
@keyframes draw{to{stroke-dashoffset:0}}@keyframes fade{to{opacity:.12}}
</style>
<div class="grid" id="g"></div>
<script>
const D=__DATA__;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d)=>new Intl.NumberFormat('fr-FR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
const g=document.getElementById('g');
D.forEach((d,i)=>{
  const up=d.change>=0;
  g.insertAdjacentHTML('beforeend',`<div class="card" style="--c:${esc(d.color)};--i:${i}">
    <div class="top"><div><div class="sym">${esc(d.symbol)}</div><div class="name">${esc(d.name)}</div></div>
    <span class="pill ${up?'up':'down'}">${up?'▲':'▼'} ${fmt(Math.abs(d.change),2)} %</span></div>
    <div class="price" data-v="${d.price}" data-d="${d.dec}" data-i="${i}">0 €</div>
    <svg viewBox="0 0 100 30" preserveAspectRatio="none">
      <path class="area" d="${esc(d.path)} L100,30 L0,30 Z"/>
      <path class="line" pathLength="1" d="${esc(d.path)}" vector-effect="non-scaling-stroke"/></svg></div>`);
});
document.querySelectorAll('.price').forEach(el=>{
  const to=+el.dataset.v,dec=+el.dataset.d,t0=performance.now()+(+el.dataset.i)*110;
  const step=t=>{const p=Math.min(Math.max((t-t0)/1500,0),1),e=p===1?1:1-Math.pow(2,-10*p);
    el.textContent=fmt(to*e,dec)+' €';if(p<1)requestAnimationFrame(step)};
  requestAnimationFrame(step);
});
</script>"""


def kpi_cards(df, ids):
    cards = []
    for i, cid in enumerate(ids):
        d = df[df["id"] == cid]
        last = d.iloc[-1]
        y = d["current_price"].tail(40).to_numpy()
        span = (y.max() - y.min()) or 1
        pts = [(100 * k / max(len(y) - 1, 1), 27 - 24 * (v - y.min()) / span) for k, v in enumerate(y)]
        if len(pts) < 2:
            pts = [(0, 15), (100, 15)]
        path = "M" + " L".join(f"{x:.1f},{v:.1f}" for x, v in pts)
        change = last["change_24h"] if pd.notna(last["change_24h"]) else 0.0
        cards.append({"name": cid, "symbol": str(last["symbol"]).upper(), "price": float(last["current_price"]),
                      "dec": 4 if last["current_price"] < 10 else 2, "change": float(change),
                      "color": color(cid, i), "path": path})
    payload = json.dumps(cards).replace("</", "<\\/")
    st.iframe(KPI_HTML.replace("__DATA__", payload), height=215)


def perf_chart(df, ids, col, base100, label):
    piv = df.pivot_table(index="ts", columns="id", values=col).sort_index().ffill()[ids]
    if base100:
        piv = piv / piv.bfill().iloc[0] * 100
    frames_idx = np.unique(np.linspace(2, len(piv), min(60, len(piv)), dtype=int))
    fig = go.Figure()
    for i, cid in enumerate(ids):
        fig.add_trace(go.Scatter(x=piv.index, y=piv[cid], name=cid.capitalize(), mode="lines",
                                 line=dict(color=color(cid, i), width=3, shape="spline", smoothing=.6),
                                 hovertemplate="%{y:,.2f}<extra>" + cid.capitalize() + "</extra>"))
    fig.frames = [
        go.Frame(name=str(k), data=[go.Scatter(x=piv.index[:k], y=piv[c].iloc[:k]) for c in ids])
        for k in frames_idx
    ]
    ymin, ymax = float(piv.min().min()), float(piv.max().max())
    pad = (ymax - ymin) * 0.06 or 1
    fig.update_layout(
        height=430, hovermode="x unified", margin=dict(l=10, r=40, t=30, b=10),
        xaxis=dict(range=[piv.index[0], piv.index[-1]], showgrid=False),
        yaxis=dict(range=[ymin - pad, ymax + pad], gridcolor="rgba(255,255,255,.07)",
                   title="Base 100" if base100 else label),
        legend=dict(orientation="h", y=1.1, x=0),
        updatemenus=[dict(type="buttons", direction="left", x=1, xanchor="right", y=1.17, showactive=False,
                          bgcolor="rgba(139,92,246,.25)", bordercolor="rgba(139,92,246,.8)",
                          buttons=[dict(label="▶ Rejouer", method="animate",
                                        args=[None, dict(frame=dict(duration=45, redraw=False),
                                                         transition=dict(duration=0), fromcurrent=False)])])],
    )
    return fig


def change_chart(df, ids):
    last = df[df["id"].isin(ids)].sort_values("ts").groupby("id").tail(1).sort_values("change_24h")
    ch = last["change_24h"].fillna(0)
    fig = go.Figure(go.Bar(
        x=ch, y=last["symbol"].str.upper(), orientation="h",
        marker=dict(color=[GREEN if v >= 0 else RED for v in ch], cornerradius=8),
        text=[f"{v:+.2f} %" for v in ch], textposition="outside", cliponaxis=False,
        hovertemplate="%{y} : %{x:+.2f} %<extra></extra>"))
    lim = max(float(ch.abs().max()), 1) * 1.45  # marge pour que les libellés ne touchent pas les noms
    fig.update_layout(height=360, margin=dict(l=10, r=20, t=20, b=10),
                      xaxis=dict(range=[-lim, lim], showgrid=False, zeroline=True,
                                 zerolinecolor="rgba(255,255,255,.3)", ticksuffix=" %"),
                      yaxis=dict(showgrid=False, automargin=True))
    return fig


def bubble_chart(df, ids):
    d = df[df["id"].isin(ids)].copy()
    steps = np.unique(np.linspace(0, d["ts"].nunique() - 1, min(40, d["ts"].nunique()), dtype=int))
    keep = pd.Series(sorted(d["ts"].unique())).iloc[steps]
    d = d[d["ts"].isin(keep)].dropna(subset=["market_cap", "total_volume"])
    d["frame"] = d["ts"].dt.strftime("%d/%m %H:%M")
    d["nom"] = d["id"].str.capitalize()
    fig = px.scatter(d, x="total_volume", y="market_cap", size="market_cap", color="nom", animation_frame="frame",
                     log_x=True, log_y=True, size_max=60, hover_name="nom",
                     color_discrete_map={c.capitalize(): color(c, i) for i, c in enumerate(ids)},
                     range_x=[d["total_volume"].min() * .4, d["total_volume"].max() * 3.5],
                     range_y=[d["market_cap"].min() * .4, d["market_cap"].max() * 4],
                     labels={"total_volume": "Volume (€)", "market_cap": "Capitalisation (€)", "nom": ""})
    fig.update_traces(marker=dict(line=dict(width=1.5, color="rgba(255,255,255,.5)"), opacity=.85))
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h", y=1.1),
                      xaxis=dict(gridcolor="rgba(255,255,255,.07)", dtick=1),  # 1 graduation par puissance de 10
                      yaxis=dict(gridcolor="rgba(255,255,255,.07)", dtick=1))
    return fig


def main():
    st.set_page_config(page_title="Crypto Pulse", page_icon="⚡", layout="wide")
    style()
    real = load_real()

    with st.sidebar:
        st.markdown("### ⚙️ Contrôles")
        demo = st.toggle("Mode démo (données simulées)", value=real["ts"].nunique() < 20 if len(real) else True,
                         help="Tant que le pipeline n'a pas accumulé d'historique, la démo montre le rendu final.")
        df = make_demo() if demo else real
        if df.empty:
            st.warning("Aucune donnée. Lance `python src/main.py` puis `dbt build`, ou active le mode démo.")
            st.stop()
        ids = sorted(df["id"].unique())
        sel = st.multiselect("Cryptos", ids, default=ids, format_func=str.capitalize)
        period = st.radio("Période", list(PERIODS), index=3, horizontal=True)
        metric = st.selectbox("Métrique du graphique", list(METRICS))
        base100 = st.toggle("Comparer en base 100", value=True)
    if not sel:
        st.info("Choisis au moins une crypto dans la barre latérale.")
        st.stop()

    df = df[df["id"].isin(sel)]
    if PERIODS[period] is not None:
        df = df[df["ts"] >= df["ts"].max() - PERIODS[period]]

    badge = ('<span class="dot demo"></span>Données simulées' if demo else
             f'<span class="dot"></span>Données réelles · dernière mise à jour {df["ts"].max():%d/%m/%Y %H:%M}')
    st.markdown(f'<div class="hero"><h1>Crypto Pulse</h1><p>Pipeline ELT · CoinGecko → DuckDB → dbt</p>'
                f'<span class="badge">{badge}</span></div>',
                unsafe_allow_html=True)

    kpi_cards(df, sel)
    st.markdown("### Évolution")
    st.plotly_chart(perf_chart(df, sel, METRICS[metric], base100, metric), width="stretch")
    left, right = st.columns(2)
    with left:
        st.markdown("### Variation 24 h")
        st.plotly_chart(change_chart(df, sel), width="stretch", config={"displayModeBar": False})
    with right:
        st.markdown("### Volume × capitalisation")
        st.plotly_chart(bubble_chart(df, sel), width="stretch", config={"displayModeBar": False})
    with st.expander("Données brutes"):
        st.dataframe(df.sort_values("ts", ascending=False).head(200), width="stretch")


# Plotly : fond transparent et police claire pour tous les graphiques
import plotly.io as pio  # noqa: E402

pio.templates["pulse"] = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#EAEAF5"),
    hoverlabel=dict(bgcolor="#14142B", font_size=13)))
pio.templates.default = "pulse"

main()
