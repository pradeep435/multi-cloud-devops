from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from prometheus_client import Counter, Gauge, generate_latest
import time, os

app = Flask(__name__)
START_TIME = time.time()
CLOUD = os.environ.get("CLOUD_PROVIDER", "AWS")

REQUEST_COUNT  = Counter('app_requests_total', 'Total requests', ['endpoint'])
SEARCH_COUNT   = Counter('app_searches_total', 'Total searches')
WATCHLIST_SIZE = Gauge('app_watchlist_items',  'Watchlist size')

MOVIES = [
    {"id":1,  "title":"Inception",          "year":2010, "genre":"Sci-Fi",    "rating":8.8, "duration":"2h 28m", "desc":"A thief enters dreams to steal secrets.",        "thumb":"🎭", "color":"#1a1a2e"},
    {"id":2,  "title":"The Dark Knight",    "year":2008, "genre":"Action",    "rating":9.0, "duration":"2h 32m", "desc":"Batman faces the Joker in Gotham City.",          "thumb":"🦇", "color":"#16213e"},
    {"id":3,  "title":"Interstellar",       "year":2014, "genre":"Sci-Fi",    "rating":8.6, "duration":"2h 49m", "desc":"Astronauts travel through a wormhole.",           "thumb":"🚀", "color":"#0f3460"},
    {"id":4,  "title":"Avengers: Endgame",  "year":2019, "genre":"Action",    "rating":8.4, "duration":"3h 01m", "desc":"Heroes unite to reverse Thanos.",                 "thumb":"⚡", "color":"#533483"},
    {"id":5,  "title":"The Matrix",         "year":1999, "genre":"Sci-Fi",    "rating":8.7, "duration":"2h 16m", "desc":"A hacker discovers reality is a simulation.",     "thumb":"💊", "color":"#1b4332"},
    {"id":6,  "title":"Parasite",           "year":2019, "genre":"Thriller",  "rating":8.5, "duration":"2h 12m", "desc":"A poor family schemes into a wealthy household.", "thumb":"🏠", "color":"#370617"},
    {"id":7,  "title":"Dune",               "year":2021, "genre":"Sci-Fi",    "rating":8.0, "duration":"2h 35m", "desc":"A noble family controls the desert planet.",      "thumb":"🏜", "color":"#7f4f24"},
    {"id":8,  "title":"Oppenheimer",        "year":2023, "genre":"Drama",     "rating":8.5, "duration":"3h 00m", "desc":"The story of the atomic bomb creation.",          "thumb":"💣", "color":"#3a0ca3"},
    {"id":9,  "title":"John Wick",          "year":2014, "genre":"Action",    "rating":7.4, "duration":"1h 41m", "desc":"A retired hitman seeks vengeance.",               "thumb":"🔫", "color":"#212529"},
    {"id":10, "title":"Get Out",            "year":2017, "genre":"Horror",    "rating":7.7, "duration":"1h 44m", "desc":"A man uncovers a disturbing secret.",             "thumb":"👁", "color":"#2d0000"},
    {"id":11, "title":"Joker",              "year":2019, "genre":"Drama",     "rating":8.4, "duration":"2h 02m", "desc":"The origin story of Batman's greatest villain.",  "thumb":"🃏", "color":"#6a0572"},
    {"id":12, "title":"1917",               "year":2019, "genre":"War",       "rating":8.3, "duration":"1h 59m", "desc":"Two soldiers race to deliver a vital message.",   "thumb":"🎖", "color":"#2b2d42"},
    {"id":13, "title":"Whiplash",           "year":2014, "genre":"Drama",     "rating":8.5, "duration":"1h 47m", "desc":"A drummer pursues perfection at any cost.",       "thumb":"🥁", "color":"#3d0000"},
    {"id":14, "title":"Mad Max: Fury Road", "year":2015, "genre":"Action",    "rating":8.1, "duration":"2h 00m", "desc":"A post-apocalyptic road war for survival.",       "thumb":"🚗", "color":"#4a1303"},
    {"id":15, "title":"Arrival",            "year":2016, "genre":"Sci-Fi",    "rating":7.9, "duration":"1h 56m", "desc":"A linguist decodes an alien language.",           "thumb":"🛸", "color":"#005f73"},
    {"id":16, "title":"Hereditary",         "year":2018, "genre":"Horror",    "rating":7.3, "duration":"2h 07m", "desc":"A family unravels dark secrets after a death.",   "thumb":"🕯", "color":"#10002b"},
    {"id":17, "title":"Tenet",              "year":2020, "genre":"Sci-Fi",    "rating":7.3, "duration":"2h 30m", "desc":"A spy manipulates the flow of time.",             "thumb":"⏪", "color":"#023e8a"},
    {"id":18, "title":"The Revenant",       "year":2015, "genre":"Adventure", "rating":8.0, "duration":"2h 36m", "desc":"A frontiersman survives against all odds.",       "thumb":"🐻", "color":"#1b2838"},
]

