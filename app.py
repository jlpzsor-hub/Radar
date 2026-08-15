
import os
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

API_BASE = "https://api.odds-api.io/v3"
BOOKMAKERS = ["Bet365", "William Hill"]
SPORTS = {"football": "Fútbol", "tennis": "Tenis", "basketball": "Baloncesto"}

def api_key():
    return os.getenv("ODDS_API_KEY", "").strip()

def odds_get(path, params=None):
    key = api_key()
    if not key:
        raise RuntimeError("Falta ODDS_API_KEY en el servidor.")
    params = dict(params or {})
    params["apiKey"] = key
    r = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def nice_value(item):
    event = item.get("event") or {}
    market = item.get("market") or {}
    bookmaker_odds = item.get("bookmakerOdds") or {}
    side = (item.get("betSide") or "").lower()

    # Odds field can vary by side.
    odd = bookmaker_odds.get(side)
    if odd is None:
        if side == "home":
            odd = bookmaker_odds.get("home")
        elif side == "away":
            odd = bookmaker_odds.get("away")
        elif side == "draw":
            odd = bookmaker_odds.get("draw")

    try:
        ev = float(item.get("expectedValue", 0))
    except Exception:
        ev = 0.0

    return {
        "type": "better_price",
        "sport": event.get("sport", ""),
        "league": event.get("league", ""),
        "home": event.get("home", ""),
        "away": event.get("away", ""),
        "date": event.get("date", ""),
        "bookmaker": item.get("bookmaker", ""),
        "selection": item.get("betSide", ""),
        "market": market.get("name", market.get("label", "Mercado")),
        "line": market.get("hdp"),
        "odds": odd,
        "advantage": round(ev, 2),
        "updated": item.get("expectedValueUpdatedAt", ""),
        "link": bookmaker_odds.get(f"{side}DirectLink") or bookmaker_odds.get("href") or "",
        "message": f"{item.get('bookmaker','Esta casa')} está pagando mejor de lo normal en esta opción."
    }

def nice_arb(item):
    event = item.get("event") or {}
    legs = item.get("legs") or []
    stakes = item.get("optimalStakes") or []
    stake_map = {(s.get("bookmaker"), s.get("side")): s for s in stakes}

    parts = []
    for leg in legs:
        key = (leg.get("bookmaker"), leg.get("side"))
        s = stake_map.get(key, {})
        parts.append({
            "bookmaker": leg.get("bookmaker", ""),
            "selection": leg.get("label") or leg.get("side") or "",
            "odds": leg.get("odds"),
            "stake": s.get("stake"),
            "potential_return": s.get("potentialReturn"),
            "link": leg.get("directLink") or leg.get("href") or ""
        })

    try:
        margin = float(item.get("profitMargin", 0))
    except Exception:
        margin = 0.0

    return {
        "type": "covered",
        "sport": event.get("sport", ""),
        "league": event.get("league", ""),
        "home": event.get("home", ""),
        "away": event.get("away", ""),
        "date": event.get("date", ""),
        "market": (item.get("market") or {}).get("label") or (item.get("market") or {}).get("name") or "Mercado",
        "profit": round(margin, 2),
        "total_stake": item.get("totalStake"),
        "legs": parts,
        "updated": item.get("updatedAt", ""),
        "message": "Si puedes colocar todas las apuestas a estas cuotas, el resultado queda cubierto."
    }

@app.route("/")
def index():
    return render_template("index.html", bookmakers=BOOKMAKERS, sports=SPORTS)

@app.route("/api/status")
def status():
    return jsonify({
        "ok": bool(api_key()),
        "bookmakers": BOOKMAKERS,
        "message": "Conectado" if api_key() else "Falta configurar la API Key en el servidor"
    })

@app.route("/api/opportunities")
def opportunities():
    sport = request.args.get("sport", "all")
    mode = request.args.get("mode", "all")
    out = []
    errors = []

    if mode in ("all", "better"):
        for bookmaker in BOOKMAKERS:
            params = {"bookmaker": bookmaker, "includeEventDetails": "true"}
            if sport != "all":
                params["sport"] = sport
            try:
                data = odds_get("/value-bets", params)
                if isinstance(data, list):
                    out.extend(nice_value(x) for x in data)
            except Exception as e:
                errors.append(f"{bookmaker}: {e}")

    if mode in ("all", "covered"):
        params = {
            "bookmakers": ",".join(BOOKMAKERS),
            "includeEventDetails": "true",
            "limit": 100
        }
        try:
            data = odds_get("/arbitrage-bets", params)
            if isinstance(data, list):
                arbs = [nice_arb(x) for x in data]
                if sport != "all":
                    arbs = [x for x in arbs if (x.get("sport") or "").lower() == sport]
                out.extend(arbs)
        except Exception as e:
            errors.append(f"Arbitraje: {e}")

    # Highest apparent opportunity first.
    def score(x):
        return x.get("profit", x.get("advantage", 0)) or 0
    out.sort(key=score, reverse=True)

    return jsonify({"items": out[:120], "errors": errors})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
