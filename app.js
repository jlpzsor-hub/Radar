
let sport = "all";
let mode = "all";

const cards = document.getElementById("cards");
const statusEl = document.getElementById("status");

function esc(x){return String(x ?? "").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]))}
function fmtNum(x){
  const n = Number(x);
  return Number.isFinite(n) ? n.toFixed(2) : x ?? "—";
}
function eventName(x){ return [x.home,x.away].filter(Boolean).join(" – ") || "Evento"; }

function cardBetter(x){
  const line = x.line !== null && x.line !== undefined ? ` · Línea ${esc(x.line)}` : "";
  return `<article class="card">
    <div class="top">
      <span class="badge better">🟢 ESTA CASA PAGA MÁS</span>
      <div class="metric">+${fmtNum(x.advantage)}% <small>ventaja</small></div>
    </div>
    <div class="event">${esc(eventName(x))}</div>
    <div class="meta">${esc(x.league || x.sport || "")}</div>
    <div class="market">
      <strong>${esc(x.market || "Mercado")}${line}</strong>
      <div>${esc(x.bookmaker)} · ${esc(x.selection)}</div>
      <div class="price">@ ${esc(x.odds || "—")}</div>
    </div>
    <div class="message">${esc(x.message)}</div>
    ${x.link ? `<a class="action" href="${esc(x.link)}" target="_blank" rel="noreferrer">Abrir casa ↗</a>` : ""}
  </article>`;
}

function cardCovered(x){
  const legs = (x.legs||[]).map(l => `<div class="leg">
    <div><b>${esc(l.bookmaker)}</b><span>${esc(l.selection)}</span></div>
    <div style="text-align:right"><b>@ ${esc(l.odds||"—")}</b>${l.stake!=null?`<span>${fmtNum(l.stake)} €</span>`:""}</div>
  </div>`).join("");
  return `<article class="card">
    <div class="top">
      <span class="badge covered">🔵 RESULTADO CUBIERTO</span>
      <div class="metric">+${fmtNum(x.profit)}% <small>aprox.</small></div>
    </div>
    <div class="event">${esc(eventName(x))}</div>
    <div class="meta">${esc(x.league || x.sport || "")}</div>
    <div class="market"><strong>${esc(x.market || "Mercado")}</strong><div class="legs">${legs}</div></div>
    <div class="message">${esc(x.message)}</div>
  </article>`;
}

async function load(){
  cards.innerHTML = `<div class="empty">Buscando oportunidades…</div>`;
  try{
    const r = await fetch(`/api/opportunities?sport=${encodeURIComponent(sport)}&mode=${encodeURIComponent(mode)}`, {cache:"no-store"});
    const data = await r.json();
    const items = data.items || [];
    if(!items.length){
      cards.innerHTML = `<div class="empty">Ahora mismo no hemos encontrado oportunidades con estos filtros.<br><br>Prueba a actualizar dentro de unos minutos.</div>`;
    }else{
      cards.innerHTML = items.map(x=>x.type==="covered"?cardCovered(x):cardBetter(x)).join("");
    }
    if((data.errors||[]).length) console.warn(data.errors);
  }catch(e){
    cards.innerHTML = `<div class="empty">No se ha podido consultar el radar.<br>${esc(e.message)}</div>`;
  }
}

async function checkStatus(){
  try{
    const r = await fetch("/api/status");
    const s = await r.json();
    statusEl.textContent = s.ok ? `● Conectado · ${s.bookmakers.join(" + ")}` : `● ${s.message}`;
    if(s.ok) statusEl.classList.add("ok");
  }catch(e){ statusEl.textContent="● Sin conexión con el servidor"; }
}

document.querySelectorAll(".chip").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".chip").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); sport=b.dataset.sport; load();
});
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); mode=b.dataset.mode; load();
});
document.getElementById("refresh").onclick=load;

checkStatus(); load();
