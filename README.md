# qq-bot-notifier

内网 QQ 群机器人通知转发服务。Jenkins 或其他系统只需要 POST 一段简单 JSON，本服务会把 `@leaf`、`@monster_tester` 这类目标展开成 QQ 消息段，再通过 OneBot v11 HTTP 接口交给 [SnowLuma](https://github.com/SnowLuma/SnowLuma) 发送到 QQ 群或私聊。

> 本项目只负责“通知内容 → OneBot 消息”的转换和转发，**不负责 QQ 登录，也不实现 QQ 协议**。QQ 登录和 OneBot 接口由上游 [SnowLuma](https://github.com/SnowLuma/SnowLuma) 提供。

## 功能

- `POST /notify`：接收 Jenkins 通知，按项目找到 QQ 群并发送。
- `POST /private-message`：向指定 QQ 号发送私聊文本。
- 支持 `@用户名` 和 `@通知组`，自动展开、按 QQ 号去重。
- 网页管理用户、通知组、项目群号，并查看推送记录。
- 缓存接收到的消息，支持网页查看、复制和清理。
- 发送给 OneBot 的 payload 会落盘到 JSONL，方便排错。

## 工作方式

```text
Jenkins / 任意 HTTP 客户端
        │  POST /notify  {project, title, text, extra}
        ▼
qq-bot-notifier  (FastAPI, 默认 :7848)
        │  POST /send_group_msg  (OneBot v11 HTTP)
        ▼
SnowLuma  (QQ 协议端, 默认 :3000)
        │
        ▼
QQ 群 / QQ 私聊
```

## 上游 SnowLuma 与前置条件

使用本服务前，需要先准备一个已经登录 QQ 的 SnowLuma 实例，并开启 OneBot v11 HTTP 服务。

| 资源 | 链接 |
| --- | --- |
| SnowLuma 项目主页 | <https://github.com/SnowLuma/SnowLuma> |
| SnowLuma 中文文档 | <https://snowluma.github.io/zh/> |
| **SnowLuma Docker 部署文档** | <https://snowluma.github.io/zh/docs/guide/deploy/docker> |
| SnowLuma Docker Framework | <https://github.com/SnowLuma/SnowLuma.Docker.Framework> |
| SnowLuma Docker 镜像 | <https://hub.docker.com/r/motricseven7/snowluma> |
| OneBot v11 标准 | <https://github.com/botuniverse/onebot-11> |
| NapCat（可选，另一种 OneBot 实现） | <https://github.com/NapNeko/NapCatQQ> |

SnowLuma Docker 部署后通常涉及这些端口：

- `5099`：SnowLuma WebUI，用来登录 QQ、配置 OneBot。
- `3000`：OneBot HTTP，本服务默认调用的地址。
- `3001`：OneBot WebSocket。
- `6081`：noVNC（需要看容器内 QQ 界面时使用）。

在 SnowLuma 中开启 OneBot HTTP 服务后，把地址填到本服务的 `qq_bot.url`，例如：

```text
http://<snowluma-host>:3000/send_group_msg
```

如果 SnowLuma 配置了 access token，把同一个 token 填到本服务的 `QQ_BOT_TOKEN`。

**环境要求：**

- Python 3.11+
- 能访问 SnowLuma 的 OneBot HTTP 端口（默认 `3000`）
- 本服务默认监听 `7848`

## 5 分钟快速开始

### 1. 安装依赖

Windows（cmd）：

```bat
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux：

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 2. 生成配置

```bash
# macOS / Linux
cp config/config_sample.json config/config.json
cp .env.example .env
```

```bat
:: Windows
copy config\config_sample.json config\config.json
copy .env.example .env
```

`config/config.json` 和 `.env` 都已在 `.gitignore` 中忽略，不会被提交。请把真实 token 只放在 `.env` 里。

### 3. 填写配置

编辑 `config/config.json`，至少修改：

- `qq_bot.url`：SnowLuma 的 `send_group_msg` 地址。
- `projects`：项目名 → QQ 群号。
- `users`：用户名 → QQ 号。
- `mention_groups`：通知组名 → 用户名列表。

然后编辑 `.env`：

```dotenv
QQ_BOT_TOKEN=your-snowluma-token
```

配置示例：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 7848
  },
  "qq_bot": {
    "url": "http://127.0.0.1:3000/send_group_msg",
    "token": "",
    "timeout_seconds": 10.0
  },
  "projects": {
    "monster": {
      "group_id": 123456789
    }
  },
  "users": {
    "leaf": {
      "qq": "10001"
    }
  },
  "mention_groups": {
    "monster_tester": {
      "members": [
        "leaf"
      ]
    }
  }
}
```

### 4. 启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7848 --reload
```

打开 <http://127.0.0.1:7848/> 可以看到管理页面，健康检查：

```bash
curl -fsS http://127.0.0.1:7848/healthz
# {"ok":"true"}
```

生产环境不要使用 `--reload`，并保持**单进程**运行（不要加 `--workers`），因为缓存消息保存在进程内。

### 5. 发一条测试消息

```bash
curl -X POST "http://127.0.0.1:7848/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "monster",
    "title": "构建失败",
    "text": "@leaf 请看一下，测试消息。"
  }'
```

其中 `monster` 必须已经在 `projects` 中登记，`leaf` 必须已经在 `users` 中登记。

## 配置说明

默认配置文件是 `config/config.json`，可以通过 `QQ_NOTIFIER_CONFIG` 指定其他路径。

| 配置项 | 说明 |
| --- | --- |
| `server.host` / `server.port` | 仅作记录；实际监听地址由启动 uvicorn 时的 `--host` / `--port` 决定 |
| `qq_bot.url` | OneBot 的 `send_group_msg` 完整地址，私聊接口会用同主机同端口的 `/send_private_msg` |
| `qq_bot.token` | OneBot access token；建议留空，改用环境变量 `QQ_BOT_TOKEN` |
| `qq_bot.timeout_seconds` | 调用 OneBot 的超时时间，默认 10 秒 |
| `projects.<项目名>.group_id` | 项目对应的 QQ 群号 |
| `users.<用户名>.qq` | 用户名对应的 QQ 号，纯数字字符串 |
| `mention_groups.<组名>.members` | 组内成员的用户名列表，成员必须存在于 `users` 中 |

### Token 的读取顺序

1. 进程环境变量 `QQ_BOT_TOKEN`。
2. `.env` 文件中的 `QQ_BOT_TOKEN`（项目根目录或当前工作目录）。
3. `config/config.json` 的 `qq_bot.token`。

环境变量优先级最高。设置了 `QQ_BOT_TOKEN` 后，通过网页修改配置时不会把 token 写回 `config.json`，避免密钥落盘。

> `.env` 的加载规则：已经存在的系统环境变量不会被 `.env` 覆盖；也可以用 `QQ_ENV_FILE` 指定一个明确的 `.env` 路径。

### `@` 解析规则

- 支持 `@用户名` 和 `@通知组名`，例如 `@leaf`、`@monster_tester`。
- 用户名/组名只支持 **字母、数字、下划线 `_`、连字符 `-`**，不支持中文或空格。
- 通知组会展开为组内全部成员的 QQ 号，重复的 QQ 自动去重。
- 无法识别的 `@xxx` 会保留原文继续发送，并出现在响应的 `unknown_mentions` 中。
- `title`、`text`、`extra` 中的内容都会参与 `@` 解析。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/notify` | 发送群通知 |
| `POST` | `/private-message` | 发送私聊文本 |
| `POST` | `/cache-messages` | 写入一条缓存消息 |
| `GET` | `/cache-messages/copy-all` | 按 `project` + `key` 获取全部缓存文本 |
| `DELETE` | `/cache-messages/clear-all` | 按 `project` + `key` 清空缓存 |
| `GET` | `/` | 网页管理界面 |
| `GET` | `/config` | 查看当前配置，token 显示为 `***` |
| `GET` | `/config/validate` | 校验配置 |
| `GET` | `/healthz` | 健康检查 |

> 所有接口默认**没有认证**，只适合部署在可信内网。不要把 `7848` 端口直接暴露到公网。

### `POST /notify`

请求字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `project` | 是 | 项目名，必须已在 `projects` 中登记 |
| `text` | 是 | 消息正文，支持 `@用户名` / `@通知组名` |
| `title` | 否 | 标题，发送时排在正文之前 |
| `extra` | 否 | 附加对象，按 `键: 值` 逐行追加到正文之后，空值跳过 |

请求示例：

```bash
curl -X POST "http://127.0.0.1:7848/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "monster",
    "title": "构建失败",
    "text": "@leaf @monster_tester monster 项目构建失败，请处理。",
    "extra": {
      "job": "monster-main",
      "build_number": "123",
      "build_url": "http://jenkins.example/job/monster-main/123/"
    }
  }'
```

成功响应：

```json
{
  "ok": true,
  "project": "monster",
  "group_id": 123456789,
  "mentioned_users": ["leaf"],
  "mentioned_qqs": ["10001"],
  "unknown_mentions": [],
  "qq_bot_status": 200
}
```

`qq_bot_status` 是下游 OneBot 接口返回的 HTTP 状态码。

失败响应：

- `404`：`project` 未登记。
- `500`：配置校验不通过。
- `502`：下游 OneBot 调用失败（网络错误或非 2xx/4xx 拒绝）。

### `POST /private-message`

向指定 QQ 号发送私聊文本。请求发往与 `qq_bot.url` 同主机同端口的 `/send_private_msg`。

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `qq` | 是 | 目标 QQ 号，纯数字字符串，不以 `0` 开头 |
| `text` | 是 | 私聊文本内容，不能为空 |

```bash
curl -X POST "http://127.0.0.1:7848/private-message" \
  -H "Content-Type: application/json" \
  -d '{
    "qq": "10001",
    "text": "构建已经完成，请及时查看。"
  }'
```

成功响应：

```json
{
  "ok": true,
  "qq": "10001",
  "qq_bot_status": 200
}
```

失败响应：

- `422`：`qq` / `text` 格式不符。
- `502`：OneBot 发送失败。

除 HTTP 状态码外，本服务还会检查 OneBot 返回体：如果返回体中包含 `status` / `retcode`，则要求 `status == "ok"` 且 `retcode == 0`，避免出现 HTTP 200 但实际没有发出去的情况。

### 缓存消息

缓存接口适合接收构建产物、日志片段等需要在网页上复制的内容。

```bash
# 写入或刷新一条缓存消息（相同 project + key + message 会去重）
curl -X POST "http://127.0.0.1:7848/cache-messages" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "monster",
    "key": "build-123",
    "message": "构建日志片段",
    "payload": {"job": "monster-main"}
  }'

# 获取某个 project + key 下的全部文本
curl "http://127.0.0.1:7848/cache-messages/copy-all?project=monster&key=build-123"

# 清空某个 project + key
curl -X DELETE "http://127.0.0.1:7848/cache-messages/clear-all?project=monster&key=build-123"
```

缓存默认保存在 `logs/received-messages.json`，可用 `QQ_RECEIVED_MESSAGES` 覆盖路径。

### 网页管理

打开 <http://127.0.0.1:7848/>，页面包含三个标签页：

- **接收消息**：查看、复制、删除缓存消息。
- **配置**：管理用户、通知组、项目群号。
- **推送记录**：查看最近 24 小时实际发送给 OneBot 的消息和结果。

## Jenkins 集成

最小示例：

```bash
curl -X POST "http://<qq-bot-notifier-host>:7848/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "monster",
    "title": "构建失败",
    "text": "@leaf @monster_tester monster 项目构建失败，请处理。",
    "extra": {
      "job": "monster-main",
      "build_number": "123",
      "build_url": "http://jenkins.example/job/monster-main/123/"
    }
  }'
```

更多说明见 [docs/jenkins.md](docs/jenkins.md)。

## 部署

### Linux systemd

仓库已提供 systemd 单元和安装脚本：

```bash
# 先创建虚拟环境
python3 -m venv env
env/bin/pip install -r requirements.txt

# 按当前用户和项目路径渲染并安装（可用 RUN_USER / PORT / PYTHON_BIN 覆盖）
sudo bash deploy/linux/install-systemd.sh
```

也可以直接使用已按 `/home/leaf/qq-bot-notifier` 填好的单元：

```bash
sudo install -m 0644 deploy/linux/qq-bot-notifier.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now qq-bot-notifier
```

常用操作：

```bash
sudo systemctl restart qq-bot-notifier     # 重启
sudo systemctl status qq-bot-notifier      # 状态
journalctl -u qq-bot-notifier -f           # 跟随日志
curl -fsS http://127.0.0.1:7848/healthz    # 健康检查
sudo bash deploy/linux/uninstall-systemd.sh # 卸载（保留项目文件）
```

注意：

- 单元固定单进程运行，不要加 `--workers`。
- 服务运行目录必须是项目根目录，`app/templates`、`config/config.json`、`logs/` 都依赖相对路径。
- `.env` 通过 `EnvironmentFile=-.../.env` 注入，缺失不会阻断启动。

### macOS launchctl

```bash
bash deploy/macos/install-launchctl.sh
```

或者手工安装固定路径版本：

```bash
cp deploy/macos/com.leaf.bot-notifier.plist ~/Library/LaunchAgents/
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.leaf.bot-notifier.plist
launchctl kickstart -k "gui/$(id -u)/com.leaf.bot-notifier"
```

重启服务：

```bash
bash restart.sh
```

### Windows

开发时直接运行：

```bat
env\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 7848
```

长期运行可以用任务计划程序、NSSM 或公司现有的进程管理工具托管。

### VS Code

仓库已提供 `.vscode/launch.json`，启动项为 `QQ Bot Notifier: uvicorn`，同时支持 Windows 和 macOS：

- Windows 使用 `${workspaceFolder}/env/Scripts/python.exe`
- macOS 使用 `${workspaceFolder}/env/bin/python`

### Docker

本服务本身目前不内置 Dockerfile，推荐使用上面的 systemd / launchctl / Windows 方式直接运行。

QQ 协议端建议使用 SnowLuma 官方 Docker 部署：

- Docker 部署文档：<https://snowluma.github.io/zh/docs/guide/deploy/docker>
- Docker Framework 仓库：<https://github.com/SnowLuma/SnowLuma.Docker.Framework>
- Docker 镜像：<https://hub.docker.com/r/motricseven7/snowluma>

部署 SnowLuma 后，把 OneBot HTTP 地址填入本服务的 `qq_bot.url` 即可。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `QQ_BOT_TOKEN` | 空 | OneBot access token，优先级高于 `config/config.json` |
| `QQ_NOTIFIER_CONFIG` | `config/config.json` | 配置文件路径 |
| `QQ_DELIVERY_LOG` | `logs/qqbot-payloads.jsonl` | 实际发送 payload 的 JSONL 日志路径 |
| `QQ_RECEIVED_MESSAGES` | `logs/received-messages.json` | 缓存消息持久化路径 |
| `QQ_ENV_FILE` | 项目根目录 `.env` | 指定要加载的 `.env` 文件 |

## 日志与排错

- 发送给 OneBot 的 payload：`logs/qqbot-payloads.jsonl`（包含成功和失败，不记录 Authorization token）。
- 缓存消息：`logs/received-messages.json`。
- `logs/` 目录已被 `.gitignore` 忽略。
- 网页“推送记录”标签页可以查看最近 24 小时的发送结果。

常见问题：

| 现象 | 排查方向 |
| --- | --- |
| `Config file not found` | 没有创建 `config/config.json`，按快速开始复制示例 |
| 启动后 500 | 先访问 `GET /config/validate` 查看配置错误 |
| `401` / `403` | `QQ_BOT_TOKEN` 与 SnowLuma 的 access token 不一致 |
| `/notify` 返回 `404` | `project` 没有在 `projects` 中登记 |
| `/notify` 返回 `502` | SnowLuma 没启动、OneBot HTTP 没开启、地址或端口不对 |
| `@某人` 没有变成蓝色 @ | 用户名不在 `users` 中，或名字包含中文/空格等不支持的字符 |
| 私聊返回 502 但 OneBot 是 200 | OneBot 返回体的 `status` / `retcode` 表示失败，检查 SnowLuma 日志 |
| 端口被占用 | 改 `--port`，或停止占用 `7848` 的进程 |

## 安全须知

- 本服务的网页和 API **没有登录认证**，仅适合可信内网。暴露到更大范围前，请加反向代理认证、防火墙或 VPN。
- 不要提交 `config/config.json`、`.env`、`logs/`。
- 真实 token、密码只放在 `.env` 或进程环境变量中。
- `GET /config` 只会把 token 显示为 `***`，但其他配置仍然可见。
- 如果真实凭据曾经被提交到 Git，**仅从当前文件删除并不能清除历史**。请立即在 SnowLuma / Jenkins 侧轮换 token，必要时使用 `git filter-repo` 清理历史。

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest -q
```

项目结构：

```text
app/
  main.py                  FastAPI 入口和路由
  config_store.py          配置读写、校验、token 隐藏
  message_parser.py        @ 解析和 OneBot 消息段构造
  qq_sender.py             调用 OneBot 群聊/私聊接口、payload 日志
  received_message_store.py 缓存消息持久化
  models.py                Pydantic 模型
  templates/index.html     网页管理界面
config/
  config_sample.json       配置示例（不含真实 token）
.env.example               环境变量示例（复制为 .env 后填写）
deploy/                    Linux systemd / macOS launchctl 部署脚本
docs/jenkins.md            Jenkins 调用说明
tests/                     自动化测试
```

## License

[MIT](LICENSE)