GENRES = sorted(set(m["genre"] for m in MOVIES))
watchlist = []

STYLE = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#0a0a0a;color:#fff;min-height:100vh}
.nav{position:sticky;top:0;z-index:100;background:rgba(0,0,0,.95);display:flex;align-items:center;gap:28px;padding:0 40px;height:64px;border-bottom:1px solid rgba(255,255,255,.07);backdrop-filter:blur(12px)}
.logo{font-size:22px;font-weight:900;background:linear-gradient(90deg,#e50914,#ff6b35);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-links{display:flex;gap:20px;flex:1}
.nav-links a{color:rgba(255,255,255,.6);text-decoration:none;font-size:14px;font-weight:500}
.nav-links a:hover{color:#fff}
.nav-right{display:flex;align-items:center;gap:14px;margin-left:auto}
.cloud-pill{background:rgba(229,9,20,.12);border:1px solid rgba(229,9,20,.35);color:#ff7070;padding:4px 13px;border-radius:20px;font-size:12px;font-weight:600}
.wl-btn{background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.18);color:#fff;padding:6px 16px;border-radius:20px;text-decoration:none;font-size:13px}
.badge{background:#e50914;color:#fff;border-radius:50%;width:18px;height:18px;font-size:10px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-left:4px}
.hero{position:relative;height:480px;overflow:hidden;background:linear-gradient(135deg,#150005,#0a0a1a,#001510);display:flex;align-items:center;padding:0 60px}
.hero::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 70% 60% at 65% 50%,rgba(229,9,20,.15),transparent 70%)}
.hero-badge{background:rgba(229,9,20,.18);border:1px solid rgba(229,9,20,.45);color:#ff7070;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:600;display:inline-block;margin-bottom:14px}
.hero-title{font-size:54px;font-weight:900;line-height:1.05;margin-bottom:12px;background:linear-gradient(135deg,#fff 55%,rgba(255,255,255,.4));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-sub{font-size:15px;color:rgba(255,255,255,.5);max-width:460px;line-height:1.6;margin-bottom:26px}
.hero-meta{font-size:12px;color:rgba(255,255,255,.3);margin-top:5px}
.actions{display:flex;gap:12px}
.btn-red{background:#e50914;color:#fff;border:none;padding:12px 28px;border-radius:6px;font-size:15px;font-weight:700;cursor:pointer}
.btn-ghost{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.25);padding:12px 24px;border-radius:6px;font-size:15px;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:6px}
.hero-stats{position:absolute;bottom:32px;right:60px;display:flex;gap:28px}
.stat-num{font-size:24px;font-weight:900;color:#e50914}
.stat-lbl{font-size:11px;color:rgba(255,255,255,.35);text-transform:uppercase;letter-spacing:1px}
.search-bar{background:rgba(255,255,255,.02);border-bottom:1px solid rgba(255,255,255,.06);padding:16px 40px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.s-input{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);color:#fff;padding:9px 16px;border-radius:6px;font-size:14px;width:280px;outline:none}
.s-input:focus{border-color:rgba(229,9,20,.5)}
.s-input::placeholder{color:rgba(255,255,255,.25)}
.s-btn{background:#e50914;color:#fff;border:none;padding:9px 18px;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer}
.tags{display:flex;gap:6px;margin-left:14px;flex-wrap:wrap}
.tag{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.55);padding:5px 13px;border-radius:20px;font-size:12px;text-decoration:none}
.tag:hover,.tag.on{background:rgba(229,9,20,.2);border-color:rgba(229,9,20,.4);color:#fff}
.section{padding:26px 40px}
.sec-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.sec-title{font-size:18px;font-weight:700}
.sec-title span{color:#e50914}
.see-all{color:rgba(255,255,255,.35);font-size:13px;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:13px}
.card{border-radius:7px;overflow:hidden;cursor:pointer;position:relative;transition:transform .2s,box-shadow .2s}
.card:hover{transform:scale(1.06);z-index:10;box-shadow:0 16px 50px rgba(0,0,0,.8)}
.thumb{height:230px;display:flex;align-items:center;justify-content:center;font-size:68px;position:relative}
.thumb::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,transparent 38%,rgba(0,0,0,.92) 100%)}
.rating{position:absolute;top:8px;right:8px;z-index:2;background:rgba(0,0,0,.7);color:#ffd700;padding:3px 7px;border-radius:4px;font-size:11px;font-weight:700}
.add-btn{position:absolute;bottom:48px;left:0;right:0;z-index:3;background:rgba(229,9,20,.88);color:#fff;border:none;padding:8px;font-size:12px;font-weight:600;cursor:pointer;opacity:0;transition:opacity .2s}
.card:hover .add-btn{opacity:1}
.card-info{padding:10px;background:rgba(0,0,0,.88)}
.card-title{font-size:13px;font-weight:600;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-meta{display:flex;gap:6px}
.yr{font-size:11px;color:rgba(255,255,255,.35)}
.gn{font-size:11px;color:#e50914;font-weight:600}
.dur{font-size:11px;color:rgba(255,255,255,.25)}
.pg-hdr{padding:36px 40px 0}
.pg-title{font-size:32px;font-weight:900;margin-bottom:6px}
.pg-sub{color:rgba(255,255,255,.35);font-size:14px}
.wl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:13px;padding:20px 40px}
.clear-btn{display:inline-block;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:rgba(255,255,255,.55);padding:6px 16px;border-radius:6px;font-size:13px;text-decoration:none;margin-left:10px}
.clear-btn:hover{background:rgba(229,9,20,.15);border-color:#e50914;color:#fff}
.empty{text-align:center;padding:80px 40px;color:rgba(255,255,255,.25)}
.empty-icon{font-size:64px;margin-bottom:16px}
.empty-ttl{font-size:20px;font-weight:700;margin-bottom:8px;color:rgba(255,255,255,.5)}
.empty-sub{font-size:14px;margin-bottom:24px}
.empty-link{background:#e50914;color:#fff;text-decoration:none;padding:10px 24px;border-radius:6px;font-weight:600}
.footer{border-top:1px solid rgba(255,255,255,.06);padding:24px 40px;display:flex;justify-content:space-between;align-items:center;color:rgba(255,255,255,.25);font-size:12px;margin-top:40px}
.footer-logo{font-size:15px;font-weight:900;background:linear-gradient(90deg,#e50914,#ff6b35);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
</style>"""

def nav(active="home"):
    n = len(watchlist)
    badge = f'<span class="badge">{n}</span>' if n else ""
    return f"""<nav class="nav">
  <div class="logo">StreamCloud</div>
  <div class="nav-links">
    <a href="/">Home</a>
    <a href="/?genre=Action">Action</a>
    <a href="/?genre=Sci-Fi">Sci-Fi</a>
    <a href="/?genre=Drama">Drama</a>
    <a href="/?genre=Horror">Horror</a>
  </div>
  <div class="nav-right">
    <span class="cloud-pill">☁ {CLOUD}</span>
    <a href="/watchlist" class="wl-btn">My List{badge}</a>
  </div>
</nav>"""

def card(m):
    return f"""<div class="card">
  <div class="thumb" style="background:{m['color']}">
    <span style="position:relative;z-index:1">{m['thumb']}</span>
    <div class="rating">⭐ {m['rating']}</div>
  </div>
  <form method="POST" action="/add_to_watchlist" style="margin:0">
    <input type="hidden" name="movie_id" value="{m['id']}">
    <button class="add-btn" type="submit">+ My List</button>
  </form>
  <div class="card-info">
    <div class="card-title">{m['title']}</div>
    <div class="card-meta">
      <span class="yr">{m['year']}</span>
      <span class="gn">{m['genre']}</span>
      <span class="dur">{m['duration']}</span>
    </div>
  </div>
</div>"""

def footer():
    return f"""<div class="footer">
  <span class="footer-logo">StreamCloud</span>
  <span>Multi-Cloud DevOps · AWS Primary + Azure Standby</span>
  <span>☁ Serving from <b style="color:#e50914">{CLOUD}</b></span>
</div>"""

@app.route("/")
def home():
    REQUEST_COUNT.labels(endpoint='/').inc()
    genre  = request.args.get("genre","")
    search = request.args.get("q","")
    movies = MOVIES
    if genre:  movies = [m for m in movies if m["genre"]==genre]
    if search:
        SEARCH_COUNT.inc()
        movies = [m for m in movies if search.lower() in m["title"].lower() or search.lower() in m["genre"].lower()]
    featured  = MOVIES[1]
    cards     = "".join(card(m) for m in movies)
    gtags     = "".join(f'<a href="/?genre={g}" class="tag {"on" if g==genre else ""}">{g}</a>' for g in GENRES)
    sec_title = f"<span>{genre or 'All'}</span> Movies" if (genre or search) else "Popular on <span>StreamCloud</span>"
    count     = f"{len(movies)} movie{'s' if len(movies)!=1 else ''}"
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>StreamCloud</title>{STYLE}</head><body>
{nav()}
<div class="hero"><div>
  <div class="hero-badge">🎬 Featured</div>
  <div class="hero-title">{featured['title']}</div>
  <div class="hero-sub">{featured['desc']}<div class="hero-meta">{featured['year']} · {featured['genre']} · {featured['duration']} · ⭐ {featured['rating']}</div></div>
  <div class="actions">
    <button class="btn-red">▶ Play Now</button>
    <a href="#movies" class="btn-ghost">ℹ More Info</a>
  </div>
</div>
<div class="hero-stats">
  <div><div class="stat-num">{len(MOVIES)}</div><div class="stat-lbl">Movies</div></div>
  <div><div class="stat-num">{len(GENRES)}</div><div class="stat-lbl">Genres</div></div>
  <div><div class="stat-num">{len(watchlist)}</div><div class="stat-lbl">My List</div></div>
</div></div>
<div class="search-bar">
  <form method="GET" action="/" style="display:flex;gap:8px">
    <input class="s-input" type="text" name="q" placeholder="Search movies..." value="{search}">
    <button class="s-btn" type="submit">Search</button>
  </form>
  <div class="tags"><a href="/" class="tag {"on" if not genre else ""}">All</a>{gtags}</div>
</div>
<div class="section" id="movies">
  <div class="sec-hdr">
    <div class="sec-title">{sec_title} <span style="font-size:12px;color:rgba(255,255,255,.25);font-weight:400;margin-left:6px">{count}</span></div>
    <a href="/" class="see-all">Browse All →</a>
  </div>
  <div class="grid">{cards}</div>
</div>
{footer()}</body></html>"""

@app.route("/watchlist")
def watchlist_page():
    REQUEST_COUNT.labels(endpoint='/watchlist').inc()
    if watchlist:
        body = f"""<div class="pg-hdr"><div class="pg-title">My List</div>
<div class="pg-sub">{len(watchlist)} saved <a href="/clear_watchlist" class="clear-btn">Clear All</a></div></div>
<div class="wl-grid">{"".join(card(m) for m in watchlist)}</div>"""
    else:
        body = """<div class="empty"><div class="empty-icon">📭</div>
<div class="empty-ttl">Your list is empty</div>
<div class="empty-sub">Hover a movie and click + My List</div>
<a href="/" class="empty-link">Browse Movies</a></div>"""
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>My List — StreamCloud</title>{STYLE}</head><body>
{nav()}{body}{footer()}</body></html>"""

@app.route("/add_to_watchlist", methods=["POST"])
def add_to_watchlist():
    mid = int(request.form.get("movie_id"))
    movie = next((m for m in MOVIES if m["id"]==mid), None)
    if movie and movie not in watchlist:
        watchlist.append(movie)
        WATCHLIST_SIZE.set(len(watchlist))
    return redirect(url_for("home"))

@app.route("/clear_watchlist")
def clear_watchlist():
    watchlist.clear()
    WATCHLIST_SIZE.set(0)
    return redirect(url_for("watchlist_page"))

@app.route("/health")
def health():
    REQUEST_COUNT.labels(endpoint='/health').inc()
    return jsonify({"status":"healthy","app":"StreamCloud","cloud":CLOUD,
        "uptime_seconds":round(time.time()-START_TIME,2),
        "total_movies":len(MOVIES),"watchlist_count":len(watchlist)}), 200

@app.route("/metrics")
def metrics():
    REQUEST_COUNT.labels(endpoint='/metrics').inc()
    return generate_latest(), 200, {"Content-Type":"text/plain; charset=utf-8"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

Click **"Commit changes"** → click green **"Commit changes"** button. ✅

---

# FILE 2 — `requirements.txt`

Go to `https://github.com/pradeep435/multi-cloud-devops/edit/main/requirements.txt`

Delete everything, paste this:
```
flask==3.0.3
prometheus_client==0.20.0
