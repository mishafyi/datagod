"""NewsNow — ~50 trending/hot boards (Hacker News, GitHub, Product Hunt, Weibo, …) via a self-hosted instance."""

from . import UpstreamJSON, safe_get
from ..config import cfg

# Board ids valid for the pinned release (ghcr.io/ourongxing/newsnow:v0.0.41) — from
# https://github.com/ourongxing/newsnow/blob/v0.0.41/shared/pre-sources.ts with
# `disable: true` entries (linuxdo, ghxi, smzdm, pcbeta-windows) dropped.
# Rank = item position in the returned list; `extra.info` carries per-board
# metrics where the board has them (HN points, GitHub stars, Zhihu heat).
SOURCES = (
    # Tech / dev (English + Chinese)
    "hackernews", "producthunt", "github-trending-today",
    "v2ex-share", "coolapk", "ithome", "solidot", "sspai", "juejin", "aihot",
    "36kr-quick", "36kr-renqi", "pcbeta-windows11", "freebuf", "nowcoder",
    # China social / general hot lists
    "zhihu", "weibo", "douyin", "baidu", "toutiao", "tieba", "thepaper",
    "ifeng", "tencent-hot", "bilibili-hot-search", "bilibili-hot-video",
    "bilibili-ranking", "kuaishou", "douban", "qqvideo-tv-hotsearch",
    "iqiyi-hot-ranklist", "chongbuluo-latest", "chongbuluo-hot",
    # Finance (CN market wires + hot lists)
    "wallstreetcn-quick", "wallstreetcn-news", "wallstreetcn-hot",
    "cls-telegraph", "cls-depth", "cls-hot", "xueqiu-hotstock", "gelonghui",
    "fastbull-express", "fastbull-news", "jin10", "mktnews-flash",
    # World news (Chinese-language)
    "zaobao", "cankaoxiaoxi", "sputniknewscn", "kaopu",
    # Sports / other
    "hupu", "dongqiudi", "steam",
)


async def source(source_id: str, latest: bool = True) -> UpstreamJSON:
    """One board: {status, updatedTime, items: [{title, url, extra?}, …]}.

    `latest=True` asks newsnow for a fresh upstream fetch (honored because the
    self-hosted instance runs with login disabled); `latest=False` accepts its
    cache (per-board interval 2 min–1 h, TTL 30 min).
    """
    if not cfg.NEWSNOW_BASE_URL:
        return {"error": True, "source": "newsnow", "upstream_status": 0,
                "message": "NEWSNOW_BASE_URL not configured"}
    params = {"id": source_id}
    if latest:
        params["latest"] = "true"
    return await safe_get(f"{cfg.NEWSNOW_BASE_URL}/api/s", "newsnow", params=params)
