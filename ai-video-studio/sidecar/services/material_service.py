"""
Material service - searches and downloads stock videos from Pexels/Pixabay.
"""
import os
import hashlib
import asyncio
from pathlib import Path
from loguru import logger

CACHE_DIR = Path("./cache_videos")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def search_videos(query: str, api_key: str, source: str = "pexels", count: int = 10) -> list[dict]:
    """Search for stock videos."""
    if source == "pexels":
        return await _search_pexels(query, api_key, count)
    elif source == "pixabay":
        return await _search_pixabay(query, api_key, count)
    return []


async def _search_pexels(query: str, api_key: str, count: int) -> list[dict]:
    """Search Pexels for videos."""
    import aiohttp
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": count, "orientation": "portrait"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                logger.error(f"Pexels search failed: {resp.status}")
                return []
            data = await resp.json()
            videos = []
            for item in data.get("video_files", []):
                if item.get("file_type") == "video/mp4":
                    videos.append({
                        "url": item["link"],
                        "width": item.get("width", 0),
                        "height": item.get("height", 0),
                        "duration": item.get("duration", 0),
                        "source": "pexels",
                    })
            return videos[:count]


async def _search_pixabay(query: str, api_key: str, count: int) -> list[dict]:
    """Search Pixabay for videos."""
    import aiohttp
    url = "https://pixabay.com/api/videos/"
    params = {"key": api_key, "q": query, "per_page": count}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logger.error(f"Pixabay search failed: {resp.status}")
                return []
            data = await resp.json()
            videos = []
            for hit in data.get("hits", []):
                video = hit.get("videos", {}).get("medium", {})
                if video.get("url"):
                    videos.append({
                        "url": video["url"],
                        "width": video.get("width", 0),
                        "height": video.get("height", 0),
                        "duration": hit.get("duration", 0),
                        "source": "pixabay",
                    })
            return videos[:count]


async def download_video(url: str) -> str:
    """Download a video file and return local path."""
    import aiohttp
    url_hash = hashlib.md5(url.encode()).hexdigest()
    local_path = CACHE_DIR / f"vid-{url_hash}.mp4"

    if local_path.exists():
        logger.debug(f"Cache hit: {local_path}")
        return str(local_path)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Download failed: {resp.status}")
            with open(local_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    f.write(chunk)

    logger.info(f"Downloaded: {local_path}")
    return str(local_path)


async def download_videos(urls: list[str], max_concurrent: int = 3) -> list[str]:
    """Download multiple videos concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def _download(url: str):
        async with semaphore:
            try:
                path = await download_video(url)
                results.append(path)
            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")

    await asyncio.gather(*[_download(u) for u in urls])
    return results
