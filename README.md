# Crypto Morning Screener

A multi-mode crypto scanner (intraday / BTST / swing / range / investment)
across your 44-coin watchlist, with a live heatmap, rule-based entry/SL/target
generation, and a multi-exchange price fallback chain. Built as a sibling
project to the F&O Morning Screener, same architecture pattern.

## What's in here

```
backend/
  coin_universe.py      44-coin watchlist, grouped by risk/liquidity category
  indicators.py          EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, OBV (pure Python, no pandas)
  heatmap.py              24h change/volume aggregation across the universe
  sources/
    price_waterfall.py    CoinDCX -> Delta Exchange -> Binance -> CoinGecko fallback chain
  strategies/
    engine.py              per-mode scoring + entry/SL/target generation
  app.py                   Flask API tying it all together
  requirements.txt
frontend/
  index.html               standalone dashboard (heatmap + 5 scan tabs), calls the Flask API
```

## Running it

```
cd backend
pip install -r requirements.txt --break-system-packages
python app.py
```

This starts the API on http://localhost:5000. Then open frontend/index.html
directly in a browser (double-click it, or `open frontend/index.html`) --
it has an API base URL field pre-filled to http://localhost:5000, click Connect.

## Important: what's verified vs what isn't yet

I built and tested this inside a sandboxed environment that cannot reach
external exchange APIs (CoinDCX, Delta, Binance, CoinGecko are all
network-blocked here). So here's the honest breakdown:

Fully tested and verified (500+ stress trials, real HTTP requests, real
JS execution against a live server):
- All indicator math (EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, OBV)
- The full strategy engine across all 5 modes, including the entry/SL/target
  ordering logic at extreme price scales (sub-cent memecoins to BTC prices)
- The Flask API routes, caching layer, CORS headers, JSON response shapes
- The dashboard's JS rendering logic against live API responses (heatmap +
  all 5 scan tabs), executed with Node against a running server

NOT yet verified (needs you to run it once with real internet access):
- Whether CoinDCX's public candle endpoint (/market_data/candles) actually
  accepts the pair format used here (B-BTC_USDT) -- CoinDCX's public API
  has changed shape before and it could not be called from this sandbox
  to confirm.
- Whether Delta Exchange India's /v2/history/candles endpoint and symbol
  naming (BTCUSD style) match what's assumed -- same reachability issue.
- Real-world latency of the universe scan across 44 symbols x multiple
  exchanges (synthetic data made this near-instant; real API calls with
  network round-trips will be much slower, which is why the in-memory cache
  with per-interval TTLs exists -- but watch the first live run's timing
  before treating this as "morning-routine fast").

Recommended first real run: start app.py and hit
http://localhost:5000/api/scan?symbol=BTCUSDT&modes=intraday directly in
a browser first. Check the data_sources field in the response -- it shows
which exchange in the waterfall actually answered. If CoinDCX and Delta both
fail and it falls through to Binance every time, that's fine (Binance is the
deepest/most reliable proxy feed anyway) but worth knowing. If you hit actual
error messages from a failed CoinDCX/Delta call, that's the most useful thing
to share back -- the source adapters can be fixed against the real error,
but can't be iterated against their live response shape from this sandbox.

## Do you need API keys / secrets (like the F&O screener needs Angel One)?

No, not for this as built. The F&O screener needs Angel One/Zerodha
credentials because it reads your personal trading account (positions,
order book) via an authenticated API. This crypto screener only reads
public market data (price candles) -- it doesn't touch any account, doesn't
place orders, and doesn't need to know who you are. CoinDCX's public market
data API, Delta Exchange's public candle history, Binance's public REST API,
and CoinGecko's public API all serve OHLCV candles without any key.

The tradeoff is public endpoints sometimes have tighter rate limits than
authenticated ones. If you ever want this to pull your actual Delta/CoinDCX
*account* data (your open positions, your specific order book access) rather
than generic public market data, that's a separate, optional upgrade -- ask
and it can be added, but it's not required for the entry/SL/target scanning
this was built to do.

## Deploying to Render

There are two pieces to deploy: the Flask **backend** (the API) and the
**frontend** (the dashboard HTML). They're independent — the dashboard is
just a static file that calls whatever API URL you put in its "Connect"
field, so you can deploy them separately and point one at the other.

### Backend (Flask API)

**Option A — using the included render.yaml (Blueprint):**
1. Push this whole project to a GitHub repo.
2. In the Render dashboard: New -> Blueprint -> connect the repo. Render
   reads `render.yaml` at the project root and configures everything
   automatically (build command, start command, Python version).
3. Click Apply. Wait for the build -- first build typically takes a few
   minutes.
4. Your API will be live at something like
   `https://crypto-morning-screener-api.onrender.com`.

**Option B — manual setup (if you skip the Blueprint):**
1. New -> Web Service -> connect your GitHub repo.
2. Root directory: `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Plan: Free
6. Click Create Web Service.

Either way, once it's live, test it the same way you would locally:
`https://your-app.onrender.com/api/health` should return `{"status":"ok",...}`.

### Frontend (dashboard)

The dashboard is a single static HTML file with no build step, so the
simplest options are:
- **Static Site on Render**: New -> Static Site -> connect the repo,
  set root directory to `frontend`, leave build command empty (or
  `echo "no build needed"`), publish directory `.`. Render gives you a
  static URL.
