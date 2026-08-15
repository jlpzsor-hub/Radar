
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
h1{font-size:31px;line-height:1.03;margin:7px 0 8px}p{color:var(--muted);margin:0}.refresh{border:0;border-radius:14px;background:#fff;color:#08111f;font-weight:900;padding:11px 13px;height:42px}
.status{margin:20px 0 12px;padding:11px 13px;border:1px solid var(--line);border-radius:14px;color:var(--muted);font-size:13px}.ok{color:#b7f7df}
.row{display:flex;gap:8px;overflow:auto;padding:5px 0}.chip{white-space:nowrap;border:1px solid var(--line);background:#121c2f;color:#cbd5e1;border-radius:999px;padding:10px 13px;font-weight:800}.chip.active{background:white;color:#0b1220}
#cards{display:grid;gap:12px;margin-top:12px}.card{background:linear-gradient(180deg,#182640,#121c2f);border:1px solid var(--line);border-radius:22px;padding:17px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:center}.badge{font-size:12px;font-weight:900;padding:7px 9px;border-radius:999px}.better{background:#123c32;color:#75efc1}.covered{background:#17355d;color:#a6cbff}
.metric{font-size:21px;font-weight:900}.event{font-size:19px;font-weight:900;margin:13px 0 4px}.meta{font-size:12px;color:var(--muted)}
.market{margin:14px 0;background:rgba(255,255,255,.05);border-radius:15px;padding:12px}.price{font-size:26px;font-weight:900;margin-top:7px}.msg{font-size:14px;line-height:1.45;color:#dbe3ee}
.leg{background:rgba(255,255,255,.05);border-radius:14px;padding:11px;display:flex;justify-content:space-between;margin-top:8px}.empty{text-align:center;color:var(--muted);padding:40px 15px}
footer{font-size:11px;color:#718096;line-height:1.5;padding:25px 4px}
</style>
</head>
<body>
<div class="shell">
<header>
<div>
<div class="eyebrow">RADAR PRIVADO · V0.1</div>
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
<button class="chip mode" data-mode="better">Pagan más</button>
<button class="chip mode" data-mode="covered">Ganancia cubierta</button>
</div>

<main id="cards"><div class="empty">Cargando oportunidades…</div></main>

<footer><b>V0.1 privada.</b> Las cuotas cambian. Verifica siempre mercado, línea y precio antes de confirmar.</footer>
</div>

<script>
let sport="all",mode="all";
const cards=document.getElementById("cards"),statusEl=document.getElementById("status");

const esc=x=>String(x??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]));
const n=x=>Number.isFinite(Number(x))?Number(x).toFixed(2):(x??"—");
const ev=x=>[x.home,x.away].filter(Boolean).join(" – ")||"Evento";

function better(x){
  return `<article class="card">
    <div class="top">
      <span class="badge better">🟢 ESTA CASA PAGA MÁS</span>
      <div class="metric">+${n(x.advantage)}%</div>
    </div>
    <div class="event">${esc(ev(x))}</div>
    <div class="meta">${esc(x.league||x.sport||"")}</div>
    <div class="market">
      <b>${esc(x.market||"Mercado")}</b>
      <div>${esc(x.bookmaker)} · ${esc(x.selection)}</div>
      <div class="price">@ ${esc(x.odds||"—")}</div>
    </div>
    <div class="msg">${esc(x.message)}</div>
  </article>`;
}

function covered(x){
  let legs=(x.legs||[]).map(l=>`<div class="leg">
    <div><b>${esc(l.bookmaker)}</b><br>${esc(l.selection)}</div>
    <div style="text-align:right"><b>@ ${esc(l.odds||"—")}</b>${l.stake!=null?`<br>${n(l.stake)} €`:""}</div>
  </div>`).join("");

  return `<article class="card">
    <div class="top">
      <span class="badge covered">🔵 RESULTADO CUBIERTO</span>
      <div class="metric">+${n(x.profit)}%</div>
    </div>
    <div class="event">${esc(ev(x))}</div>
    <div class="meta">${esc(x.league||x.sport||"")}</div>
    <div class="market"><b>${esc(x.market||"Mercado")}</b>${legs}</div>
    <div class="msg">${esc(x.message)}</div>
  </article>`;
}

async function load(){
  cards.innerHTML='<div class="empty">Buscando oportunidades…</div>';
  try{
    let r=await fetch(`/api/opportunities?sport=${encodeURIComponent(sport)}&mode=${encodeURIComponent(mode)}`,{cache:"no-store"});
    let d=await r.json();
    let items=d.items||[];
    cards.innerHTML=items.length
      ? items.map(x=>x.type==="covered"?covered(x):better(x)).join("")
      : '<div class="empty">Ahora mismo no hemos encontrado oportunidades con estos filtros.<br><br>Prueba a actualizar dentro de unos minutos.</div>';
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
  }catch(e){
    statusEl.textContent="● Sin conexión";
  }
}

document.querySelectorAll("[data-sport]").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("[data-sport]").forEach(x=>x.classList.remove("active"));
  b.classList.add("active");
  sport=b.dataset.sport;
  load();
});

document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("[data-mode]").forEach(x=>x.classList.remove("active"));
  b.classList.add("active");
  mode=b.dataset.mode;
  load();
});

