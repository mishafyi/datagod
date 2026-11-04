---
name: trending
description: "What's trending right now (self-hosted NewsNow, ~50 boards) — Hacker News, Product Hunt, GitHub trending, V2EX, plus Chinese hot lists (Weibo, Zhihu, Douyin, Baidu, Bilibili, Toutiao) and CN finance wires (Wallstreetcn, CLS, Xueqiu). Ranked titles and URLs. Use for current tech, social and news buzz."
keywords: "trending, hot list, Hacker News, Product Hunt, GitHub trending, Weibo, Zhihu, Douyin, Baidu, Bilibili, Toutiao, news, social media, buzz, viral, NewsNow"
routes: "/trending, /trending/{source_id}"
---

# Trending — NewsNow (self-hosted)

~50 trending / hot boards — Hacker News, Product Hunt, GitHub trending, V2EX,
Weibo, Zhihu, Douyin, Baidu, Bilibili, Toutiao, CN finance wires (Wallstreetcn,
CLS, Xueqiu) and more — served by a **self-hosted** NewsNow instance
(github.com/ourongxing/newsnow), image pinned to
`ghcr.io/ourongxing/newsnow:v0.0.41`. DataGod reads its `/api/s?id=` endpoint.
Client: `app/clients/newsnow.py`.

## Configuration

`NEWSNOW_BASE_URL` — the instance's base URL, e.g. the Coolify-internal
`http://newsnow:4444`. Unset → every `/trending/{source_id}` call answers an
error envelope ("NEWSNOW_BASE_URL not configured", HTTP 502).

## Endpoints

### `GET /trending`

The board ids `/trending/{source_id}` serves: `{sources: [...]}` — a static list
taken from the pinned release's `shared/pre-sources.ts` with its
`disable: true` entries removed.

### `GET /trending/{source_id}`

One board, the upstream JSON unchanged:
`{status, updatedTime, items: [{title, url, extra?}]}`. **Rank is the item's
position.** `extra.info` carries board metrics where the board has them (HN
points, GitHub stars, Zhihu heat).
**Params:** `latest` (default `true`) asks NewsNow for a fresh upstream fetch —
honored because the instance runs with login disabled; `latest=false` accepts
its cache (per-board refresh interval 2 min–1 h, TTL 30 min).

## Quirks & notes

- Board ids are valid **for the pinned release only**. When upgrading the
  image, refresh `SOURCES` in `app/clients/newsnow.py` from that release's
  `shared/pre-sources.ts`.
- An id outside the list is still forwarded; NewsNow answers it with an error.
