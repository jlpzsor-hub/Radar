RADAR PRIVADO V0 — iPhone

QUÉ ES
Web móvil privada para Bet365 + William Hill usando Odds-API.io.
Muestra:
- "Esta casa paga más" (value bets del proveedor)
- "Resultado cubierto" (arbitrajes entre las dos casas)
- Filtros para fútbol, tenis y baloncesto

IMPORTANTE
La API Key nunca va en el navegador. Se configura como variable de entorno ODDS_API_KEY en el hosting.

FORMA MÁS FÁCIL DE USARLO EN IPHONE
1. Sube esta carpeta a un hosting Python (por ejemplo Render).
2. Configura la variable ODDS_API_KEY con tu clave de Odds-API.io.
3. Despliega.
4. Abre la URL del hosting desde Safari.
5. Safari > Compartir > Añadir a pantalla de inicio.
6. Se abrirá como una app.

RENDER
El proyecto incluye render.yaml.
En el panel del servicio añade:
ODDS_API_KEY = tu clave privada

COMANDO LOCAL (opcional)
pip install -r requirements.txt
export ODDS_API_KEY="TU_CLAVE"
python app.py
Luego abre http://localhost:8000

NOTAS
- V0: usa los endpoints propios de value-bets y arbitrage-bets de Odds-API.io.
- Las cuotas cambian. Verifica mercado, línea y precio antes de confirmar.
- La siguiente versión debería comparar directamente las cuotas de ambos books y guardar histórico/latencia.
