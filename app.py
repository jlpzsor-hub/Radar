
import os
import time
import math
import requests
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

API_BASE = "https://api.odds-api.io/v3"
BOOKMAKERS = ["Bet365", "William Hill"]
ALLOWED_SPORTS = {"football", "tennis", "basketball"}
MIN_PRICE_GAP = 1.0
EVENT_LIMIT_PER_BOOK = 30
CACHE_TTL = 45

_cache = {}

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
h1{font-size:31px;line-height:1.03;margin:7px 0 8px}p{color:var(--muted);margin:0}
.refresh{border:0;border-radius:14px;background:#fff;color:#08111f;font-weight:900;padding:11px 13px;height:42px}
.status{margin:20px 0 12px;padding:11px 13px;border:1px solid var(--line);border-radius:14px;color:var(--muted);font-size:13px}.ok{color:#b7f7df}
.row{display:flex;gap:8px;overflow:auto;padding:5px 0}.chip{white-space:nowrap;border:1px solid var(--line);background:#121c2f;color:#cbd5e1;border-radius:999px;padding:10px 13px;font-weight:800}.chip.active{background:white;color:#0b1220}
#cards{display:grid;gap:12px;margin-top:12px}.card{background:linear-gradient(180deg,#182640,#121c2f);border:1px solid var(--line);border-radius:22px;padding:17px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:center}.badge{font-size:12px;font-weight:900;padding:7px 9px;border-radius:999px}.better{background:#123c32;color:#75efc1}.covered{background:#17355d;color:#a6cbff}.review{background:#4b3410;color:#ffd68a}
.metric{font-size:21px;font-weight:900}.metric small{display:block;color:var(--muted);font-size:10px;text-align:right}
.event{font-size:19px;font-weight:900;margin:13px 0 4px}.meta{font-size:12px;color:var(--muted)}
.market{margin:14px 0;background:rgba(255,255,255,.05);border-radius:15px;padding:12px}.market-title{font-weight:900;margin-bottom:4px}.selection{color:#dbe3ee}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:12px}
.book{display:block;background:rgba(255,255,255,.05);border:1px solid transparent;border-radius:15px;padding:12px;color:inherit;text-decoration:none}
.book.best{border-color:#2d8c68;background:rgba(45,140,104,.12)}.book.disabled{opacity:.72}
.book-name{font-size:12px;color:var(--muted);font-weight:800}.book-price{font-size:27px;font-weight:950;margin-top:5px}
.best-label{font-size:10px;font-weight:900;color:#75efc1;margin-top:4px}.open-label{font-size:10px;font-weight:900;color:#9cc7ff;margin-top:4px}
.msg{font-size:14px;line-height:1.45;color:#dbe3ee}.fresh{font-size:11px;color:#94a3b8;margin-top:10px}
.leg{background:rgba(255,255,255,.05);border-radius:14px;padding:11px;display:flex;justify-content:space-between;margin-top:8px}
.empty{text-align:center;color:var(--muted);padding:40px 15px}
footer{font-size:11px;color:#718096;line-height:1.5;padding:25px 4px}
</style>
</head>
<body>
<div class="shell">
<header>
<div>
<div class="eyebrow">RADAR PRIVADO · V0.6</div>
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

<footer><b>V0.6 privada.</b> Ahora comparamos directamente las cuotas de Bet365 y William Hill. Una diferencia de precio no garantiza por sí sola que la apuesta sea rentable. Verifica siempre mercado, línea y cuota antes de confirmar.</footer>
</div>

<script>
let sport="all",mode="all";
const cards=document.getElementById("cards"),statusEl=document.getElementById("status");
const esc=x=>String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
const n=x=>Number.isFinite(Number(x))?Number(x).toFixed(2):(x??"—");
const ev=x=>[x.home,x.away].filter(Boolean).join(" – ")||"Evento";

function better(x){
  const warn=Number(x.price_gap||0)>=25;
  const books=(x.prices||[]).map(b=>{
    const inner=`<div class="book-name">${esc(b.bookmaker)}</div>
      <div class="book-price">@ ${esc(b.odds??"—")}</div>
      ${b.best?'<div class="best-label">MEJOR CUOTA</div>':''}
      ${b.link?'<div class="open-label">ABRIR EN LA CASA ↗</div>':''}`;
    return b.link
      ? `<a class="book ${b.best?"best":""}" href="${esc(b.link)}" target="_blank" rel="noopener noreferrer">${inner}</a>`
      : `<div class="book disabled ${b.best?"best":""}">${inner}</div>`;
  }).join("");

  return `<article class="card">
    <div class="top">
      <span class="badge ${warn?"review":"better"}">${warn?"🟠 REVISAR DIFERENCIA":"🟢 PAGAN MEJOR AQUÍ"}</span>
      <div class="metric">+${n(x.price_gap)}%<small>paga más</small></div>
    </div>
    <div class="event">${esc(ev(x))}</div>
    <div class="meta">${esc(x.league||x.sport||"")}</div>
    <div class="market">
      <div class="market-title">${esc(x.market_label)}</div>
      <div class="selection">${esc(x.selection_label)}</div>
      <div class="compare">${books}</div>
    </div>
    <div class="msg">${esc(x.message)}</div>
    <div class="fresh">${esc(x.freshness||"Cuotas consultadas ahora")}</div>
  </article>`;
}

function covered(x){
  const legs=(x.legs||[]).map(l=>{
    const inner=`<div><b>${esc(l.bookmaker)}</b><br>${esc(l.selection)}</div>
      <div style="text-align:right"><b>@ ${esc(l.odds||"—")}</b>${l.stake!=null?`<br>${n(l.stake)} €`:""}${l.link?'<br><span class="open-label">ABRIR ↗</span>':''}</div>`;
    return l.link?`<a class="leg" style="color:inherit;text-decoration:none" href="${esc(l.link)}" target="_blank" rel="noopener noreferrer">${inner}</a>`:`<div class="leg">${inner}</div>`;
  }).join("");
  return `<article class="card">
    <div class="top"><span class="badge covered">🔵 RESULTADO CUBIERTO</span><div class="metric">+${n(x.profit)}%<small>beneficio aprox.</small></div></div>
    <div class="event">${esc(ev(x))}</div><div class="meta">${esc(x.league||x.sport||"")}</div>
    <div class="market"><div class="market-title">${esc(x.market_label||x.market||"Mercado")}</div>${legs}</div>
    <div class="msg">${esc(x.message)}</div>
  </article>`;
}

async function load(){
  cards.innerHTML='<div class="empty">Comparando Bet365 y William Hill…</div>';
  try{
    const r=await fetch(`/api/opportunities?sport=${encodeURIComponent(sport)}&mode=${encodeURIComponent(mode)}`,{cache:"no-store"});
    const d=await r.json();
    const items=d.items||[];
    console.log("Radar debug", d.debug, d.errors);
    cards.innerHTML=items.length?items.map(x=>x.type==="covered"?covered(x):better(x)).join("")
      :'<div class="empty">No encontramos comparaciones válidas ahora mismo.<br><br>La V0.6 consulta una lista única de eventos y después pide las cuotas de Bet365 y William Hill sobre los mismos partidos.</div>';
  }catch(e){
    cards.innerHTML=`<div class="empty">No se ha podido consultar el radar.<br>${esc(e.message)}</div>`;
  }
}
async function st(){
  try{
    const r=await fetch("/api/status"),s=await r.json();
    statusEl.textContent=s.ok?`● Conectado · ${s.bookmakers.join(" + ")}`:`● ${s.message}`;
    if(s.ok)statusEl.classList.add("ok");
  }catch(e){statusEl.textContent="● Sin conexión";}
}
document.querySelectorAll("[data-sport]").forEach(b=>b.onclick=()=>{document.querySelectorAll("[data-sport]").forEach(x=>x.classList.remove("active"));b.classList.add("active");sport=b.dataset.sport;load();});
document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>{document.querySelectorAll("[data-mode]").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode;load();});
document.getElementById("refresh").onclick=load;
st();load();
</script>
</body>
</html>
"""

def api_key():
    return os.getenv("ODDS_API_KEY","").strip()

def api_get(path, params=None):
    if not api_key():
        raise RuntimeError("Falta ODDS_API_KEY")
    p=dict(params or {})
    p["apiKey"]=api_key()
    r=requests.get(f"{API_BASE}{path}",params=p,timeout=20)
    r.raise_for_status()
    return r.json()

def sport_slug(x):
    if isinstance(x,dict):
        return (x.get("slug") or x.get("name") or "").lower()
    return (x or "").lower()

def league_name(x):
    if isinstance(x,dict):
        return x.get("name") or x.get("slug") or ""
    return x or ""

def fnum(x):
    try:
        v=float(x)
        return v if v>1.0 else None
    except:
        return None

def compact(s):
    return " ".join(str(s or "").strip().lower().replace("_"," ").replace("-"," ").split())

def canonical_market(name):
    n=compact(name)
    aliases={
        "moneyline":"ml","match winner":"ml","winner":"ml","ml":"ml",
        "spread":"spread","handicap":"spread","asian handicap":"spread",
        "totals":"totals","total":"totals","over under":"totals",
        "spread ht":"spread ht","handicap ht":"spread ht",
        "totals ht":"totals ht","total ht":"totals ht",
        "spread 1q":"spread 1q","totals 1q":"totals 1q",
        "spread 1h":"spread 1h","totals 1h":"totals 1h",
    }
    return aliases.get(n,n)

def human_market(name,sport):
    c=canonical_market(name)
    mapping={
        "ml":"Ganador del partido",
        "spread":"Hándicap",
        "spread ht":"Hándicap · 1ª parte",
        "spread 1q":"Hándicap · 1º cuarto",
        "spread 1h":"Hándicap · 1ª mitad",
        "totals ht":"Total · 1ª parte",
        "totals 1q":"Total · 1º cuarto",
        "totals 1h":"Total · 1ª mitad",
    }
    if c=="totals":
        return "Total de juegos" if sport=="tennis" else ("Total de puntos" if sport=="basketball" else "Total de goles")
    return mapping.get(c,name or "Mercado")

def line_value(market,row):
    for source in (row,market):
        for key in ("hdp","line","handicap","total"):
            if key in source and source.get(key) not in (None,""):
                try:return round(float(source.get(key)),4)
                except:return str(source.get(key))
    return None

def market_label_for_side(market,side):
    raw=market.get(side)
    return str(raw).strip() if raw not in (None,"") else ""

def canonical_side(market_name,market,side):
    s=compact(side)
    c=canonical_market(market_name)
    label=compact(market_label_for_side(market,side))

    # Totals are frequently transported as home/away but labelled Over/Under.
    if c.startswith("totals"):
        if label in {"over","more","más","mas"} or s=="over":
            return "over"
        if label in {"under","less","menos"} or s=="under":
            return "under"
        if s=="home":
            return "over"
        if s=="away":
            return "under"

    if s in {"home","away","draw","over","under"}:
        return s
    return s

def selection_label(market_name,market,side,line,home,away):
    cs=canonical_side(market_name,market,side)
    label=market_label_for_side(market,side)
    c=canonical_market(market_name)

    if c.startswith("totals"):
        if cs=="over": return f"Más de {line}" if line is not None else "Más de"
        if cs=="under": return f"Menos de {line}" if line is not None else "Menos de"

    if c.startswith("spread"):
        participant=home if cs=="home" else away if cs=="away" else (label or side)
        if line is not None:
            sign="+" if isinstance(line,(int,float)) and line>0 else ""
            return f"{participant} {sign}{line}"
        return participant

    if c=="ml":
        if cs=="home": return home
        if cs=="away": return away
        if cs=="draw": return "Empate"

    return label or (home if cs=="home" else away if cs=="away" else "Empate" if cs=="draw" else side)

def direct_link(event,bookmaker,market,row,side):
    for key in (f"{side}DirectLink","directLink","href"):
        if row.get(key): return row.get(key)
    for key in (f"{side}DirectLink","directLink","href"):
        if market.get(key): return market.get(key)
    urls=event.get("urls") or {}
    url=urls.get(bookmaker)
    if isinstance(url,str): return url
    if isinstance(url,dict):
        return url.get("href") or url.get("directLink") or ""
    return ""

def extract_offers(event,bookmaker):
    offers={}
    markets=(event.get("bookmakers") or {}).get(bookmaker) or []
    home,away=event.get("home",""),event.get("away","")
    sport=sport_slug(event.get("sport"))

    for market in markets:
        mname=market.get("name") or "Mercado"
        cm=canonical_market(mname)
        rows=market.get("odds") or []
        if not isinstance(rows,list): continue

        for row in rows:
            if not isinstance(row,dict): continue
            line=line_value(market,row)

            for side in ("home","away","draw","over","under"):
                odd=fnum(row.get(side))
                if odd is None: continue

                cs=canonical_side(mname,market,side)
                key=(cm,str(line),cs)
                # keep best duplicate quote from same bookmaker
                if key in offers and offers[key]["odds"]>=odd:
                    continue
                offers[key]={
                    "odds":odd,
                    "link":direct_link(event,bookmaker,market,row,side),
                    "market_label":human_market(mname,sport),
                    "selection_label":selection_label(mname,market,side,line,home,away),
                    "line":line,
                    "market_name":mname,
                    "side":cs
                }
    return offers

def fetch_events(sport):
    data = api_get("/events",{
        "sport": sport,
        "limit": EVENT_LIMIT_PER_BOOK
    })
    return data if isinstance(data, list) else []

def fetch_multi(ids):
    result=[]
    for i in range(0,len(ids),10):
        chunk=ids[i:i+10]
        if not chunk:
            continue
        data=api_get("/odds/multi",{
            "eventIds":",".join(chunk),
            "bookmakers":",".join(BOOKMAKERS)
        })
        if isinstance(data,list):
            result.extend(data)
    return result

def compare_event(event):
    offers_a=extract_offers(event,BOOKMAKERS[0])
    offers_b=extract_offers(event,BOOKMAKERS[1])
    shared=set(offers_a)&set(offers_b)
    out=[]
    home,away=event.get("home",""),event.get("away","")
    sport=sport_slug(event.get("sport"))
    league=league_name(event.get("league"))

    for key in shared:
        a,b=offers_a[key],offers_b[key]
        if not a["odds"] or not b["odds"]: continue

        if a["odds"]>=b["odds"]:
            best_book,best,other_book,other=BOOKMAKERS[0],a,BOOKMAKERS[1],b
        else:
            best_book,best,other_book,other=BOOKMAKERS[1],b,BOOKMAKERS[0],a

        gap=(best["odds"]/other["odds"]-1)*100
        if gap<MIN_PRICE_GAP: continue

        out.append({
            "type":"better_price",
            "sport":sport,
            "league":league,
            "home":home,
            "away":away,
            "market_label":best["market_label"],
            "selection_label":best["selection_label"],
            "price_gap":round(gap,2),
            "prices":[
                {"bookmaker":BOOKMAKERS[0],"odds":round(a["odds"],3),"best":BOOKMAKERS[0]==best_book,"link":a["link"]},
                {"bookmaker":BOOKMAKERS[1],"odds":round(b["odds"],3),"best":BOOKMAKERS[1]==best_book,"link":b["link"]}
            ],
            "message":f"{best_book} ofrece {best['odds']:.2f} frente a {other['odds']:.2f} en {other_book}.",
            "freshness":"Comparado directamente en ambas casas"
        })
    return out

def get_comparisons(sport):
    key=f"cmp:{sport}"
    now=time.time()
    cached=_cache.get(key)
    if cached and now-cached["ts"]<CACHE_TTL:
        return cached["data"]

    # Important: do NOT intersect two separately paginated bookmaker event lists.
    # Fetch one canonical event list, then request both books for those same IDs.
    events = fetch_events(sport)
    ids=[str(e.get("id")) for e in events if e.get("id") is not None]
    odds_events=fetch_multi(ids)

    out=[]
    for event in odds_events:
        # Only compare when BOTH bookmakers really returned odds for this event.
        books=event.get("bookmakers") or {}
        if BOOKMAKERS[0] not in books or BOOKMAKERS[1] not in books:
            continue
        out.extend(compare_event(event))

    out.sort(key=lambda x:x["price_gap"],reverse=True)
    _cache[key]={"ts":now,"data":out}
    return out

def human_arb(item):
    event=item.get("event") or {}
    sport=sport_slug(event.get("sport"))
    market=item.get("market") or {}
    mname=market.get("name") or market.get("label") or "Mercado"
    hdp=market.get("hdp")
    stakes={(x.get("bookmaker"),x.get("side")):x for x in (item.get("optimalStakes") or [])}
    legs=[]
    for leg in item.get("legs") or []:
        s=stakes.get((leg.get("bookmaker"),leg.get("side")),{})
        legs.append({
            "bookmaker":leg.get("bookmaker",""),
            "selection":leg.get("label") or leg.get("side") or "",
            "odds":leg.get("odds"),
            "stake":s.get("stake"),
            "link":leg.get("directLink") or leg.get("href") or ""
        })
    return {
        "type":"covered",
        "sport":sport,
        "league":league_name(event.get("league")),
        "home":event.get("home",""),
        "away":event.get("away",""),
        "market_label":human_market(mname,sport),
        "profit":round(float(item.get("profitMargin") or 0),2),
        "legs":legs,
        "message":"Si consigues colocar todas las apuestas a estas cuotas, el resultado queda cubierto."
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
    sport=(request.args.get("sport") or "all").lower()
    mode=request.args.get("mode") or "all"
    sports=list(ALLOWED_SPORTS) if sport=="all" else [sport]
    sports=[s for s in sports if s in ALLOWED_SPORTS]
    out=[]
    debug={}
    errors=[]

    if mode in ("all","better"):
        for s in sports:
            try:
                data=get_comparisons(s)
                debug[s]={"comparisons":len(data)}
                out.extend(data)
            except Exception as e:
                errors.append(f"{s}: {type(e).__name__}: {e}")
                debug[s]={"comparisons":0,"error":str(e)}

    if mode in ("all","covered"):
        try:
            arbs=api_get("/arbitrage-bets",{
                "bookmakers":",".join(BOOKMAKERS),
                "limit":100,
                "includeEventDetails":"true"
            })
            if isinstance(arbs,list):
                count=0
                for item in arbs:
                    x=human_arb(item)
                    if x["sport"] in sports:
                        out.append(x)
                        count+=1
                debug["arbitrage"]=count
        except Exception as e:
            errors.append(f"arbitrage: {type(e).__name__}: {e}")

    out.sort(key=lambda x:x.get("profit",x.get("price_gap",0)) or 0,reverse=True)
    return jsonify({"items":out[:100],"debug":debug,"errors":errors})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","8000")))
