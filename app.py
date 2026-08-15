
import os
import time
import requests
import re
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

CACHE_TTL = 300
_RESPONSE_CACHE = {"ts": 0, "items": [], "data_status": "ok", "data_message": ""}

API_BASE = "https://api.odds-api.io/v3"
BOOKMAKERS = ["Bet365", "William Hill"]
ALLOWED_SPORTS = {"football", "tennis", "basketball"}
MAX_CONFIRMED_PRICE_GAP = 25.0  # gaps larger than this are blocked, never shown as confirmed
MAX_VERIFIED_ARB_PROFIT = 15.0   # unusually large surebets are rejected as probable mapping/feed errors

HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#17633f">
<title>Radar Privado</title>
<style>
:root{--bg:#f3f0e9;--panel:#fffefa;--line:#d7ddd8;--txt:#17211b;--muted:#6d786f;--green:#17633f;--green2:#286f49;--mint:#79e8bf;--amber:#9a5c00;--blue:#2f6ca5;--danger:#9f2f2f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.shell{max-width:720px;margin:auto;padding:0 0 40px}
header{display:flex;justify-content:space-between;gap:14px;background:linear-gradient(145deg,var(--green2),var(--green));padding:calc(env(safe-area-inset-top) + 20px) 20px 22px;border-radius:0 0 30px 30px;color:white}
header>div{min-width:0}.eyebrow{font-size:11px;font-weight:900;letter-spacing:.14em;color:#d1f0df}h1{font-size:30px;line-height:1.02;margin:8px 0 8px;letter-spacing:-.02em}header p{color:#d6e6dc;font-size:15px;line-height:1.3;margin:0}
.refresh{border:0;border-radius:16px;background:#fff;color:var(--green);font-weight:900;padding:11px 15px;height:44px;box-shadow:0 4px 14px rgba(0,0,0,.08)}
.status{margin:16px 16px 6px;padding:13px 15px;border:1px solid #b8d6c3;border-radius:15px;color:var(--green);background:#f8fffb;font-size:14px;font-weight:850}.status.ok{color:#17633f}.cache{margin:0 20px 8px;color:#56635a;font-size:12px;font-weight:700}
.row,.mode-row{display:flex;gap:8px;overflow:auto;padding:5px 16px;scrollbar-width:none}.row::-webkit-scrollbar,.mode-row::-webkit-scrollbar{display:none}.mode-row{flex-wrap:wrap;overflow:visible}
.chip{white-space:nowrap;border:1px solid var(--line);background:#fff;color:#3b4940;border-radius:999px;padding:10px 14px;font-weight:850;font-size:14px}.chip.active{background:var(--green);color:white;border-color:var(--green)}
#cards{display:grid;gap:14px;margin:15px 16px 0}.card{background:var(--panel);border:1px solid var(--line);border-radius:24px;padding:18px;box-shadow:0 7px 24px rgba(31,55,42,.07)}
.top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.badge{font-size:11px;font-weight:950;padding:8px 10px;border-radius:999px;letter-spacing:.01em}.better{background:#0e4f36;color:#82edc7}.covered{background:#0e5639;color:#8ff0ca}.review{background:#5a3909;color:#ffd895}.single{background:#eef1ee;color:#506056}.asian{background:#e8f5ee;color:#17633f;border:1px solid #bedaca}
.metric{font-size:24px;font-weight:950;line-height:1;text-align:right}.metric small{display:block;color:var(--muted);font-size:10px;line-height:1.2;margin-top:5px}.event{font-size:20px;font-weight:950;margin:15px 0 5px;line-height:1.16}.meta{font-size:12px;color:var(--muted);line-height:1.35}
.market{margin:15px 0;background:#f3f6f3;border-radius:17px;padding:13px}.market-title{font-weight:950;margin-bottom:5px}.selection{color:#526158;font-weight:750}.compare{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:12px}
.book{display:block;background:white;border:1px solid var(--line);border-radius:16px;padding:13px;color:inherit;text-decoration:none;min-width:0}.book.best{border:2px solid #2d8c68;background:#f1fbf6}.book.disabled{opacity:.58}.book-name{font-size:12px;color:var(--muted);font-weight:850}.book-price{font-size:29px;font-weight:950;margin-top:6px}.best-label{font-size:10px;font-weight:950;color:#28a574;margin-top:5px}.open-label{font-size:10px;font-weight:950;color:#4e8fd0;margin-top:5px}
.msg{font-size:14px;line-height:1.5;color:#465249}.fresh{font-size:11px;color:#8b968e;margin-top:10px}.leg{background:white;border:1px solid var(--line);border-radius:15px;padding:12px;display:flex;justify-content:space-between;gap:10px;margin-top:9px;color:inherit;text-decoration:none}.leg.best{border-color:#9acbb2}.stake{font-size:12px;color:#56635a;margin-top:3px}.profitbox{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:11px}.stat{background:#edf6f0;border-radius:13px;padding:10px}.stat b{display:block;font-size:16px}.stat span{font-size:10px;color:var(--muted);font-weight:800}.tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.tag{font-size:10px;font-weight:900;border-radius:999px;padding:6px 8px;background:#edf3ef;color:#42604e}.tag.split{background:#fff3d9;color:#7b4e00}.empty{text-align:center;color:var(--muted);padding:48px 18px;line-height:1.45}footer{font-size:11px;color:#7e8881;line-height:1.5;padding:27px 20px}
@media(max-width:390px){h1{font-size:27px}.refresh{padding:10px 12px}.card{padding:15px}.compare{gap:7px}.book-price{font-size:26px}}
</style>
</head>
<body>
<div class="shell">
<header><div><div class="eyebrow">RADAR PRIVADO · V1.1</div><h1>Encuentra tu oportunidad real.</h1><p>Comparamos las casas por ti. Tú eliges.</p></div><button class="refresh" id="refresh">Actualizar</button></header>
<div id="status" class="status">Comprobando conexión…</div><div id="cacheInfo" class="cache">Datos guardados temporalmente para ahorrar consultas.</div>
<div class="row"><button class="chip active" data-sport="all">Todo</button><button class="chip" data-sport="football">⚽ Fútbol</button><button class="chip" data-sport="tennis">🎾 Tenis</button><button class="chip" data-sport="basketball">🏀 Basket</button></div>
<div class="mode-row"><button class="chip mode active" data-mode="all">Oportunidades</button><button class="chip mode" data-mode="better">Valor real entre casas</button><button class="chip mode" data-mode="covered">Ganancia segura</button></div>
<main id="cards"><div class="empty">Cargando oportunidades…</div></main>
<footer><b>V1.1 privada.</b> El Radar bloquea comparaciones sospechosas y exige coincidencia de mercado y línea. En Ganancia segura solo muestra arbitrajes que pasan la verificación matemática. Confirma siempre evento, mercado y cuota antes de apostar.</footer>
</div>
<script>
let sport="all",mode="all";
const cards=document.getElementById("cards"),statusEl=document.getElementById("status"),cacheInfo=document.getElementById("cacheInfo");
const esc=x=>String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
const n=x=>Number.isFinite(Number(x))?Number(x).toFixed(2):(x??"—");
const ev=x=>[x.home,x.away].filter(Boolean).join(" – ")||"Evento";
function better(x){
 const compared=!!x.compared;
 const books=(x.prices||[]).map(b=>{const inner=`<div class="book-name">${esc(b.bookmaker)}</div><div class="book-price">@ ${esc(b.odds??"—")}</div>${b.best?'<div class="best-label">MEJOR CUOTA</div>':''}${b.link?'<div class="open-label">ABRIR EN LA CASA ↗</div>':''}`;return b.link?`<a class="book ${b.best?"best":""}" href="${esc(b.link)}" target="_blank" rel="noopener noreferrer">${inner}</a>`:`<div class="book ${b.odds==null?"disabled":""} ${b.best?"best":""}">${inner}</div>`}).join("");
 return `<article class="card"><div class="top"><span class="badge ${compared?"better":"single"}">${compared?"🟢 PAGAN MEJOR AQUÍ":"⚪ OPORTUNIDAD DETECTADA"}</span><div class="metric">${compared?`+${n(x.price_gap)}%`:`+${n(x.provider_advantage)}%`}<small>${compared?"paga más":"señal del feed"}</small></div></div><div class="event">${esc(ev(x))}</div><div class="meta">${esc(x.league||x.sport||"")}</div><div class="market"><div class="market-title">${esc(x.market_label||x.market||"Mercado")}</div><div class="selection">${esc(x.selection_label||x.selection||"")}</div><div class="compare">${books}</div></div><div class="msg">${esc(x.message)}</div><div class="fresh">${esc(x.freshness||"Actualizado recientemente")}</div></article>`;
}
function covered(x){
 const legs=(x.legs||[]).map(l=>{const inner=`<div><b>${esc(l.bookmaker)}</b><div class="stake">${esc(l.selection)}</div></div><div style="text-align:right"><b>@ ${esc(l.odds||"—")}</b>${l.stake!=null?`<div class="stake">${n(l.stake)} € / 100 €</div>`:""}${l.link?'<div class="open-label">ABRIR EN LA CASA ↗</div>':''}</div>`;return l.link?`<a class="leg" href="${esc(l.link)}" target="_blank" rel="noopener noreferrer">${inner}</a>`:`<div class="leg">${inner}</div>`}).join("");
 const tags=[x.asian?'<span class="tag">HÁNDICAP/TOTAL ASIÁTICO</span>':'',x.split?'<span class="tag split">ASIAN SPLIT · 0.25/0.75</span>':''].join("");
 return `<article class="card"><div class="top"><span class="badge covered">🔒 SUREBET VERIFICADA</span><div class="metric">+${n(x.profit)}%<small>beneficio mínimo</small></div></div><div class="event">${esc(ev(x))}</div><div class="meta">${esc(x.league||x.sport||"")}</div><div class="tags">${tags}</div><div class="market"><div class="market-title">${esc(x.market_label||x.market||"Mercado")}</div>${legs}<div class="profitbox"><div class="stat"><b>100 €</b><span>CAPITAL REPARTIDO</span></div><div class="stat"><b>+${n(x.profit_eur??x.profit)} €</b><span>GANANCIA MÍNIMA</span></div></div></div><div class="msg">${esc(x.message)}</div><div class="fresh">Verificación matemática del peor escenario</div></article>`;
}
async function load(){cards.innerHTML='<div class="empty">Buscando oportunidades…</div>';try{let r=await fetch('/api/opportunities?sport=all&mode=all',{cache:"no-store"});let d=await r.json();if(d.data_status==="rate_limited"){cacheInfo.textContent="🟠 Datos temporalmente limitados";cards.innerHTML='<div class="empty"><b>La fuente de cuotas ha alcanzado su límite temporal.</b><br><br>Reintentaremos cuando vuelva a estar disponible.</div>';return}if(d.data_status==="error"){cacheInfo.textContent="🔴 Fuente de datos no disponible";cards.innerHTML=`<div class="empty"><b>No hemos podido leer las cuotas ahora mismo.</b><br><br>${esc(d.data_message||"Prueba de nuevo en unos minutos.")}</div>`;return}let items=d.items||[];if(sport!=="all")items=items.filter(x=>(x.sport||"").toLowerCase()===sport);if(mode==="better")items=items.filter(x=>x.type!=="covered");if(mode==="covered")items=items.filter(x=>x.type==="covered");cacheInfo.textContent=d.from_cache?"✓ Usando datos guardados para ahorrar consultas":"✓ Datos renovados ahora";cards.innerHTML=items.length?items.map(x=>x.type==="covered"?covered(x):better(x)).join(""):(mode==="covered"?'<div class="empty"><b>No hay una surebet verificada ahora mismo.</b><br><br>Estamos priorizando hándicap asiático, totales asiáticos y mercados completos. No mostramos una oportunidad si no supera la comprobación del peor escenario.</div>':'<div class="empty">Ahora mismo no hay oportunidades con estos filtros.<br><br>Seguiremos comprobando las cuotas.</div>')}catch(e){cacheInfo.textContent="🔴 Sin conexión con la fuente de datos";cards.innerHTML=`<div class="empty">No se ha podido consultar el Radar.<br>${esc(e.message)}</div>`}}
async function st(){try{const r=await fetch('/api/status'),s=await r.json();statusEl.textContent=s.ok?`● Conectado · ${s.bookmakers.join(" + ")}`:`● ${s.message}`;if(s.ok)statusEl.classList.add("ok")}catch(e){statusEl.textContent="● Sin conexión"}}
document.querySelectorAll('[data-sport]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-sport]').forEach(x=>x.classList.remove('active'));b.classList.add('active');sport=b.dataset.sport;load()});document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-mode]').forEach(x=>x.classList.remove('active'));b.classList.add('active');mode=b.dataset.mode;load()});document.getElementById('refresh').onclick=load;st();load();
</script></body></html>"""

def api_key():
    return os.getenv("ODDS_API_KEY","").strip()

class APIError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code=status_code
        self.message=message

def api_get(path, params=None):
    if not api_key():
        raise APIError(401, "Falta ODDS_API_KEY")
    p=dict(params or {})
    p["apiKey"]=api_key()
    r=requests.get(f"{API_BASE}{path}",params=p,timeout=20)
    if r.status_code == 429:
        raise APIError(429, "Límite temporal de consultas alcanzado")
    if not r.ok:
        raise APIError(r.status_code, f"Error de datos ({r.status_code})")
    return r.json()

def fnum(x):
    try:
        v=float(x)
        return v if v>1.0 else None
    except:
        return None

def sport_slug(x):
    if isinstance(x,dict):
        return (x.get("slug") or x.get("name") or "").strip().lower()
    return (x or "").strip().lower()

def league_name(x):
    if isinstance(x,dict):
        return x.get("name") or x.get("slug") or ""
    return x or ""

def compact(s):
    return " ".join(str(s or "").strip().lower().replace("_"," ").replace("-"," ").split())

PROTECTED_AGE_RE = re.compile(r"\b(?:u|under|sub)\s*[- ]?\s*(1[5-9]|2[0-3])\b", re.I)

def protected_profile(*texts):
    text=" ".join(str(x or "") for x in texts).lower().replace("_"," ")
    tags=set()
    for age in PROTECTED_AGE_RE.findall(text):
        tags.add(f"u{age}")
    if re.search(r"\b(women|woman|women's|womens|female|femenin[oa]s?|fem\.?|ladies)\b", text): tags.add("women")
    if re.search(r"\b(reserve|reserves|reserva|reservas|b team|team b|filial)\b", text): tags.add("reserve")
    if re.search(r"\b(youth|juvenil|juveniles|academy|academia)\b", text): tags.add("youth")
    return tags

def event_profile(home,away,league):
    return protected_profile(home,away,league)

def profiles_compatible(a,b):
    # Age/gender/reserve/youth markers are protected. If one side has one and the other does not, reject.
    return set(a)==set(b)

def meaningful_label(s):
    x=compact(s)
    return x not in {"", "home", "away", "draw", "1", "2", "x", "over", "under", "more", "less", "mas", "más", "menos"}

def participant_compatible(a,b):
    if not meaningful_label(a) or not meaningful_label(b):
        return True
    if not profiles_compatible(protected_profile(a),protected_profile(b)):
        return False
    # Soft lexical check after removing generic club words.
    junk={"fc","cf","sc","afc","club","city","the"}
    ta={t for t in compact(a).split() if t not in junk and not re.fullmatch(r"u\d{2}",t)}
    tb={t for t in compact(b).split() if t not in junk and not re.fullmatch(r"u\d{2}",t)}
    return not ta or not tb or len(ta & tb)>=max(1,min(len(ta),len(tb))//2)

def canonical_market(name):
    n=compact(name)
    if n in {"ml","moneyline","match winner","winner"}: return "ml"
    if "total" in n or "over under" in n: return "totals"
    if "spread" in n or "handicap" in n: return "spread"
    if "both teams" in n or "btts" in n: return "btts"
    if "draw no bet" in n or "dnb" in n: return "dnb"
    return n

def line_value(market,row=None):
    row=row or {}
    for source in (row,market):
        for key in ("hdp","line","handicap","total"):
            if source.get(key) not in (None,""):
                try:return float(source.get(key))
                except:return source.get(key)
    return None

def label_for_side(market,side):
    v=market.get(side)
    return str(v).strip() if v not in (None,"") else ""

def human_market(name,sport):
    c=canonical_market(name)
    if c=="ml": return "Ganador del partido"
    if c=="spread": return "Hándicap asiático" if "asian" in compact(name) else "Hándicap"
    if c=="totals":
        base="Total de juegos" if sport=="tennis" else ("Total de puntos" if sport=="basketball" else "Total de goles")
        return f"{base} · Asiático" if "asian" in compact(name) else base
    if c=="btts": return "Marcan ambos"
    if c=="dnb": return "Empate no cuenta"
    return name or "Mercado"

def canonical_side(market_name,market,side):
    s=compact(side)
    c=canonical_market(market_name)
    lab=compact(label_for_side(market,side))
    if c=="totals":
        if "over" in lab or "más" in lab or "mas" in lab: return "over"
        if "under" in lab or "menos" in lab: return "under"
        if s=="home": return "over"
        if s=="away": return "under"
    return s

def human_selection(market_name,market,side,line,home,away):
    cs=canonical_side(market_name,market,side)
    c=canonical_market(market_name)
    raw=label_for_side(market,side)

    if c=="totals":
        if cs=="over": return f"Más de {line}" if line is not None else "Más de"
        if cs=="under": return f"Menos de {line}" if line is not None else "Menos de"

    if c=="spread":
        who=home if cs=="home" else away if cs=="away" else (raw or side)
        if line is not None:
            try:
                sign="+" if float(line)>0 else ""
                return f"{who} {sign}{line:g}"
            except:
                return f"{who} {line}"
        return who

    if c=="ml":
        if cs=="home": return home
        if cs=="away": return away
        if cs=="draw": return "Empate"

    return raw or (home if cs=="home" else away if cs=="away" else "Empate" if cs=="draw" else side)

def ev_adv(raw):
    try:
        v=float(raw)
        return round(v-100,2) if v>=100 else round(v,2)
    except:
        return 0.0

def value_direct_link(bo,side):
    return (
        bo.get(f"{side}DirectLink")
        or bo.get("directLink")
        or bo.get("href")
        or ""
    )

def parse_value(item):
    event=item.get("event") or {}
    market=item.get("market") or {}
    bo=item.get("bookmakerOdds") or {}
    side=(item.get("betSide") or "").lower()
    odd=fnum(bo.get(side))
    if odd is None:
        odd=fnum(
            bo.get("home") if side=="home"
            else bo.get("away") if side=="away"
            else bo.get("draw") if side=="draw"
            else None
        )

    sport=sport_slug(event.get("sport"))
    line=line_value(market)
    return {
        "event_id":item.get("eventId"),
        "sport":sport,
        "league":league_name(event.get("league")),
        "home":event.get("home",""),
        "away":event.get("away",""),
        "market":market.get("name","Mercado"),
        "market_obj":market,
        "line":line,
        "side":side,
        "bookmaker":item.get("bookmaker",""),
        "odds":odd,
        "link":value_direct_link(bo,side),
        "provider_advantage":ev_adv(item.get("expectedValue",0)),
        "updated_at":item.get("expectedValueUpdatedAt",""),
        "starts_at": event.get("startsAt") or event.get("startTime") or event.get("commenceTime") or event.get("date") or "",
        "event_profile": sorted(event_profile(event.get("home",""),event.get("away",""),league_name(event.get("league"))))
    }

def get_event_odds(event_id):
    # Try the most direct endpoint first; fall back to /odds/multi.
    for path,params in (
        ("/odds",{"eventId":event_id,"bookmakers":",".join(BOOKMAKERS)}),
        ("/odds/multi",{"eventIds":str(event_id),"bookmakers":",".join(BOOKMAKERS)})
    ):
        try:
            data=api_get(path,params)
            if isinstance(data,list):
                return data[0] if data else {}
            if isinstance(data,dict):
                # Some APIs wrap the actual event.
                if "bookmakers" in data: return data
                if isinstance(data.get("data"),dict): return data["data"]
        except:
            pass
    return {}

def market_equiv(a,b):
    return canonical_market(a)==canonical_market(b)

def line_equiv(a,b,market_name=""):
    cm=canonical_market(market_name)
    if a is None and b is None:
        return cm not in {"spread","totals"}
    if a is None or b is None:
        return False
    try:return abs(float(a)-float(b))<1e-9
    except:return str(a)==str(b)

def extract_other_quote(event_data, target_book, target):
    event_data=event_data or {}
    # Never trust an odds payload solely because the provider reused an event id.
    eh=event_data.get("home","")
    ea=event_data.get("away","")
    el=league_name(event_data.get("league"))
    if eh or ea or el:
        p1=set(target.get("event_profile") or [])
        p2=event_profile(eh,ea,el)
        if not profiles_compatible(p1,p2):
            return None

    books=event_data.get("bookmakers") or {}
    markets=books.get(target_book) or []
    target_market=target["market"]
    target_line=target["line"]
    target_side=canonical_side(target_market,target["market_obj"],target["side"])
    target_label=label_for_side(target["market_obj"],target["side"])

    for market in markets:
        mname=market.get("name") or ""
        if not market_equiv(mname,target_market):
            continue
        rows=market.get("odds") or []
        for row in rows:
            row_line=line_value(market,row)
            if not line_equiv(row_line,target_line,target_market):
                continue

            candidates=[]
            for side in ("home","away","draw","over","under"):
                val=fnum(row.get(side))
                if val is None: continue
                cs=canonical_side(mname,market,side)
                raw_label=label_for_side(market,side)
                if cs!=target_side:
                    continue
                if not participant_compatible(target_label,raw_label):
                    continue
                score=2
                if meaningful_label(target_label) and meaningful_label(raw_label) and compact(target_label)==compact(raw_label): score+=4
                candidates.append((score,side,val,raw_label))

            if not candidates:
                continue
            candidates.sort(reverse=True,key=lambda x:x[0])
            _,side,val,raw_label=candidates[0]
            link=(row.get(f"{side}DirectLink") or row.get("directLink") or row.get("href") or market.get("href") or market.get("directLink") or "")
            return {"odds":val,"link":link,"label":raw_label,"line":row_line}
    return None

def make_card(v):
    other_book=BOOKMAKERS[1] if v["bookmaker"]==BOOKMAKERS[0] else BOOKMAKERS[0]
    other=None
    if v["event_id"] is not None:
        event_data=get_event_odds(v["event_id"])
        other=extract_other_quote(event_data,other_book,v)

    prices=[]
    quoted={v["bookmaker"]:{"odds":v["odds"],"link":v["link"]},other_book:other or {"odds":None,"link":""}}
    compared=other is not None and other.get("odds") is not None and v["odds"] is not None

    if compared:
        best_book=max(quoted,key=lambda b:quoted[b]["odds"])
        worst_book=min(quoted,key=lambda b:quoted[b]["odds"])
        best_odds=quoted[best_book]["odds"]
        worst_odds=quoted[worst_book]["odds"]
        gap=round((best_odds/worst_odds-1)*100,2)
        # A huge same-selection discrepancy is more likely to be a mapping/market error than actionable value.
        # Do not downgrade it to an orange warning: remove it from actionable results entirely.
        if gap>=MAX_CONFIRMED_PRICE_GAP:
            return None
        message=f"{best_book} ofrece {best_odds:.2f} frente a {worst_odds:.2f} en {worst_book}."
    else:
        best_book=v["bookmaker"]
        gap=0.0
        message=f"{v['bookmaker']} ofrece {v['odds']:.2f}. La otra casa no devuelve ahora mismo este mercado exacto en el feed."

    for b in BOOKMAKERS:
        q=quoted.get(b) or {}
        prices.append({"bookmaker":b,"odds":q.get("odds"),"link":q.get("link",""),"best":b==best_book})

    return {
        "type":"better_price","sport":v["sport"],"league":v["league"],"home":v["home"],"away":v["away"],
        "market_label":human_market(v["market"],v["sport"]),
        "selection_label":human_selection(v["market"],v["market_obj"],v["side"],v["line"],v["home"],v["away"]),
        "prices":prices,"compared":compared,"price_gap":gap,"provider_advantage":v["provider_advantage"],
        "message":message,"freshness":"Comparación confirmada" if compared else "Pendiente de segunda cuota"
    }

def get_value_cards(sports):
    raw=[]
    rate_limited=False
    success_calls=0

    for bookmaker in BOOKMAKERS:
        for sport in sports:
            try:
                data=api_get("/value-bets",{
                    "bookmaker":bookmaker,
                    "sport":sport,
                    "includeEventDetails":"true"
                })
                success_calls+=1
                if isinstance(data,list):
                    for item in data:
                        v=parse_value(item)
                        if v["sport"] in ALLOWED_SPORTS and v["odds"] is not None:
                            raw.append(v)
            except APIError as e:
                if e.status_code==429:
                    rate_limited=True
                continue

    if success_calls==0 and rate_limited:
        raise APIError(429, "Límite temporal de consultas alcanzado")

    dedup={}
    for v in raw:
        key=(v["event_id"],canonical_market(v["market"]),str(v["line"]),canonical_side(v["market"],v["market_obj"],v["side"]))
        if key not in dedup or v["provider_advantage"]>dedup[key]["provider_advantage"]:
            dedup[key]=v

    candidates=sorted(dedup.values(),key=lambda x:x["provider_advantage"],reverse=True)[:35]
    cards=[c for c in (make_card(v) for v in candidates) if c is not None]
    cards.sort(key=lambda x:(1 if x["compared"] else 0,x["price_gap"] if x["compared"] else x["provider_advantage"]),reverse=True)
    return cards

def _line_from_label(label):
    text=str(label or "").replace(",", ".")
    # Prefer signed values. Fall back to a decimal/integer next to over/under text.
    m=re.search(r"(?<!\d)([+-]\d+(?:\.\d+)?)", text)
    if not m:
        m=re.search(r"\b(\d+(?:\.\d+)?)\b", text)
    if not m: return None
    try:return float(m.group(1))
    except:return None

def _leg_line(leg, market, cm):
    explicit=None
    for key in ("hdp","line","handicap","total"):
        if leg.get(key) not in (None,""):
            try: explicit=float(leg.get(key)); break
            except: pass
    if explicit is None:
        explicit=_line_from_label(leg.get("label"))
    if explicit is not None:
        return explicit
    common=line_value(market)
    try: common=float(common)
    except: return None
    side=compact(leg.get("side"))
    if cm=="spread" and side=="away":
        return -common
    return common

def _split_lines(line):
    line=float(line)
    frac=abs(line)%1
    if abs(frac-.25)<1e-9 or abs(frac-.75)<1e-9:
        return (line-.25,line+.25)
    return (line,)

def _settle(adjusted, odds):
    if adjusted>1e-9: return float(odds)
    if adjusted<-1e-9: return 0.0
    return 1.0

def _asian_factor(cm, side, line, state, odds):
    vals=[]
    for ln in _split_lines(line):
        if cm=="spread":
            margin=float(state)
            adjusted=(margin+ln) if side=="home" else (-margin+ln)
        else:
            total=float(state)
            adjusted=(total-ln) if side=="over" else (ln-total)
        vals.append(_settle(adjusted,odds))
    return sum(vals)/len(vals)

def _stake_weights(item, legs):
    supplied={}
    for x in item.get("optimalStakes") or []:
        try: val=float(x.get("stake"))
        except: continue
        if val<=0: continue
        supplied[(x.get("bookmaker"),compact(x.get("side")))]=val
    raw=[]
    for leg in legs:
        val=supplied.get((leg.get("bookmaker"),compact(leg.get("side"))))
        if val is None:
            try: val=1.0/float(leg.get("odds"))
            except: return None
        raw.append(val)
    total=sum(raw)
    if total<=0:return None
    return [x/total for x in raw]

def _verify_arbitrage(item, sport, market, legs):
    cm=canonical_market(market.get("name") or market.get("label") or "")
    if len(legs)<2:return None
    try:
        odds=[float(x.get("odds")) for x in legs]
    except:return None
    if any(o<=1 for o in odds):return None
    if len({x.get("bookmaker") for x in legs})<2:return None
    if any(x.get("bookmaker") not in BOOKMAKERS for x in legs):return None

    # Bookmaker leg labels must preserve protected event attributes (U20, women, reserves, etc.).
    ev=item.get("event") or {}
    for leg in legs:
        side=compact(leg.get("side"))
        label=leg.get("label") or ""
        if side=="home" and meaningful_label(label) and not participant_compatible(ev.get("home",""),label): return None
        if side=="away" and meaningful_label(label) and not participant_compatible(ev.get("away",""),label): return None

    weights=_stake_weights(item,legs)
    if not weights:return None

    # Asian handicaps/totals: enumerate the actual settlement, including pushes and quarter-line half wins/losses.
    if cm in {"spread","totals"}:
        infos=[]
        for leg,o,w in zip(legs,odds,weights):
            side=compact(leg.get("side"))
            if cm=="spread" and side not in {"home","away"}:return None
            if cm=="totals" and side not in {"over","under"}:return None
            ln=_leg_line(leg,market,cm)
            if ln is None:return None
            infos.append((side,float(ln),o,w))
        if cm=="spread":
            states=range(-30,31) if sport=="basketball" else range(-15,16)
        else:
            states=range(0,351) if sport=="basketball" else (range(0,101) if sport=="tennis" else range(0,21))
        returns=[]
        for state in states:
            ret=sum(w*_asian_factor(cm,side,ln,state,o) for side,ln,o,w in infos)
            returns.append(ret)
        minimum=min(returns) if returns else 0
        if minimum<=1.000001:return None
        profit=(minimum-1)*100
        if profit>MAX_VERIFIED_ARB_PROFIT:return None
        split=any(len(_split_lines(ln))==2 for _,ln,_,_ in infos)
        return {"profit":round(profit,2),"weights":weights,"asian":True,"split":split}

    # Standard exhaustive markets. Only call these 'safe' when all mutually-exclusive outcomes are present.
    sides={compact(x.get("side")) for x in legs}
    exhaustive=False
    if cm=="ml":
        exhaustive = sides.issuperset({"home","away","draw"}) if sport=="football" else sides.issuperset({"home","away"})
    elif cm=="btts":
        labels={compact(x.get("label") or x.get("side")) for x in legs}
        exhaustive=(len(legs)==2 and any("yes" in z or "sí" in z or "si"==z for z in labels) and any("no"==z or " no" in z for z in labels))
    if not exhaustive:return None
    inv=sum(1/o for o in odds)
    if inv>=1:return None
    # Recalculate canonical dutching rather than trusting provider stakes.
    weights=[(1/o)/inv for o in odds]
    profit=(1/inv-1)*100
    if profit>MAX_VERIFIED_ARB_PROFIT:return None
    return {"profit":round(profit,2),"weights":weights,"asian":False,"split":False}

def human_arb(item):
    event=item.get("event") or {}
    sport=sport_slug(event.get("sport"))
    market=item.get("market") or {}
    raw_legs=[x for x in (item.get("legs") or []) if x.get("bookmaker") in BOOKMAKERS]
    check=_verify_arbitrage(item,sport,market,raw_legs)
    if not check:
        return None

    # Normalize the displayed distribution to exactly 100 EUR.
    legs=[]
    for leg,w in zip(raw_legs,check["weights"]):
        label=leg.get("label") or leg.get("side") or ""
        cm=canonical_market(market.get("name") or market.get("label") or "")
        ln=_leg_line(leg,market,cm) if cm in {"spread","totals"} else None
        if ln is not None and str(ln) not in str(label):
            side=compact(leg.get("side"))
            if side in {"home","away","over","under"}:
                sign="+" if ln>0 and side in {"home","away"} else ""
                label=f"{label} {sign}{ln:g}".strip()
        legs.append({
            "bookmaker":leg.get("bookmaker",""),"selection":label,"odds":leg.get("odds"),
            "stake":round(w*100,2),"link":leg.get("directLink") or leg.get("href") or ""
        })

    profit=max(0.0,float(check["profit"]))
    mname=market.get("name") or market.get("label") or "Mercado"
    return {
        "type":"covered","sport":sport,"league":league_name(event.get("league")),
        "home":event.get("home",""),"away":event.get("away",""),"market_label":human_market(mname,sport),
        "profit":round(profit,2),"profit_eur":round(profit,2),"legs":legs,
        "asian":bool(check["asian"]),"split":bool(check["split"]),
        "message":"Reparto calculado sobre 100 €. El porcentaje mostrado es el beneficio mínimo del peor escenario de liquidación."
    }

@app.route("/")
def index():
    return Response(HTML,mimetype="text/html")

@app.route("/api/status")
def status():
    return jsonify({
        "ok":bool(api_key()),
        "bookmakers":BOOKMAKERS,
        "message":"Conectado" if api_key() else "Falta configurar la API Key en Render"
    })

@app.route("/api/opportunities")
def opportunities():
    now=time.time()

    if _RESPONSE_CACHE["ts"] and now-_RESPONSE_CACHE["ts"]<CACHE_TTL:
        return jsonify({
            "items":_RESPONSE_CACHE["items"],
            "from_cache":True,
            "data_status":_RESPONSE_CACHE["data_status"],
            "data_message":_RESPONSE_CACHE["data_message"]
        })

    try:
        sports=list(ALLOWED_SPORTS)
        out=[]
        out.extend(get_value_cards(sports))

        try:
            data=api_get("/arbitrage-bets",{
                "bookmakers":",".join(BOOKMAKERS),
                "limit":100,
                "includeEventDetails":"true"
            })
            if isinstance(data,list):
                for item in data:
                    x=human_arb(item)
                    if x and x["sport"] in sports:
                        out.append(x)
        except APIError as e:
            if e.status_code==429 and not out:
                raise

        out.sort(
            key=lambda x:(
                3 if x["type"]=="covered" and x.get("asian") else 2 if x["type"]=="covered" else 1 if x.get("compared") else 0,
                x.get("profit",x.get("price_gap",x.get("provider_advantage",0))) or 0
            ),
            reverse=True
        )
        items=out[:80]
        status="ok"
        message=""
    except APIError as e:
        items=[]
        status="rate_limited" if e.status_code==429 else "error"
        message=("La fuente de cuotas ha alcanzado su límite temporal. Reintentaremos automáticamente."
                 if e.status_code==429 else e.message)

    _RESPONSE_CACHE["ts"]=now
    _RESPONSE_CACHE["items"]=items
    _RESPONSE_CACHE["data_status"]=status
    _RESPONSE_CACHE["data_message"]=message

    return jsonify({
        "items":items,
        "from_cache":False,
        "data_status":status,
        "data_message":message
    })

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","8000")))
