
import os
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
h1{font-size:31px;line-height:1.03;margin:7px 0 8px}p{color:var(--muted);margin:0}
.refresh{border:0;border-radius:14px;background:#fff;color:#08111f;font-weight:900;padding:11px 13px;height:42px}
.status{margin:20px 0 12px;padding:11px 13px;border:1px solid var(--line);border-radius:14px;color:var(--muted);font-size:13px}.ok{color:#b7f7df}
.row{display:flex;gap:8px;overflow:auto;padding:5px 0}.chip{white-space:nowrap;border:1px solid var(--line);background:#121c2f;color:#cbd5e1;border-radius:999px;padding:10px 13px;font-weight:800}.chip.active{background:white;color:#0b1220}
#cards{display:grid;gap:12px;margin-top:12px}.card{background:linear-gradient(180deg,#182640,#121c2f);border:1px solid var(--line);border-radius:22px;padding:17px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:center}.badge{font-size:12px;font-weight:900;padding:7px 9px;border-radius:999px}.better{background:#123c32;color:#75efc1}.covered{background:#17355d;color:#a6cbff}.review{background:#4b3410;color:#ffd68a}.single{background:#252d3e;color:#d7deea}
.metric{font-size:21px;font-weight:900}.metric small{display:block;color:var(--muted);font-size:10px;text-align:right}
.event{font-size:19px;font-weight:900;margin:13px 0 4px}.meta{font-size:12px;color:var(--muted)}
.market{margin:14px 0;background:rgba(255,255,255,.05);border-radius:15px;padding:12px}.market-title{font-weight:900;margin-bottom:4px}.selection{color:#dbe3ee}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:12px}
.book{display:block;background:rgba(255,255,255,.05);border:1px solid transparent;border-radius:15px;padding:12px;color:inherit;text-decoration:none}
.book.best{border-color:#2d8c68;background:rgba(45,140,104,.12)}.book.disabled{opacity:.62}
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
<div class="eyebrow">RADAR PRIVADO · V0.7</div>
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

<footer><b>V0.7 privada.</b> Priorizamos que el radar siga mostrando oportunidades reales del feed. Cuando las dos casas ofrecen exactamente el mismo mercado, las compara; si solo una casa devuelve ese mercado, lo indica sin inventar una comparación.</footer>
</div>

<script>
let sport="all",mode="all";
const cards=document.getElementById("cards"),statusEl=document.getElementById("status");
const esc=x=>String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
const n=x=>Number.isFinite(Number(x))?Number(x).toFixed(2):(x??"—");
const ev=x=>[x.home,x.away].filter(Boolean).join(" – ")||"Evento";

function better(x){
  const compared=!!x.compared;
  const warn=compared && Number(x.price_gap||0)>=25;
  const badgeClass=compared?(warn?"review":"better"):"single";
  const badgeText=compared?(warn?"🟠 REVISAR DIFERENCIA":"🟢 PAGAN MEJOR AQUÍ"):"⚪ OPORTUNIDAD DETECTADA";

  const books=(x.prices||[]).map(b=>{
    const inner=`<div class="book-name">${esc(b.bookmaker)}</div>
      <div class="book-price">@ ${esc(b.odds??"—")}</div>
      ${b.best?'<div class="best-label">MEJOR CUOTA</div>':''}
      ${b.link?'<div class="open-label">ABRIR EN LA CASA ↗</div>':''}`;
    return b.link
      ? `<a class="book ${b.best?"best":""}" href="${esc(b.link)}" target="_blank" rel="noopener noreferrer">${inner}</a>`
      : `<div class="book ${b.odds==null?"disabled":""} ${b.best?"best":""}">${inner}</div>`;
  }).join("");

  return `<article class="card">
    <div class="top">
      <span class="badge ${badgeClass}">${badgeText}</span>
      <div class="metric">${compared?`+${n(x.price_gap)}%`:`+${n(x.provider_advantage)}%`}<small>${compared?"paga más":"señal del feed"}</small></div>
    </div>
    <div class="event">${esc(ev(x))}</div>
    <div class="meta">${esc(x.league||x.sport||"")}</div>
    <div class="market">
      <div class="market-title">${esc(x.market_label||x.market||"Mercado")}</div>
      <div class="selection">${esc(x.selection_label||x.selection||"")}</div>
      <div class="compare">${books}</div>
    </div>
    <div class="msg">${esc(x.message)}</div>
    <div class="fresh">${esc(x.freshness||"Actualizado recientemente")}</div>
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
  cards.innerHTML='<div class="empty">Buscando oportunidades…</div>';
  try{
    const r=await fetch(`/api/opportunities?sport=${encodeURIComponent(sport)}&mode=${encodeURIComponent(mode)}`,{cache:"no-store"});
    const d=await r.json();
    const items=d.items||[];
    cards.innerHTML=items.length?items.map(x=>x.type==="covered"?covered(x):better(x)).join("")
      :'<div class="empty">Ahora mismo no hay oportunidades con estos filtros.<br><br>Prueba a actualizar en unos minutos.</div>';
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
    if c=="spread": return "Hándicap"
    if c=="totals":
        return "Total de juegos" if sport=="tennis" else ("Total de puntos" if sport=="basketball" else "Total de goles")
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
        "updated_at":item.get("expectedValueUpdatedAt","")
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

def line_equiv(a,b):
    if a is None or b is None: return True
    try:return abs(float(a)-float(b))<1e-9
    except:return str(a)==str(b)

def extract_other_quote(event_data, target_book, target):
    books=(event_data or {}).get("bookmakers") or {}
    markets=books.get(target_book) or []
    target_market=target["market"]
    target_line=target["line"]
    target_side=canonical_side(target_market,target["market_obj"],target["side"])
    target_label=compact(label_for_side(target["market_obj"],target["side"]))

    for market in markets:
        mname=market.get("name") or ""
        if not market_equiv(mname,target_market):
            continue
        rows=market.get("odds") or []
        for row in rows:
            row_line=line_value(market,row)
            if not line_equiv(row_line,target_line):
                continue

            candidates=[]
            for side in ("home","away","draw","over","under"):
                val=fnum(row.get(side))
                if val is None: continue
                cs=canonical_side(mname,market,side)
                lab=compact(label_for_side(market,side))
                score=0
                if cs==target_side: score+=2
                if target_label and lab==target_label: score+=3
                candidates.append((score,side,val))

            if not candidates:
                continue

            candidates.sort(reverse=True,key=lambda x:x[0])
            score,side,val=candidates[0]
            if score<=0:
                continue

            link=(
                row.get(f"{side}DirectLink")
                or row.get("directLink")
                or row.get("href")
                or market.get("href")
                or market.get("directLink")
                or ""
            )
            return {"odds":val,"link":link}
    return None

def make_card(v):
    other_book=BOOKMAKERS[1] if v["bookmaker"]==BOOKMAKERS[0] else BOOKMAKERS[0]
    other=None
    if v["event_id"] is not None:
        event_data=get_event_odds(v["event_id"])
        other=extract_other_quote(event_data,other_book,v)

    prices=[]
    quoted={
        v["bookmaker"]:{"odds":v["odds"],"link":v["link"]},
        other_book:other or {"odds":None,"link":""}
    }

    compared=other is not None and other.get("odds") is not None and v["odds"] is not None
    if compared:
        best_book=max(quoted,key=lambda b:quoted[b]["odds"])
        worst_book=min(quoted,key=lambda b:quoted[b]["odds"])
        best_odds=quoted[best_book]["odds"]
        worst_odds=quoted[worst_book]["odds"]
        gap=round((best_odds/worst_odds-1)*100,2)
        message=f"{best_book} ofrece {best_odds:.2f} frente a {worst_odds:.2f} en {worst_book}."
    else:
        best_book=v["bookmaker"]
        gap=0.0
        message=f"{v['bookmaker']} ofrece {v['odds']:.2f}. La otra casa no devuelve ahora mismo este mercado exacto en el feed."

    for b in BOOKMAKERS:
        q=quoted.get(b) or {}
        prices.append({
            "bookmaker":b,
            "odds":q.get("odds"),
            "link":q.get("link",""),
            "best":b==best_book
        })

    return {
        "type":"better_price",
        "sport":v["sport"],
        "league":v["league"],
        "home":v["home"],
        "away":v["away"],
        "market_label":human_market(v["market"],v["sport"]),
        "selection_label":human_selection(v["market"],v["market_obj"],v["side"],v["line"],v["home"],v["away"]),
        "prices":prices,
        "compared":compared,
        "price_gap":gap,
        "provider_advantage":v["provider_advantage"],
        "message":message,
        "freshness":"Comparación confirmada" if compared else "Pendiente de segunda cuota"
    }

def get_value_cards(sports):
    raw=[]
    for bookmaker in BOOKMAKERS:
        for sport in sports:
            try:
                data=api_get("/value-bets",{
                    "bookmaker":bookmaker,
                    "sport":sport,
                    "includeEventDetails":"true"
                })
                if isinstance(data,list):
                    for item in data:
                        v=parse_value(item)
                        if v["sport"] in ALLOWED_SPORTS and v["odds"] is not None:
                            raw.append(v)
            except:
                continue

    # Deduplicate the same event/market/line/side; keep strongest signal.
    dedup={}
    for v in raw:
        key=(v["event_id"],canonical_market(v["market"]),str(v["line"]),canonical_side(v["market"],v["market_obj"],v["side"]))
        if key not in dedup or v["provider_advantage"]>dedup[key]["provider_advantage"]:
            dedup[key]=v

    # Limit expensive enrichment to strongest opportunities.
    candidates=sorted(dedup.values(),key=lambda x:x["provider_advantage"],reverse=True)[:35]
    cards=[make_card(v) for v in candidates]

    # Compared opportunities first, then feed-only opportunities.
    cards.sort(key=lambda x:(1 if x["compared"] else 0,x["price_gap"] if x["compared"] else x["provider_advantage"]),reverse=True)
    return cards

def human_arb(item):
    event=item.get("event") or {}
    sport=sport_slug(event.get("sport"))
    market=item.get("market") or {}
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
    try:profit=float(item.get("profitMargin") or 0)
    except:profit=0
    return {
        "type":"covered",
        "sport":sport,
        "league":league_name(event.get("league")),
        "home":event.get("home",""),
        "away":event.get("away",""),
        "market_label":human_market(market.get("name") or market.get("label") or "Mercado",sport),
        "profit":round(profit,2),
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

    if mode in ("all","better"):
        out.extend(get_value_cards(sports))

    if mode in ("all","covered"):
        try:
            data=api_get("/arbitrage-bets",{
                "bookmakers":",".join(BOOKMAKERS),
                "limit":100,
                "includeEventDetails":"true"
            })
            if isinstance(data,list):
                for item in data:
                    x=human_arb(item)
                    if x["sport"] in sports:
                        out.append(x)
        except:
            pass

    out.sort(
        key=lambda x:(
            2 if x["type"]=="covered" else 1 if x.get("compared") else 0,
            x.get("profit",x.get("price_gap",x.get("provider_advantage",0))) or 0
        ),
        reverse=True
    )
    return jsonify({"items":out[:80]})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","8000")))
