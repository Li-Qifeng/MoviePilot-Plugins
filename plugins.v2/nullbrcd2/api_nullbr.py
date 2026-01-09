import requests
from typing import List, Dict, Any, Optional
from app.log import logger

class NullbrClient:
    BASE_URL = "https://api.nullbr.eu.org"

    def __init__(self, app_id: str, api_key: str, cookie: str = None):
        self.app_id = app_id
        self.api_key = api_key
        self.cookie = cookie
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MoviePilot/NullbrCD2",
            "X-APP-ID": self.app_id,
            "X-API-KEY": self.api_key
        })
        if self.cookie:
            self.session.headers.update({"Cookie": self.cookie})

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Nullbr API request failed: {e}")
            return None

    def search(self, keyword: str, page: int = 1) -> List[Dict[str, Any]]:
        """
        搜索资源
        :param keyword: 关键词
        :param page: 页码
        :return: 搜索结果列表
        """
        data = self._request("GET", "/search", params={"query": keyword, "page": page})
        if data and "items" in data:
            return data["items"]
        return []

    def get_movie_115(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """
        获取电影 115 资源
        """
        data = self._request("GET", f"/movie/{tmdb_id}/115")
        return data.get("115", []) if data else []

    def get_movie_magnet(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """
        获取电影磁力资源
        """
        data = self._request("GET", f"/movie/{tmdb_id}/magnet")
        return data.get("magnet", []) if data else []
    
    def get_movie_ed2k(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """
        获取电影 Ed2k 资源
        """
        data = self._request("GET", f"/movie/{tmdb_id}/ed2k")
        return data.get("ed2k", []) if data else []

    def get_tv_115(self, tmdb_id: int) -> List[Dict[str, Any]]:
        """
        获取剧集 115 资源 (通常包含全季)
        """
        data = self._request("GET", f"/tv/{tmdb_id}/115")
        return data.get("115", []) if data else []

    def get_tv_season_magnet(self, tmdb_id: int, season: int) -> List[Dict[str, Any]]:
        """
        获取剧集单季磁力
        """
        data = self._request("GET", f"/tv/{tmdb_id}/season/{season}/magnet")
        return data.get("magnet", []) if data else []
