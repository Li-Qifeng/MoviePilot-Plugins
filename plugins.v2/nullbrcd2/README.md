# NullbrCD2 插件开发文档

## 1. 项目概述
本插件旨在集成 `Nullbr` 资源站 API 与 `CloudDrive2` (CD2) API，为 MoviePilot 提供从资源搜索到 115 网盘转存、离线下载及自动入库的一站式解决方案。

### 参考文档
*   [Nullbr API Reference](api_nullbr.md)
*   [CloudDrive2 API Reference](api_cd2.md)
*   [MoviePilot Plugin API Reference](api_moviepilot.md)

### 核心功能
1.  **资源搜索**: 调用 Nullbr API 搜索资源，支持获取 115 分享链接、磁力链接 (Magnet)、Ed2k、M3u8。
2.  **CD2 联动**:
    *   115 分享链接转存 (导入到指定 CD2 挂载路径)。
    *   115 离线下载 (Magnet/Ed2k 提交到 115 离线任务)。
    *   Ed2k 链接自动转换为 Magnet (如果 Nullbr 未直接提供)。
3.  **下载器集成**: 调用 MoviePilot 内部下载器接口 (作为 fallback 或特定格式处理)。
4.  **交互与通知**:
    *   支持微信/Telegram 指令 `/nullbr <关键词>` 进行交互式搜索与下载。
    *   监控 115 离线任务状态，任务完成时通过 MoviePilot 通知通道推送消息。

## 2. 技术架构

### 2.1 目录结构
```text
MoviePilot-Plugins/plugins.v2/nullbrcd2/
├── __init__.py          # 插件主入口 (Plugin Class)
├── api_nullbr.py        # Nullbr API 客户端封装
├── api_cd2.py           # CloudDrive2 API 客户端封装
├── README.md            # 开发文档
└── TODO.md              # 开发计划清单
```

### 2.2 核心类设计

#### `NullbrCd2(app.plugins._PluginBase)`
*   继承自 MoviePilot V2 插件基类。
*   负责配置加载、服务注册、命令注册及事件监听。

#### `NullbrClient`
*   **Endpoint**: `https://nullbr.online/api`
*   **Auth**: Cookie (`_streamlit_xsrf`)
*   **Methods**:
    *   `search(keyword: str) -> List[Resource]`
    *   `parse_detail(url: str) -> Detail`

#### `CloudDrive2Client`
*   **Endpoint**: 用户配置 (e.g., `http://localhost:19798`)
*   **Auth**: 用户名/密码 -> Bearer Token
*   **Methods**:
    *   `login()`
    *   `transfer_115_share(share_link: str, target_path: str)`
    *   `add_offline_task(magnet_url: str)`
    *   `get_task_status(task_id: str)`

## 3. 配置设计 (Schema)
用户需要在插件配置页填写的参数：

| 参数 Key | 类型 | 说明 | 默认值 |
| :--- | :--- | :--- | :--- |
| `nullbr_cookie` | String | Nullbr 站点 Cookie (必需) | `_streamlit_xsrf=...` |
| `cd2_host` | String | CloudDrive2 地址 | `http://localhost:19798` |
| `cd2_user` | String | CD2 用户名 | `admin` |
| `cd2_password` | String | CD2 密码 | - |
| `cd2_115_mount_path` | String | CD2 中 115 网盘的挂载路径/存储路径 | `/115` |
| `resource_priority` | String | 资源优先级 (逗号分隔) | `115,magnet,ed2k,m3u8` |
| `download_mode` | Select | 默认下载行为 | `115` |
| `download_mode_options` | - | 选项: `115` (网盘优先), `MoviePilot` (下载器优先) | - |

> **下载模式说明**:
> *   **115**:
>     *   **115 分享**: 直接调用 CD2 转存。
>     *   **Magnet**: 调用 CD2 添加离线下载。
>     *   **Ed2k**: 尝试转 Magnet 后添加离线下载。
>     *   **M3u8**: 不支持 (或仅返回链接)。
> *   **MoviePilot**:
>     *   所有资源类型尝试调用 MP 下载器接口 (DownloadChain)。

## 4. 业务流程

### 4.1 搜索与下载流程
1.  用户发送指令 `/nullbr 狂飙`。
2.  `NullbrCd2` 插件捕获指令，调用 `NullbrClient.search("狂飙")`。
3.  **结果排序**: 根据 `resource_priority` 对结果中的资源链接进行排序。
4.  返回结果列表，格式化为消息卡片回复用户（显示“下载”按钮）。
5.  用户点击按钮（触发 `EventType.PluginAction`）。
6.  插件根据 `download_mode` 配置：
    *   **模式 115**:
        *   若资源为 **115 分享**: `CloudDrive2Client.transfer_115_share(...)`
        *   若资源为 **Magnet**: `CloudDrive2Client.add_offline_task(...)`
        *   若资源为 **Ed2k**: (转换) -> `add_offline_task`
    *   **模式 MoviePilot**:
        *   调用 `DownloaderHelper.add_download_task(...)`

### 4.2 任务监控流程 (Service)
... (保持不变)

## 5. 依赖说明
... (保持不变)

## 6. API 客户端设计

### `NullbrClient`
*   基于 `requests` 封装。
*   **Search**: `GET https://nullbr.online/api?title={keyword}` (需携带 Cookie)。
*   **Parse**: 解析 HTML/JSON 提取资源列表。

### `CloudDrive2Client`
*   基于 `requests` 封装。
*   **Auth**: `/api/GetToken` 获取 Bearer Token。
*   **Actions**:
    *   `transfer_115_share(url, path)` -> `/api/AddSharedLink`
    *   `add_offline_task(url, path)` -> `/api/AddOfflineFiles`
