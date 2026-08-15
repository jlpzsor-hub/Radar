
import os
import math
import requests
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

API_BASE = "https://api.odds-api.io/v3"
BOOKMAKERS = ["Bet365", "William Hill"]
ALLOWED_SPORTS = {"football", "tennis", "basketball"}

HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0b1220">
<title>Radar Privado</title>
<style>
:root{--bg:#0b1220;--panel:#142038;--line:#263957;--txt:#f8fafc;--muted:#94a3b8}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#07101e,#0b1220);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.shell{max-width:720px;margin:auto;padding:calc(env(safe-area-inset-top) + 18px) 16px 40px}
header{display:flex;justify-content:space-between;gap:12px}.eyebrow{font-size:11px;font-weight:900;letter-spacing:.13em;color:#7dd3fc}
h1{font-size:31px;line-height:1.03;margin:7px 0 8px}p{color:var(--muted);margin:0}.refresh{border:0;border-radius:14px;background:#fff;color:#08111f;font-weight:900;padding:11px 13px;height:42px}
.status{margin:20px 0 12px;padding:11px 13px;border:1px solid var(--line);border-radius:14px;color:var(--muted);font-size:13px}.ok{color:#b7f7df}
.row{display:flex;gap:8px;overflow:auto;padding:5px 0}.chip{white-space:nowrap;border:1px solid var(--line);background:#121c2f;color:#cbd5e1;border-radius:999px;padding:10px 13px;font-weight:800}.chip.active{background:white;color:#0b1220}
#cards{display:grid;gap:12px;margin-top:12px}.card{background:linear-gradient(180deg,#182640,#121c2f);border:1px solid var(--line);border-radius:22px;padding:17px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:center}.badge{font-size:12px;font-weight:900;padding:7px 9px;border-radius:999px}.better{background:#123c32;color:#75efc1}.covered{background:#17355d;color:#a6cbff}.review{background:#4b3410;color:#ffd68a}
.metric{font-size:21px;font-weight:900}.metric small{display:block;color:var(--muted);font-size:10px;text-align:right}
.event{font-size:19px;font-weight:900;margin:13px 0 4px}.meta{font-size:12px;color:var(--muted)}
.market{margin:14px 0;background:rgba(255,255,255,.05);border-radius:15px;padding:12px}.market-title{font-weight:900;margin-bottom:4px}.selection{color:#dbe3ee}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:12px}
.book{display:block;background:rgba(255,255,255,.05);border:1px solid transparent;border-radius:15px;padding:12px;color:inherit;text-decoration:none}.book.clickable{cursor:pointer}.book.disabled{opacity:.68}
.book.best{border-color:#2d8c68;background:rgba(45,140,104,.12)}
.book-name{font-size:12px;color:var(--muted);font-weight:800}.book-price{font-size:27px;font-weight:950;margin-top:5px}
.best-label{font-size:10px;font-weight:900;color:#75efc1;margin-top:4px}.open-label{font-size:10px;font-weight:900;color:#9cc7ff;margin-top:4px}.fresh{font-size:11px;color:#94a3b8;margin-top:10px}.checkbar{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-top:12px}.checkbtn{border:1px solid var(--line);background:#0f1a2d;color:#fff;border-radius:12px;padding:9px 11px;font-weight:800;font-size:12px}
.msg{font-size:14px;line-height:1.45;color:#dbe3ee}
.secondary{font-size:12px;color:var(--muted);margin-top:8px}
.leg{background:rgba(255,255,255,.05);border-radius:14px;padding:11px;display:flex;justify-content:space-between;margin-top:8px}
.empty{text-align:center;color:var(--muted);padding:40px 15px}
footer{font-size:11px;color:#718096;line-height:1.5;padding:25px 4px}
</style>
</head>
<body>
<div class="shell">
<header>
<div>
<div class="eyebrow">RADAR PRIVADO · V0.4</div>
<h1>Encuentra dónde pagan mejor.</h1>
<p>Bet365 + William Hill · Fútbol · Tenis · Baloncesto</p>
</div>
<button class="refresh" id="refresh">Actualizar</button>
</header>

<div id="status" class="status">Comprobando conexión…</div>

<div class="row">
<button class="chip active" data-sport="all">Todo</button>
<button class="chip" data-sport="football">⚽ Fútbol</button>
<button class="chip" data-sport="tennis">🎾 Tenis</button>
<button class="chip" data-sport="basketball">🏀 Basket</button>
</div>

<div class="row">
<button class="chip mode active" data-mode="all">Todas</button>
<button class="chip mode" data-mode="better">Mejor pagadas</button>
<button class="chip mode" data-mode="covered">Ganancia cubierta</button>
</div>

<main id="cards"><div class="empty">Cargando oportunidades…</div></main>

<footer><b>V0.4 privada.</b> Las cuotas cambian. Verifica siempre partido, selección, mercado y precio antes de confirmar.</footer>
</div>

<script>
let sport="all",mode="all";
const cards=document.getElementById("cards"),statusEl=document.getElementById("status");

const esc=x=>String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
const n=x=>Number.isFinite(Number(x))?Number(x).toFixed(2):(x??"—");
const ev=x=>[x.home,x.away].filter(Boolean).join(" – ")||"Evento";

function better(x){
  const gap = Number(x.price_gap||0);
  const warn = gap >= 25;
  const badgeClass = warn ? "review" : "better";
  const badgeText = warn ? "🟠 REVISAR DIFERENCIA" : "🟢 PAGAN MEJOR AQUÍ";

  const books = (x.prices||[]).map(b=>{
    const hasLink = !!b.link;
    const inner = `
      <div class="book-name">${esc(b.bookmaker)}</div>
      <div class="book-price">@ ${esc(b.odds ?? "—")}</div>
      ${b.best?'<div class="best-label">MEJOR CUOTA</div>':''}
      ${hasLink?'<div class="open-label">ABRIR EN LA CASA ↗</div>':'<div class="open-label">ENLACE NO DISPONIBLE</div>'}`;
    return hasLink
      ? `<a class="book clickable ${b.best?"best":""}" href="${esc(b.link)}" target="_blank" rel="noopener noreferrer">${inner}</a>`
      : `<div class="book disabled ${b.best?"best":""}">${inner}</div>`;
  }).join("");

  return `<article class="card">
    <div class="top">
      <span class="badge ${badgeClass}">${badgeText}</span>
      <div class="metric">+${n(x.price_gap)}%<small>paga más</small></div>
    </div>
    <div class="event">${esc(ev(x))}</div>
    <div class="meta">${esc(x.league||x.sport||"")}</div>

    <div class="market">
      <div class="market-title">${esc(x.market_label||x.market||"Mercado")}</div>
      <div class="selection">${esc(x.selection_label||x.selection||"")}</div>
      <div class="compare">${books}</div>
    </div>

    <div class="msg">${esc(x.message)}</div>
    <div class="fresh" data-ts="${esc(x.updated_at||"")}">Actualizado recientemente</div>
    <div class="checkbar">
      <span class="secondary">Señal interna: +${n(x.provider_advantage)}%</span>
      <button class="checkbtn" onclick="event.stopPropagation();load()">Comprobar ahora</button>
    </div>
  </article>`;
}
function covered(x){
  let legs=(x.legs||[]).map(l=>{
    const content=`<div><b>${esc(l.bookmaker)}</b><br>${esc(l.selection)}</div><div style="text-align:right"><b>@ ${esc(l.odds||"—")}</b>${l.stake!=null?`<br>${n(l.stake)} €`:""}${l.link?'<br><span class="open-label">ABRIR ↗</span>':''}</div>`;
    return l.link
      ? `<a class="leg" style="color:inherit;text-decoration:none" href="${esc(l.link)}" target="_blank" rel="noopener noreferrer">${content}</a>`
      : `<div class="leg">${content}</div>`;
  }).join("");

  return `<article class="card">
    <div class="top">
      <span class="badge covered">🔵 RESULTADO CUBIERTO</span>
      <div class="metric">+${n(x.profit)}%<small>beneficio aprox.</small></div>
    </div>
    <div class="event">${esc(ev(x))}</div>
    <div class="meta">${esc(x.league||x.sport||"")}</div>
    <div class="market"><div class="market-title">${esc(x.market_label||x.market||"Mercado")}</div>${legs}</div>
    <div class="msg">${esc(x.message)}</div>
    <div class="fresh" data-ts="${esc(x.updated_at||"")}">Actualizado recientemente</div>
  </article>`;
}

function updateFreshness(){
  document.querySelectorAll(".fresh[data-ts]").forEach(el=>{
    const raw=el.dataset.ts;
    if(!raw){el.textContent="Actualizado recientemente";return;}
    const t=Date.parse(raw);
    if(!Number.isFinite(t)){el.textContent="Actualizado recientemente";return;}
    const sec=Math.max(0,Math.floor((Date.now()-t)/1000));
    if(sec<60) el.textContent=`Actualizado hace ${sec} s`;
    else if(sec<3600) el.textContent=`Actualizado hace ${Math.floor(sec/60)} min`;
    else el.textContent=`Actualizado hace ${Math.floor(sec/3600)} h`;
  });
}
setInterval(updateFreshness,10000);

async function load(){
  cards.innerHTML='<div class="empty">Buscando oportunidades…</div>';
  try{
    let r=await fetch(`/api/opportunities?sport=${encodeURIComponent(sport)}&mode=${encodeURIComponent(mode)}`,{cache:"no-store"});
    let d=await r.json();
    let items=d.items||[];
    cards.innerHTML=items.length
      ? items.map(x=>x.type==="covered"?covered(x):better(x)).join("")
      : '<div class="empty">Ahora mismo no hemos encontrado oportunidades con estos filtros.<br><br>Prueba a actualizar dentro de unos minutos.</div>';
    updateFreshness();
  }catch(e){
    cards.innerHTML=`<div class="empty">No se ha podido consultar el radar.<br>${esc(e.message)}</div>`;
  }
}

async function st(){
  try{
    let r=await fetch("/api/status");
    let s=await r.json();
    statusEl.textContent=s.ok?`● Conectado · ${s.bookmakers.join(" + ")}`:`● ${s.message}`;
    if(s.ok)statusEl.classList.add("ok");
  }catch(e){ statusEl.textContent="● Sin conexión"; }
}

document.querySelectorAll("[data-sport]").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("[data-sport]").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); sport=b.dataset.sport; load();
});
document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("[data-mode]").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); mode=b.dataset.mode; load();
});
document.getElementById("refresh").onclick=load;
st(); load();
</script>
</body>
</html>
"""

def api_key():
    return os.getenv("ODDS_API_KEY", "").strip()

def odds_get(path, params=None):
    if not api_key():
        raise RuntimeError("Falta ODDS_API_KEY")
    p = dict(params or {})
    p["apiKey"] = api_key()
    r = requests.get(f"{API_BASE}{path}", params=p, timeout=20)
    r.raise_for_status()
    return r.json()

def normalize_sport(value):
    if isinstance(value, dict):
        value = value.get("slug") or value.get("name")
    return (value or "").strip().lower()

def to_float(x):
    try: return float(x)
    except: return None

def ev_to_advantage(raw_ev):
    raw = to_float(raw_ev)
    if raw is None: return 0.0
    return round(raw - 100, 2) if raw >= 100 else round(raw, 2)

def canonical_market_name(name):
    n = (name or "").strip().lower()
    if n in {"ml", "moneyline", "match winner", "winner"}:
        return "ml"
    if "total" in n or "over/under" in n or "o/u" in n:
        return "totals"
    if "spread" in n or "handicap" in n or "hcp" in n:
        return "handicap"
    if "both teams" in n or "btts" in n:
        return "btts"
    if "draw no bet" in n or "dnb" in n:
        return "dnb"
    return n

def human_market(name, sport, hdp=None):
    c = canonical_market_name(name)
    if c == "ml":
        return "Ganador del partido"
    if c == "handicap":
        return "Hándicap"
    if c == "totals":
        unit = "goles" if sport == "football" else ("juegos" if sport == "tennis" else "puntos")
        return f"Total de {unit}"
    if c == "btts":
        return "Marcan ambos equipos"
    if c == "dnb":
        return "Empate no cuenta"
    return name or "Mercado"

def side_label_from_market(market, side):
    """Use the API's own market label first. This matters for Totals/Handicaps,
    where 'home'/'away' can mean Over/Under or the two handicap sides."""
    s = (side or "").strip().lower()
    value = market.get(s)
    if value not in (None, ""):
        return str(value)
    return ""

def human_selection(side, home, away, market_name="", hdp=None, market=None):
    s = (side or "").strip().lower()
    market = market or {}

    # First trust the label returned by the market object.
    raw_label = side_label_from_market(market, s).strip()
    if raw_label:
        # Make common labels friendlier.
        low = raw_label.lower()
        if low in {"over", "o"}:
            return f"Más de {hdp}" if hdp is not None else "Más de"
        if low in {"under", "u"}:
            return f"Menos de {hdp}" if hdp is not None else "Menos de"
        if low == "draw":
            return "Empate"
        return raw_label

    c = canonical_market_name(market_name)
    if c == "ml":
        if s == "home":
            return home or "Local"
        if s == "away":
            return away or "Visitante"
        if s == "draw":
            return "Empate"

    if c == "totals":
        if s in {"home", "over"}:
            return f"Más de {hdp}" if hdp is not None else "Más de"
        if s in {"away", "under"}:
            return f"Menos de {hdp}" if hdp is not None else "Menos de"

    if s == "home":
        return home or "Local"
    if s == "away":
        return away or "Visitante"
    if s == "draw":
        return "Empate"
    if s == "over":
        return f"Más de {hdp}" if hdp is not None else "Más de"
    if s == "under":
        return f"Menos de {hdp}" if hdp is not None else "Menos de"
    return side or ""

def market_matches(market, target_name, target_hdp):
    if canonical_market_name(market.get("name")) != canonical_market_name(target_name):
        return False

    # Match the exact line whenever a line exists.
    mh = market.get("hdp")
    if target_hdp is None or mh is None:
        return target_hdp is None or mh is None or str(mh) == str(target_hdp)
    try:
        return abs(float(mh) - float(target_hdp)) < 1e-9
    except:
        return str(mh) == str(target_hdp)

def extract_book_offer(event_odds, bookmaker, market_name, side, target_hdp=None, target_market=None):
    bookmakers = (event_odds or {}).get("bookmakers") or {}
    markets = bookmakers.get(bookmaker) or []
    side_key = (side or "").lower()
    target_market = target_market or {}

    # The value endpoint can call the two sides "home/away" even when the
    # displayed labels are Over/Under. We therefore match by BOTH side key
    # and the API's market label.
    target_label = side_label_from_market(target_market, side_key).strip().lower()

    for market in markets:
        if not market_matches(market, market_name, target_hdp):
            continue

        market_href = market.get("href") or market.get("directLink") or ""
        for row in market.get("odds") or []:
            row_hdp = row.get("hdp")
            if target_hdp is not None and row_hdp is not None:
                try:
                    if abs(float(row_hdp) - float(target_hdp)) > 1e-9:
                        continue
                except:
                    if str(row_hdp) != str(target_hdp):
                        continue

            # First attempt: standard side key.
            val = row.get(side_key)

            # Second attempt: infer side from market label, useful for totals.
            if val is None and target_label:
                for candidate in ("home", "away", "draw", "over", "under"):
                    label = str(market.get(candidate, "")).strip().lower()
                    if label and label == target_label:
                        val = row.get(candidate)
                        if val is not None:
                            side_key_for_link = candidate
                            break
                else:
                    side_key_for_link = side_key
            else:
                side_key_for_link = side_key

            f = to_float(val)
            if f is not None:
                link = (
                    row.get(f"{side_key_for_link}DirectLink")
                    or row.get("directLink")
                    or row.get("href")
                    or market_href
                    or ""
                )
                return {"odds": f, "link": link}

    return {"odds": None, "link": ""}

def batch_event_odds(event_ids):
    result = {}
    ids = [str(x) for x in event_ids if x is not None]
    for i in range(0, len(ids), 10):
        chunk = ids[i:i+10]
        try:
            data = odds_get("/odds/multi", {
                "eventIds": ",".join(chunk),
                "bookmakers": ",".join(BOOKMAKERS)
            })
            if isinstance(data, list):
                for event in data:
                    result[str(event.get("id"))] = event
        except Exception:
            pass
    return result

def raw_value(item):
    event = item.get("event") or {}
    market = item.get("market") or {}
    bo = item.get("bookmakerOdds") or {}
    side = (item.get("betSide") or "").lower()
    odd = to_float(bo.get(side))
    if odd is None:
        odd = to_float(
            bo.get("home") if side == "home"
            else bo.get("away") if side == "away"
            else bo.get("draw") if side == "draw"
            else None
        )
    sport = normalize_sport(event.get("sport"))
    return {
        "event_id": item.get("eventId"),
        "sport": sport,
        "league": event.get("league", ""),
        "home": event.get("home", ""),
        "away": event.get("away", ""),
        "bookmaker": item.get("bookmaker", ""),
        "selection": item.get("betSide", ""),
        "market": market.get("name", "Mercado"),
        "market_obj": market,
        "hdp": market.get("hdp"),
        "value_odds": odd,
        "provider_advantage": ev_to_advantage(item.get("expectedValue", 0)),
        "updated_at": item.get("expectedValueUpdatedAt", ""),
        "value_link": (
            bo.get(f"{side}DirectLink")
            or bo.get("directLink")
            or bo.get("href")
            or ""
        ),
    }

def enrich_value(v, event_odds):
    offers = {}
    for b in BOOKMAKERS:
        offer = extract_book_offer(
            event_odds,
            b,
            v["market"],
            v["selection"],
            v["hdp"],
            v.get("market_obj") or {}
        )
        if offer["odds"] is not None:
            offers[b] = offer

    # fall back to value endpoint's quoted price/direct link
    if v["bookmaker"] and v["value_odds"] is not None:
        offers.setdefault(v["bookmaker"], {
            "odds": v["value_odds"],
            "link": v.get("value_link", "")
        })
        if not offers[v["bookmaker"]].get("link") and v.get("value_link"):
            offers[v["bookmaker"]]["link"] = v["value_link"]

    # This screen is a comparison product: do not show a "better price"
    # unless BOTH selected bookmakers have the exact same market/line/side.
    if any(b not in offers or offers[b].get("odds") is None for b in BOOKMAKERS):
        return None

    best_book = max(offers, key=lambda b: offers[b]["odds"])
    best_odds = offers[best_book]["odds"]

    other_candidates = [o["odds"] for b,o in offers.items() if b != best_book]
    other_odds = max(other_candidates) if other_candidates else None

    gap = 0.0
    if other_odds and other_odds > 0:
        gap = round((best_odds / other_odds - 1) * 100, 2)

    price_rows = []
    for b in BOOKMAKERS:
        offer = offers.get(b, {})
        price_rows.append({
            "bookmaker": b,
            "odds": offer.get("odds"),
            "link": offer.get("link", ""),
            "best": b == best_book
        })

    market_label = human_market(v["market"], v["sport"], v["hdp"])
    selection_label = human_selection(
        v["selection"], v["home"], v["away"], v["market"], v["hdp"], v.get("market_obj") or {}
    )

    msg = (
        f"{best_book} ofrece {best_odds:.2f}"
        + (f" frente a {other_odds:.2f} en la otra casa." if other_odds else ".")
    )

    return {
        "type": "better_price",
        "sport": v["sport"],
        "league": v["league"],
        "home": v["home"],
        "away": v["away"],
        "market": v["market"],
        "market_label": market_label,
        "selection": v["selection"],
        "selection_label": selection_label,
        "prices": price_rows,
        "price_gap": gap,
        "provider_advantage": v["provider_advantage"],
        "updated_at": v.get("updated_at", ""),
        "message": msg
    }

def nice_arb(item):
    event = item.get("event") or {}
    sport = normalize_sport(event.get("sport"))
    legs = []
    for leg in item.get("legs") or []:
        side = leg.get("label") or leg.get("side") or ""
        legs.append({
            "bookmaker": leg.get("bookmaker", ""),
            "selection": human_selection(side, event.get("home",""), event.get("away","")),
            "odds": leg.get("odds"),
            "stake": None,
            "link": leg.get("directLink") or leg.get("href") or ""
        })
    try: profit = float(item.get("profitMargin", 0))
    except: profit = 0.0
    market = (item.get("market") or {}).get("label") or (item.get("market") or {}).get("name") or "Mercado"
    return {
        "type": "covered",
        "sport": sport,
        "league": event.get("league", ""),
        "home": event.get("home", ""),
        "away": event.get("away", ""),
        "market": market,
        "market_label": human_market(market, sport),
        "profit": round(profit, 2),
        "legs": legs,
        "updated_at": item.get("updatedAt", ""),
        "message": "Si puedes colocar todas las apuestas a estas cuotas, el resultado queda cubierto."
    }

@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")

@app.route("/api/status")
def status():
    return jsonify({
        "ok": bool(api_key()),
        "bookmakers": BOOKMAKERS,
        "message": "Conectado" if api_key() else "Falta configurar la API Key en Render"
    })

@app.route("/api/opportunities")
def opportunities():
    sport = normalize_sport(request.args.get("sport", "all"))
    mode = request.args.get("mode", "all")
    out, errors = [], []

    requested_sports = list(ALLOWED_SPORTS) if sport == "all" else [sport]
    requested_sports = [s for s in requested_sports if s in ALLOWED_SPORTS]

    if mode in ("all", "better"):
        raw = []
        for bookmaker in BOOKMAKERS:
            for sport_slug in requested_sports:
                try:
                    data = odds_get("/value-bets", {
                        "bookmaker": bookmaker,
                        "includeEventDetails": "true",
                        "sport": sport_slug
                    })
                    if isinstance(data, list):
                        for item in data:
                            v = raw_value(item)
                            if v["sport"] in ALLOWED_SPORTS:
                                raw.append(v)
                except Exception as e:
                    errors.append(f"{bookmaker}/{sport_slug}: {e}")

        # dedupe same event/market/line/selection, keeping strongest provider signal
        dedup = {}
        for v in raw:
            key = (v["event_id"], v["market"], str(v["hdp"]), v["selection"])
            if key not in dedup or v["provider_advantage"] > dedup[key]["provider_advantage"]:
                dedup[key] = v

        candidates = sorted(
            dedup.values(),
            key=lambda x: x["provider_advantage"],
            reverse=True
        )[:30]

        odds_map = batch_event_odds([x["event_id"] for x in candidates])

        for v in candidates:
            enriched = enrich_value(v, odds_map.get(str(v["event_id"]), {}))
            if enriched:
                out.append(enriched)

    if mode in ("all", "covered"):
        try:
            data = odds_get("/arbitrage-bets", {
                "bookmakers": ",".join(BOOKMAKERS),
                "includeEventDetails": "true",
                "limit": 100
            })
            if isinstance(data, list):
                for item in data:
                    x = nice_arb(item)
                    if x["sport"] not in ALLOWED_SPORTS:
                        continue
                    if sport != "all" and x["sport"] != sport:
                        continue
                    out.append(x)
        except Exception as e:
            errors.append(f"Arbitraje: {e}")

    out.sort(
        key=lambda x: x.get("profit", x.get("price_gap", 0)) or 0,
        reverse=True
    )

    return jsonify({"items": out[:60], "errors": errors})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
