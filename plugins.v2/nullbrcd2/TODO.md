# NullbrCD2 插件开发 Todo List

## 第一阶段：基础框架与 API 验证
- [x] **创建插件目录** (`MoviePilot-Plugins/plugins.v2/nullbrcd2`)
- [x] **生成 API 文档** (`api_nullbr.md`, `api_cd2.md`, `api_moviepilot.md`)
- [x] **创建 `__init__.py`**
    - [x] 定义 `NullbrCd2` 类，继承 `_PluginBase`。
    - [x] 配置元数据 (Icon, Version, Author)。
- [x] **实现配置页面 (`get_form`)**
    - [x] 输入: `nullbr_cookie`, `api_key` (新增), `app_id` (新增)。
    - [x] 输入: `cd2_host`, `cd2_user`, `cd2_password`, `cd2_115_mount_path`。
    - [x] 选项: `resource_priority` (资源优先级排序)。
    - [x] 选项: `download_mode` (115模式 / MP模式)。

## 第二阶段：API 客户端实现
- [x] **`NullbrClient` (api_nullbr.py)**
    - [x] 实现 `requests` Session 管理 (Cookie, Headers)。
    - [x] 实现 `search(keyword)`: 尝试调用 `/search` 或模拟页面搜索。
    - [x] *注*: 若 API 仅限页面交互，需实现 HTML 解析或 WebSocket 模拟 (高难度，优先尝试 API)。
- [x] **`CloudDrive2Client` (api_cd2.py)**
    - [x] 实现 `login()`: 获取 Bearer Token。
    - [x] 实现 `transfer_115(link, folder)`: 调用 `/api/AddSharedLink`。
    - [x] 实现 `add_offline(url, folder)`: 调用 `/api/AddOfflineFiles`。
    - [x] 实现 `get_tasks()`: 监控进度。

## 第三阶段：业务逻辑与交互
- [x] **命令处理 (`get_command`)**
    - [x] 注册 `/nullbr`。
    - [x] 实现搜索逻辑：调用 `NullbrClient` -> 格式化结果。
    - [x] 实现结果卡片：包含 115/Magnet/Ed2k 按钮。
- [x] **下载调度**
    - [x] **115 模式**:
        - [x] 分享链接 -> `transfer_115`。
        - [x] 磁力/Ed2k -> `add_offline` (Ed2k 需尝试转 Magnet)。
    - [x] **MP 模式**:
        - [x] 调用 `DownloaderHelper`。

## 第四阶段：监控与通知
- [x] **定时服务 (`get_service`)**
    - [x] 轮询 CD2 任务状态。
    - [x] 任务完成 -> `NotificationHelper` 推送。
- [x] **测试与优化**
    - [x] 异常处理 (Cookie 失效, CD2 断连)。