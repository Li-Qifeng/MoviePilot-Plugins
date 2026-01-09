from typing import List, Tuple, Dict, Any, Optional
from apscheduler.triggers.cron import CronTrigger
from app.plugins import _PluginBase
from app.core.event import eventmanager, EventType, Event
from app.helper.message import MessageChannel
from app.helper.downloader import DownloaderHelper
from app.helper.notification import NotificationHelper
from app.log import logger
from .api_nullbr import NullbrClient
from .api_cd2 import CloudDrive2Client

class NullbrCd2(_PluginBase):
    # 插件元数据
    plugin_name = "NullbrCD2"
    plugin_desc = "Nullbr资源搜索与CloudDrive2联动插件"
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/main/icons/115.png"
    plugin_version = "1.0"
    plugin_author = "Developer"
    plugin_config_prefix = "nullbrcd2_"
    plugin_order = 10
    auth_level = 1

    # 私有属性
    _enabled = False
    _config = {}
    _nullbr_client: NullbrClient = None
    _cd2_client: CloudDrive2Client = None
    _last_tasks = set() # 记录上次的完成任务ID，避免重复通知

    def init_plugin(self, config: dict = None):
        """
        初始化插件
        """
        self._config = config or {}
        self._enabled = self._config.get("enabled", False)
        
        self.nullbr_cookie = self._config.get("nullbr_cookie", "")
        self.api_key = self._config.get("api_key", "")
        self.app_id = self._config.get("app_id", "")
        self.cd2_host = self._config.get("cd2_host", "http://localhost:19798")
        self.cd2_user = self._config.get("cd2_user", "admin")
        self.cd2_password = self._config.get("cd2_password", "")
        self.cd2_115_mount_path = self._config.get("cd2_115_mount_path", "/115")
        self.resource_priority = self._config.get("resource_priority", "115,magnet,ed2k,m3u8")
        self.download_mode = self._config.get("download_mode", "115")

        if self._enabled:
            logger.info(f"Loading NullbrCD2 plugin... Host: {self.cd2_host}")
            self._nullbr_client = NullbrClient(self.app_id, self.api_key, self.nullbr_cookie)
            self._cd2_client = CloudDrive2Client(self.cd2_host, self.cd2_user, self.cd2_password)

    def get_state(self) -> bool:
        return self._enabled

    def stop_service(self):
        self._enabled = False

    def get_command(self) -> List[Dict[str, Any]]:
        """
        注册远程命令
        """
        return [{
            "cmd": "/nullbr",
            "event": EventType.PluginAction,
            "desc": "Nullbr 资源搜索",
            "category": "资源搜索",
            "data": {
                "action": "nullbr_search"
            }
        }]

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册定时服务
        """
        if not self._enabled:
            return []
        return [{
            "id": "nullbrcd2_monitor",
            "name": "NullbrCD2 任务监控",
            "trigger": CronTrigger.from_crontab("*/5 * * * *"),
            "func": self.sync_task,
            "kwargs": {}
        }]

    def sync_task(self):
        """
        定时监控任务状态
        """
        if not self._enabled or not self._cd2_client:
            return
        
        # 监控离线下载任务
        logger.debug("NullbrCD2 checking offline tasks...")
        offline_tasks = self._cd2_client.get_offline_tasks()
        if not offline_tasks:
            return

        current_completed = set()
        
        for task in offline_tasks:
            task_id = task.get("id") or task.get("name")
            status = task.get("status")
            
            # 假设 status 为 "Success" 或 2 代表完成，需根据实际情况调整
            if status == "Success" or status == 2: 
                current_completed.add(task_id)
                if task_id not in self._last_tasks:
                    # 新完成的任务
                    logger.info(f"NullbrCD2 task completed: {task.get('name')}")
                    NotificationHelper().send_message(
                        title="下载完成",
                        text=f"离线任务已完成：{task.get('name')}"
                    )
        
        # 更新缓存
        self._last_tasks = current_completed

    @eventmanager.register(EventType.PluginAction)
    def command_event(self, event: Event):
        """
        监听插件命令事件
        """
        if not self._enabled:
            return
            
        event_data = event.event_data
        action = event_data.get("action")
        
        if action == "nullbr_search":
            # 处理搜索命令
            message = event_data.get("message") # 用户发送的消息内容
            if message:
                # 提取关键词，移除命令本身
                keyword = message.replace("/nullbr", "").strip()
                if not keyword:
                    return
                
                channel = event_data.get("channel")
                user_id = event_data.get("user")
                
                logger.info(f"NullbrCD2 searching for: {keyword}")
                self.post_message(
                    channel=channel,
                    title="🔍 正在搜索...",
                    text=f"关键词: {keyword}",
                    userid=user_id
                )
                
                self._search_and_reply(keyword, channel, user_id)

    def _search_and_reply(self, keyword: str, channel: MessageChannel, user_id: str):
        """
        执行搜索并回复
        """
        if not self._nullbr_client:
            return

        results = self._nullbr_client.search(keyword)
        if not results:
            self.post_message(channel, title="搜索结果", text="未找到相关资源", userid=user_id)
            return

        # 仅展示前 5 条
        for item in results[:5]:
            title = item.get("title")
            overview = item.get("overview", "")[:100] + "..."
            poster = item.get("poster")
            if poster and not poster.startswith("http"):
                poster = f"https://image.tmdb.org/t/p/w500{poster}"
            
            tmdb_id = item.get("tmdbid")
            media_type = item.get("media_type")
            
            # 构建按钮
            buttons = []
            
            # 115 按钮
            if item.get("115-flg") == 1:
                buttons.append({
                    "text": "💾 115转存",
                    "callback_data": f"[PLUGIN]NullbrCd2|dl:115:{media_type}:{tmdb_id}"
                })
            
            # 磁力 按钮
            if item.get("magnet-flg") == 1:
                buttons.append({
                    "text": "🧲 磁力下载",
                    "callback_data": f"[PLUGIN]NullbrCd2|dl:mag:{media_type}:{tmdb_id}"
                })

            if buttons:
                # 每行2个按钮
                formatted_buttons = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
                
                self.post_message(
                    channel=channel,
                    title=f"🎬 {title}",
                    text=overview,
                    image=poster,
                    userid=user_id,
                    buttons=formatted_buttons
                )

    @eventmanager.register(EventType.MessageAction)
    def message_event(self, event: Event):
        """
        监听消息交互事件
        """
        if not self._enabled:
            return

        event_data = event.event_data
        if not event_data:
            return

        plugin_id = event_data.get("plugin_id")
        if plugin_id != self.__class__.__name__:
            return

        callback_data = event_data.get("text", "")
        channel = event_data.get("channel")
        user_id = event_data.get("userid")

        # callback_data format: dl:{type}:{media_type}:{tmdb_id}
        if callback_data.startswith("dl:"):
            try:
                _, dl_type, media_type, tmdb_id = callback_data.split(":")
                tmdb_id = int(tmdb_id)
                
                logger.info(f"NullbrCD2 handling download action: {dl_type} for {media_type} {tmdb_id}")
                self.post_message(channel, title="⏳ 处理中", text="正在请求资源...", userid=user_id)
                
                if dl_type == "115":
                    self._handle_download_115(channel, user_id, media_type, tmdb_id)
                elif dl_type == "mag":
                    self._handle_download_magnet(channel, user_id, media_type, tmdb_id)
            except Exception as e:
                logger.error(f"NullbrCD2 action failed: {e}")
                self.post_message(channel, title="❌ 错误", text=f"操作处理失败: {str(e)}", userid=user_id)

    def _handle_download_115(self, channel, user_id, media_type, tmdb_id):
        """
        处理 115 转存
        """
        resources = []
        if media_type == "movie":
            resources = self._nullbr_client.get_movie_115(tmdb_id)
        elif media_type == "tv":
            resources = self._nullbr_client.get_tv_115(tmdb_id)
        
        if not resources:
            self.post_message(channel, title="❌ 失败", text="未获取到 115 资源链接", userid=user_id)
            return

        # 优先选择第一个资源
        resource = resources[0]
        share_link = resource.get("share_link")
        
        password = ""
        if "password=" in share_link:
            import urllib.parse
            parsed = urllib.parse.urlparse(share_link)
            qs = urllib.parse.parse_qs(parsed.query)
            password = qs.get("password", [""])[0]

        # 调用 CD2 转存
        success = self._cd2_client.transfer_115_share(share_link, self.cd2_115_mount_path, password)
        
        if success:
            logger.info(f"NullbrCD2 transfer success: {resource.get('title')}")
            self.post_message(channel, title="✅ 转存成功", text=f"任务已提交到 CloudDrive2\n{resource.get('title')}", userid=user_id)
        else:
            self.post_message(channel, title="❌ 转存失败", text="CloudDrive2 接口调用失败，请检查日志", userid=user_id)

    def _handle_download_magnet(self, channel, user_id, media_type, tmdb_id):
        """
        处理磁力离线
        """
        resources = []
        if media_type == "movie":
            resources = self._nullbr_client.get_movie_magnet(tmdb_id)
        elif media_type == "tv":
            # 对于剧集，通常 magnet 很多，这里简化处理：尝试获取第一季的 magnet
            # TODO: 更好的交互应该是列出季让用户选，或者默认下载 S01
            resources = self._nullbr_client.get_tv_season_magnet(tmdb_id, 1)
        
        if not resources:
            self.post_message(channel, title="❌ 失败", text="未获取到磁力资源", userid=user_id)
            return

        resource = resources[0]
        magnet_link = resource.get("magnet")
        
        if self.download_mode == "MoviePilot":
            # 使用 MP 下载器
            try:
                DownloaderHelper().add_download_task(
                    magnet_link
                )
                logger.info(f"NullbrCD2 added to MP downloader: {resource.get('name')}")
                self.post_message(channel, title="✅ 下载添加成功", text=f"任务已提交到 MoviePilot 下载器\n{resource.get('name')}", userid=user_id)
            except Exception as e:
                logger.error(f"NullbrCD2 MP download failed: {e}")
                self.post_message(channel, title="❌ 下载添加失败", text=f"MoviePilot 下载器调用失败: {str(e)}", userid=user_id)
        else:
            # 默认使用 CD2 离线
            success = self._cd2_client.add_offline_task(magnet_link, self.cd2_115_mount_path)
            
            if success:
                logger.info(f"NullbrCD2 offline task added: {resource.get('name')}")
                self.post_message(channel, title="✅ 离线添加成功", text=f"离线任务已提交到 CloudDrive2\n{resource.get('name')}", userid=user_id)
            else:
                self.post_message(channel, title="❌ 离线添加失败", text="CloudDrive2 接口调用失败，请检查日志", userid=user_id)

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        获取插件配置表单
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VSwitch',
                        'props': {
                            'model': 'enabled',
                            'label': '启用插件'
                        }
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 12},
                                'content': [
                                    {'component': 'div', 'text': 'Nullbr 配置', 'class': 'text-h6 mt-4 mb-2'}
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 4},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'app_id',
                                            'label': 'App ID',
                                            'placeholder': 'Nullbr App ID'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 8},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_key',
                                            'label': 'API Key',
                                            'placeholder': 'Nullbr User API Key'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 12},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'nullbr_cookie',
                                            'label': 'Cookie (Legacy)',
                                            'placeholder': '_streamlit_xsrf=...',
                                            'hint': '如果API调用失败，可能需要提供网页版Cookie'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 12},
                                'content': [
                                    {'component': 'div', 'text': 'CloudDrive2 配置', 'class': 'text-h6 mt-4 mb-2'}
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cd2_host',
                                            'label': 'CD2 地址',
                                            'placeholder': 'http://localhost:19798'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cd2_115_mount_path',
                                            'label': '115 挂载路径',
                                            'placeholder': '/115'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cd2_user',
                                            'label': '用户名',
                                            'placeholder': 'admin'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cd2_password',
                                            'label': '密码',
                                            'type': 'password'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 12},
                                'content': [
                                    {'component': 'div', 'text': '高级设置', 'class': 'text-h6 mt-4 mb-2'}
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'resource_priority',
                                            'label': '资源优先级',
                                            'placeholder': '115,magnet,ed2k,m3u8',
                                            'hint': '使用逗号分隔，排在前面的优先展示/下载'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 6},
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'download_mode',
                                            'label': '默认下载行为',
                                            'items': [
                                                {'title': '115 网盘 (CD2)', 'value': '115'},
                                                {'title': 'MoviePilot 下载器', 'value': 'MoviePilot'}
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "app_id": "",
            "api_key": "",
            "nullbr_cookie": "",
            "cd2_host": "http://localhost:19798",
            "cd2_user": "admin",
            "cd2_password": "",
            "cd2_115_mount_path": "/115",
            "resource_priority": "115,magnet,ed2k,m3u8",
            "download_mode": "115"
        }

    def get_page(self) -> List[dict]:
        """
        插件详情页面
        """
        return [
            {
                'component': 'div',
                'text': 'NullbrCD2 插件已安装',
                'class': 'text-h5 text-center mt-4'
            },
            {
                'component': 'div',
                'text': '请在配置页填写 Nullbr 和 CloudDrive2 的连接信息。',
                'class': 'text-body-1 text-center mt-2'
            }
        ]