document.getElementById("refresh").onclick=load;
st();
load();
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
    r = requests.get(f"{API_BASE}{path}", params=p, timeout=15)
    r.raise_for_status()
    return r.json()

def normalize_sport(value):
    return (value or "").strip().lower()

def ev_to_advantage(raw_ev):
    """
    Odds-API.io EV may arrive as 110.73 for +10.73%.
    Convert to the user-facing advantage.
    """
    try:
        raw = float(raw_ev)
    except Exception:
        return 0.0
    if raw >= 100:
        return round(raw - 100, 2)
    return round(raw, 2)

def nice_value(item):
    event = item.get("event") or {}
    market = item.get("market") or {}
    bo = item.get("bookmakerOdds") or {}
    side = (item.get("betSide") or "").lower()

    odd = bo.get(side)
    if odd is None:
        odd = (
            bo.get("home") if side == "home"
            else bo.get("away") if side == "away"
            else bo.get("draw") if side == "draw"
            else None
        )

    sport = normalize_sport(event.get("sport"))

    return {
        "type": "better_price",
        "sport": sport,
        "league": event.get("league", ""),
        "home": event.get("home", ""),
        "away": event.get("away", ""),
        "bookmaker": item.get("bookmaker", ""),
        "selection": item.get("betSide", ""),
        "market": market.get("name", market.get("label", "Mercado")),
        "odds": odd,
        "advantage": ev_to_advantage(item.get("expectedValue", 0)),
        "message": f"{item.get('bookmaker','Esta casa')} está pagando mejor de lo normal en esta opción."
    }

def nice_arb(item):
    event = item.get("event") or {}
    sport = normalize_sport(event.get("sport"))
    legs = []

    for leg in item.get("legs") or []:
        legs.append({
            "bookmaker": leg.get("bookmaker", ""),
            "selection": leg.get("label") or leg.get("side") or "",
            "odds": leg.get("odds"),
            "stake": None
        })

    try:
        profit = float(item.get("profitMargin", 0))
    except Exception:
        profit = 0.0

    return {
        "type": "covered",
        "sport": sport,
        "league": event.get("league", ""),
        "home": event.get("home", ""),
        "away": event.get("away", ""),
        "market": (item.get("market") or {}).get("label") or (item.get("market") or {}).get("name") or "Mercado",
        "profit": round(profit, 2),
        "legs": legs,
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
    out = []
    errors = []

    requested_sports = list(ALLOWED_SPORTS) if sport == "all" else [sport]
    requested_sports = [s for s in requested_sports if s in ALLOWED_SPORTS]

    if mode in ("all", "better"):
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
                            nice = nice_value(item)
                            if nice["sport"] in ALLOWED_SPORTS:
                                out.append(nice)
                except Exception as e:
                    errors.append(f"{bookmaker}/{sport_slug}: {e}")

    if mode in ("all", "covered"):
        try:
            data = odds_get("/arbitrage-bets", {
                "bookmakers": ",".join(BOOKMAKERS),
                "includeEventDetails": "true",
                "limit": 100
            })

            if isinstance(data, list):
                for item in data:
                    nice = nice_arb(item)
                    if nice["sport"] not in ALLOWED_SPORTS:
                        continue
                    if sport != "all" and nice["sport"] != sport:
                        continue
                    out.append(nice)

        except Exception as e:
            errors.append(f"Arbitraje: {e}")

    out.sort(
        key=lambda x: x.get("profit", x.get("advantage", 0)) or 0,
        reverse=True
    )

    return jsonify({"items": out[:120], "errors": errors})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
