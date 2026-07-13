---
name: newsnow
description: "Trending / hot boards — what's hot right now across ~50 platforms via a self-hosted NewsNow instance: Hacker News front page, GitHub trending repos, Product Hunt launches, Weibo/Douyin/Baidu/Toutiao hot searches, Zhihu hot list, Bilibili, and Chinese finance wires (CLS, WallStreetCN, Xueqiu). Ranked title+URL items; use for cross-platform hot-topic detection and China-first tech/finance stories."
keywords: "trending, hot list, hot search, viral, Hacker News, HN front page, GitHub trending, Product Hunt, Weibo, Zhihu, Douyin, Baidu, Toutiao, Bilibili, CLS, WallStreetCN, Xueqiu, China tech news, Chinese social media, finance flash, NewsNow"
routes: "/trending, /trending/{source_id}"
---

# NewsNow (Trending)

What's hot right now across ~50 boards, proxied from a **self-hosted [NewsNow](https://github.com/ourongxing/newsnow)** instance (MIT). Items are ranked title+URL tuples — **rank = 1-based list position, hottest first**. Titles only: fetch the linked article separately if you need content. Many Chinese boards surface China tech/space/AI stories hours-to-days before English-language media.

Unlike every other DataGod source, the upstream here is **infrastructure you run**, not a public third-party API: NewsNow does the actual scraping (guest cookies, reverse-engineered request signing, per-board parsers) and DataGod only proxies it.

## Upstream

- Endpoint used: `GET {NEWSNOW_BASE_URL}/api/s?id=<board>&latest=true`.
- `NEWSNOW_BASE_URL` (required): base URL of your instance. Unset → `/trending/{id}` returns a 502 envelope with `"NEWSNOW_BASE_URL not configured"`.
- Self-host: `ghcr.io/ourongxing/newsnow:<tag>` — **pin a release tag** (their CI publishes images on `v*` tags only; the client's board list matches `v0.0.41`). Minimal env: `HOST=0.0.0.0`, `PORT=4444`, `INIT_TABLE=true`, `ENABLE_CACHE=true`; persist `/usr/app/.data` (SQLite cache).
- Auth: none anywhere. Run the instance **without** the GitHub-OAuth env vars — login-disabled instances honor `latest` for anonymous callers (the public demo doesn't). The scraped platforms need no accounts either (public endpoints, self-bootstrapped guest cookies, reverse-engineered signing). Optional: `PRODUCTHUNT_API_TOKEN` on the instance upgrades Product Hunt from its RSS feed to the GraphQL API (adds vote counts).
- Caching: newsnow caches per board in SQLite — refresh interval 2 min–1 h by board (default 10 min), cache TTL 30 min. DataGod adds no cache layer on top.

## Endpoints

### `GET /trending`

Static list of valid board ids (pinned to the deployed newsnow release; source of truth: `SOURCES` in `app/clients/newsnow.py`).

### `GET /trending/{source_id}`

One board's current hot list. Maps to `newsnow.source(...)` → upstream `/api/s`.

**Params:**
- `source_id` (path, string, required) — a board id from `GET /trending`.
- `latest` (query, boolean, default `true`) — `true` asks newsnow for a fresh upstream fetch; `false` accepts its cache.

**Response `data` (upstream payload, unchanged):**

```json
{
  "status": "success",          // "success" = fresh fetch, "cache" = served from newsnow's cache
  "id": "hackernews",
  "updatedTime": 1783897182262,
  "items": [
    { "id": "48884853", "title": "…", "url": "https://…",
      "extra": { "info": "161 points" } }
  ]
}
```

- `items[i]` rank = `i + 1`. Fields: `title`, `url`, sometimes `mobileUrl`, `pubDate` (flash feeds), `extra.info` (board-specific metric: HN points, GitHub `✰ stars`, Zhihu heat), `extra.hover` (GitHub repo description).
- Invalid board id → upstream 500 → DataGod **502** error envelope.

## Boards (52, newsnow `v0.0.41`)

- **Tech (English):** `hackernews` · `producthunt` · `github-trending-today`
- **Tech (Chinese):** `v2ex-share` · `coolapk` · `ithome` · `solidot` · `sspai` · `juejin` · `aihot` · `36kr-quick` · `36kr-renqi` · `pcbeta-windows11` · `freebuf` · `nowcoder`
- **China social / general:** `zhihu` · `weibo` · `douyin` · `baidu` · `toutiao` · `tieba` · `thepaper` · `ifeng` · `tencent-hot` · `bilibili-hot-search` · `bilibili-hot-video` · `bilibili-ranking` · `kuaishou` · `douban` · `qqvideo-tv-hotsearch` · `iqiyi-hot-ranklist` · `chongbuluo-latest` · `chongbuluo-hot`
- **Finance (CN wires + hot lists):** `wallstreetcn-quick` · `wallstreetcn-news` · `wallstreetcn-hot` · `cls-telegraph` · `cls-depth` · `cls-hot` · `xueqiu-hotstock` · `gelonghui` · `fastbull-express` · `fastbull-news` · `jin10` · `mktnews-flash`
- **World news (Chinese-language):** `zaobao` · `cankaoxiaoxi` · `sputniknewscn` · `kaopu`
- **Sports / other:** `hupu` · `dongqiudi` · `steam`

Two flavors: **hottest** boards are ranked lists (weibo, zhihu, hackernews); **realtime** boards are newest-first flash feeds (cls-telegraph, jin10, mktnews-flash, gelonghui — 2–5 min cadence).

## Quirks

- **Board ids track the pinned release.** Bumping the newsnow image can add/remove boards — update `SOURCES` in `app/clients/newsnow.py` and this doc together (upstream catalog: `shared/pre-sources.ts` at the pinned tag).
- On a **login-enabled** instance, anonymous `latest=true` is silently downgraded to cache — keep login disabled.
- Some boards are unavailable when newsnow itself is hosted on Cloudflare Pages (`kuaishou`, `bilibili-hot-video`, `bilibili-ranking`, `36kr-*`); on a Node/Docker self-host they all work.
- Upstream scrapes are unofficial: a platform reshuffling markup breaks that board until the next newsnow release — one more reason to consume newsnow as a maintained dependency and bump deliberately.
- Editorial note: `sputniknewscn` is Russian state media; `cankaoxiaoxi`/`zaobao` are state-adjacent digests. The CN finance wires (CLS, WallStreetCN) are the most factual-dense boards.
