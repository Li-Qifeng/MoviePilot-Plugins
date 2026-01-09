import requests
from typing import Dict, Any, Optional
from app.log import logger
import json

class CloudDrive2Client:
    def __init__(self, host: str, username: str = None, password: str = None):
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()

    def login(self) -> bool:
        """
        登录获取 Token
        """
        if not self.username or not self.password:
            logger.warning("CloudDrive2 username or password not provided.")
            return False

        url = f"{self.host}/api/GetToken"
        payload = {
            "userName": self.username,
            "password": self.password
        }
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                self.token = data.get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True
            else:
                logger.error(f"CloudDrive2 login failed: {data.get('errorMessage')}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"CloudDrive2 login connection error: {e}")
            return False

    def _ensure_token(self):
        """
        确保有 Token，如果没有则尝试登录
        """
        if not self.token:
            self.login()

    def transfer_115_share(self, share_link: str, to_folder: str, password: str = "") -> bool:
        """
        转存 115 分享链接
        :param share_link: 分享链接
        :param to_folder: 目标文件夹路径
        :param password: 分享密码 (如有)
        """
        self._ensure_token()
        url = f"{self.host}/api/AddSharedLink"
        payload = {
            "sharedLinkUrl": share_link,
            "sharedPassword": password,
            "toFolder": to_folder
        }
        try:
            response = self.session.post(url, json=payload, timeout=20)
            # CD2 成功通常返回空 200 OK 或 JSON success=True
            if response.status_code == 200:
                # 有些版本可能返回 JSON，有些可能只是 Empty
                if response.content:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and not data.get("success", True):
                             logger.error(f"CloudDrive2 transfer failed: {data.get('errorMessage')}")
                             return False
                    except json.JSONDecodeError:
                        pass # 内容不是 JSON，但状态码是 200，假设成功
                return True
            else:
                logger.error(f"CloudDrive2 transfer request failed with status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"CloudDrive2 transfer error: {e}")
            return False

    def get_transfer_tasks(self) -> list:
        """
        获取传输任务列表
        """
        self._ensure_token()
        url = f"{self.host}/api/GetUploadFileList"
        payload = {
            "getAll": False,
            "itemsPerPage": 100,
            "pageNumber": 0,
            "filter": ""
        }
        try:
            response = self.session.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("uploadFiles", [])
            return []
        except Exception as e:
            logger.error(f"CloudDrive2 get transfer tasks error: {e}")
            return []

    def get_offline_tasks(self) -> list:
        """
        获取离线下载任务列表
        """
        self._ensure_token()
        url = f"{self.host}/api/ListAllOfflineFiles"
        payload = {
            "page": 0
        }
        try:
            response = self.session.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("offlineFiles", [])
            return []
        except Exception as e:
            logger.error(f"CloudDrive2 get offline tasks error: {e}")
            return []