- **Or just keep running it locally** by double-clicking `frontend/index.html`
  -- it works fine as a local file too, since it only talks to whatever API
  URL you type into the Connect field. No need to deploy it if you're the
  only user.

Either way: after the backend is deployed, open the dashboard and replace
`http://localhost:5000` in the API base field with your Render URL
(e.g. `https://crypto-morning-screener-api.onrender.com`), click Connect.

### Render free tier caveats that actually matter for a "morning screener"

- **Free web services spin down after 15 minutes of inactivity** and take
  about a minute to wake up on the next request. If you only check this
  once in the morning, your first request of the day will be slow
  (~60 seconds) while it wakes up -- this is normal Render free-tier
  behavior, not a bug in this code.
- **The in-memory cache resets on every cold start/restart.** Since Render's
  free tier sleeps and wakes your service, the cache effectively resets
  every morning anyway -- so the in-memory cache mostly helps within a
  single active session (e.g. flipping between scan tabs), not across days.
  If this bothers you, the Redis swap described below survives restarts.
- **750 free instance-hours per workspace per month.** A service that's
  asleep most of the day won't burn through this; one running 24/7 will
  hit the cap partway through the month and get suspended until next month.
  For a "check it in the morning" use case this should be fine as-is.
- No credit card is required for the free tier as of this writing, but
  always double check current limits on Render's own pricing page since
  these change.

### Environment variables on Render

If you tighten CORS for production, set `CORS_ALLOWED_ORIGINS` in the
Render dashboard's Environment tab to your dashboard's deployed URL
(comma-separated if you have more than one). Left unset, it defaults to
allowing all origins, which is fine for a read-only public market-data API
like this one.

## Auto-refresh (dashboard) and keep-alive (backend) -- two different things

These solve different problems and only one of them is purely a dashboard
feature:

### Auto-refresh (built into the dashboard, no setup needed)

The dashboard has an "Auto-refresh" dropdown in the top bar -- Off, 1 min,
3 min (default), 5 min, or 10 min. While the dashboard tab is open, it
re-fetches whichever panel you're currently looking at on that interval, and
shows a "last updated" timestamp. An in-flight guard skips a tick if the
previous refresh is still running, so it won't stack up overlapping requests
if a real exchange API call is slow.

Important: this only runs while the browser tab is open and your computer is
awake. It does **not** keep the Render backend from sleeping by itself --
closing the tab stops the pings entirely.

### Keeping the Render backend awake 24/7 (needs an external ping)

A `.github/workflows/keep-render-awake.yml` is included. It pings your
deployed backend's `/api/health` every 10 minutes via GitHub Actions, which
runs independently of whether your browser or laptop is on -- this is what
actually prevents Render's 15-minute sleep, not the dashboard's auto-refresh.

Setup:
1. Deploy the backend to Render first and copy its URL.
2. In your GitHub repo: Settings -> Secrets and variables -> Actions ->
   New repository secret -> name it `RENDER_APP_URL`, paste the URL
   (e.g. `https://crypto-morning-screener-api.onrender.com`).
3. Push the repo. GitHub starts running the ping automatically every
   10 minutes -- no further action needed.

Alternative if you'd rather not use GitHub Actions: **UptimeRobot**'s free
plan supports up to 50 monitors at 5-minute intervals -- sign up, add a
monitor pointed at your Render URL's `/api/health` path, done. Either
approach is a well-known community workaround, not something Render
officially guarantees -- their own docs point to a paid instance as the
supported way to avoid sleep, so treat the free workaround as solid but
not contractually reliable.

**The 750-hour math, worked out honestly:** running 24/7 for a 30-day month
needs about 720 instance-hours, against Render's free 750-hour/month cap --
so it does fit, but with only about 30 hours of slack. That's fine if this
is the only free service you run in your Render workspace; if you add
others that also run continuously, they share the same 750-hour pool and
you could get suspended before the month ends.

## Swapping the cache for Redis (matches the F&O screener pattern)

app.py has an InMemoryCache class with a tiny get/set interface. To swap in
Redis on Render, replace it with something like:

```
import redis, json
class RedisCache:
    def __init__(self, url):
        self.client = redis.from_url(url)
    def get(self, key):
        val = self.client.get(key)
        return json.loads(val) if val else None
    def set(self, key, value, ttl_seconds):
        self.client.setex(key, ttl_seconds, json.dumps(value))
```

Note: the current in-memory cache stores raw Python tuples (candles, source),
not JSON-serializable dicts directly -- adjust the value shape slightly when
switching to Redis (json.dumps needs serializable types).

## Design notes / things to know before trusting the signals

- Range mode deliberately suppresses itself during strong trends. Fading a
  Bollinger Band touch inside a strong downtrend is "catching a falling
  knife," not mean reversion -- there's an EMA-slope trend filter that zeroes
  out range signals above a 1.5% threshold.
- Investment mode is long-only. Short signals are suppressed there on
  purpose -- it's framed as an accumulation tool, not a leveraged short tool.
- Confidence % is a transparent rule count, not a backtested win rate. It
  reflects how many of the weighted technical rules agree, out of the max
  possible for that mode. It is not a probability of the trade working out.
  Treat 80% confidence as "most of my rules agree," not "80% win chance."
- No backtest has been run on this logic against real historical data.
  Everything here is forward-looking rule evaluation, not validated against
  what would have happened historically. Worth backtesting before sizing up
  real capital against any single mode's signals, especially range mode's
  fade logic and investment mode's wide ATR-based targets.
