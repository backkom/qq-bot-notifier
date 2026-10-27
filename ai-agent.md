# qq-bot-notifier AI Agent Handoff

> **内部交接文档**：包含内网地址、部署路径和示例账号，请勿随公开仓库发布；对外说明以 [README.md](README.md) 为准。

## 背景

本仓库用于实现一个 QQ 群机器人通知转发服务。服务运行在内网：

- 本服务地址：`http://192.168.0.193:7848`
- 上游调用方：Jenkins，通过 `curl` 发送 HTTP JSON 消息
- 下游机器人接口示例：`http://192.168.0.199:3000/send_group_msg`
- 下游鉴权示例：`Authorization: Bearer <your-token>`（真实 token 请放在 `.env` 的 `QQ_BOT_TOKEN` 中，不要提交）

目标是让 Jenkins 只关心项目、通知目标和文本内容，由本服务负责：

1. 接收 Jenkins 发来的 JSON。
2. 按配置找到项目对应的 QQ 群号。
3. 解析文本中的 `@xxx`。
4. 将用户名或组名转换成 QQ 号。
5. 拼接 QQ 机器人要求的消息结构。
6. POST 到 QQ 机器人接口，实现群内 @ 指定人或多人。

当前仓库状态：

- 目前只有 `README.md`、`LICENSE`、`.gitignore`，还没有服务代码。
- `.gitignore` 是 Python 项目模板，建议后续用 Python/FastAPI 实现，贴合现有仓库暗示。
- `README.md` 当前疑似编码显示异常，内容本意应为 QQ 机器人通知。

## 用户原始需求

需要实现一个用于往指定 URL POST 消息的服务，实现 QQ 机器人在群里 @ 对应人的功能。

服务需要：

1. 接收 JSON 消息，消息包含 `project`、组名、人名、文本信息；接收后按期望格式转换并转发。
2. 解析消息里的 @ 信息：
   - `@leaf`：从配置中找出 `leaf` 对应的 QQ 号。
   - `@monster_tester`：从配置中找出该组对应的多个用户名或 QQ 号，再展开成多个 @。
3. 提供网页，展示并允许任何人新增或修改用户名到 QQ 号的映射，例如 `leaf -> 172310132`。
4. 提供 JSON 配置，允许将 `@monster_tester` 这样的组目标转换为多个具体人。
5. 在 JSON 中配置 `project` 对应的群号，例如 `524653233`。
6. 定义 Jenkins 发来的消息结构，并在文档中给出示例写法。

已知可以正确执行的下游机器人请求：

```bash
curl -X POST "http://192.168.0.199:3000/send_group_msg" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 524653233,
    "message": [
      {
        "type": "at",
        "data": {
          "qq": "172310132"
        }
      },
      {
        "type": "text",
        "data": {
          "text": " test msg"
        }
      }
    ]
  }'
```

## 待审核方案

建议实现为一个轻量 FastAPI 服务。

核心模块：

- `app/main.py`：FastAPI 入口，监听 `0.0.0.0:7848`。
- `app/config_store.py`：读取和写入 JSON 配置。
- `app/message_parser.py`：解析 Jenkins 消息、提取 `@xxx`、展开人员和组。
- `app/qq_sender.py`：调用下游 QQ 机器人接口。
- `app/templates/`：网页管理界面。
- `config/config.json`：项目、用户、组、机器人接口配置。
- `docs/jenkins.md`：Jenkins curl 示例和字段说明。

推荐依赖：

- `fastapi`
- `uvicorn`
- `httpx`
- `pydantic`
- `jinja2`
- `python-multipart`
- `pytest`

## 建议的配置结构

配置文件路径建议为 `config/config.json`：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 7848
  },
  "qq_bot": {
    "url": "http://192.168.0.199:3000/send_group_msg",
    "token": "replace token here",
    "timeout_seconds": 10
  },
  "projects": {
    "monster": {
      "group_id": 524653233
    }
  },
  "users": {
    "leaf": {
      "qq": "172310132"
    }
  },
  "mention_groups": {
    "monster_tester": {
      "members": ["leaf"]
    }
  }
}
```

说明：

- `projects`：Jenkins 传来的 `project` 映射到 QQ 群号。
- `users`：用户名映射到 QQ 号。
- `mention_groups`：组名映射到多个用户名。也可以后续扩展支持直接写 QQ 号，但第一版建议只写用户名，减少歧义。
- `qq_bot.token`：敏感信息。审核后建议支持从环境变量覆盖，例如 `QQ_BOT_TOKEN`，避免真实 token 提交到仓库。

## Jenkins 请求结构

建议 Jenkins 调用本服务的接口：

```http
POST /notify
Content-Type: application/json
```

请求体：

```json
{
  "project": "monster",
  "title": "构建失败",
  "text": "@leaf @monster_tester monster 项目构建失败，请处理。",
  "extra": {
    "job": "monster-main",
    "build_number": "123",
    "build_url": "http://jenkins.example/job/monster-main/123/"
  }
}
```

字段含义：

- `project`：必填，用于找到 QQ 群号。
- `title`：可选，作为消息标题。
- `text`：必填，正文。正文中的 `@xxx` 会被解析。
- `extra`：可选，放 Jenkins 的 job、build number、URL 等扩展信息。

建议 Jenkins curl 示例：

```bash
curl -X POST "http://192.168.0.193:7848/notify" \
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

## 消息转换规则

输入：

```json
{
  "project": "monster",
  "title": "构建失败",
  "text": "@leaf @monster_tester monster 项目构建失败，请处理。"
}
```

配置：

```json
{
  "projects": {
    "monster": {
      "group_id": 524653233
    }
  },
  "users": {
    "leaf": {
      "qq": "172310132"
    },
    "alice": {
      "qq": "10001"
    },
    "bob": {
      "qq": "10002"
    }
  },
  "mention_groups": {
    "monster_tester": {
      "members": ["alice", "bob"]
    }
  }
}
```

下游请求：

```json
{
  "group_id": 524653233,
  "message": [
    {
      "type": "at",
      "data": {
        "qq": "172310132"
      }
    },
    {
      "type": "text",
      "data": {
        "text": " "
      }
    },
    {
      "type": "at",
      "data": {
        "qq": "10001"
      }
    },
    {
      "type": "at",
      "data": {
        "qq": "10002"
      }
    },
    {
      "type": "text",
      "data": {
        "text": " monster 项目构建失败，请处理。"
      }
    }
  ]
}
```

规则建议：

- 用正则识别 `@([A-Za-z0-9_\\-]+)`。
- 如果目标命中 `users`，转换为单个 QQ at。
- 如果目标命中 `mention_groups`，展开为多个 QQ at。
- 如果同一个 QQ 被多个 @ 命中，默认去重，避免重复刷屏。
- 原文中无法识别的 `@xxx` 建议保留为普通文本，并在响应里返回 `unknown_mentions`，方便 Jenkins 或调用方排查。
- 每个 at 后可以插入一个空格文本，让 QQ 客户端显示更自然。

## API 设计

### `POST /notify`

接收 Jenkins 通知，转换并转发到 QQ 机器人。

成功响应：

```json
{
  "ok": true,
  "project": "monster",
  "group_id": 524653233,
  "mentioned_users": ["leaf", "alice", "bob"],
  "unknown_mentions": []
}
```

失败响应：

- `400`：请求格式错误。
- `404`：找不到 project、用户或组配置。
- `502`：调用下游 QQ 机器人失败。

### `POST /private-message`

供上游调用方向指定 QQ 号发送私聊文本消息。

请求体：

```json
{
  "qq": "172310132",
  "text": "构建已经完成，请及时查看。"
}
```

字段含义：

- `qq`：必填，接收方 QQ 号，使用只包含数字的字符串。
- `text`：必填，要发送的文本消息，不能为空字符串。

成功响应：

```json
{
  "ok": true,
  "qq": "172310132",
  "qq_bot_status": 200
}
```

调用示例：

```bash
curl -X POST "http://192.168.0.193:7848/private-message" \
  -H "Content-Type: application/json" \
  -d '{
    "qq": "172310132",
    "text": "构建已经完成，请及时查看。"
  }'
```

根据 NapCat 官方 `send_private_msg` 动作定义，本服务向与 `qq_bot.url` 相同的 NapCat HTTP 服务调用：

```http
POST /send_private_msg
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "user_id": "172310132",
  "message": "构建已经完成，请及时查看。"
}
```

NapCat 即使业务失败也可能返回 HTTP 200，因此实现必须同时检查响应 JSON：仅 `status` 为 `ok` 且 `retcode` 为 `0` 时视为成功。调用失败时本接口返回 `502`；请求字段校验失败时由 FastAPI 返回 `422`。

### `GET /`

网页管理界面首页。

建议展示：

- 用户名到 QQ 号映射表。
- 组名到成员列表。
- 项目到群号配置。
- 最近一次配置更新时间。

### `POST /users`

新增或更新用户：

```json
{
  "username": "leaf",
  "qq": "172310132"
}
```

第一版网页表单可直接提交 `application/x-www-form-urlencoded`。

### `POST /mention-groups`

新增或更新组：

```json
{
  "name": "monster_tester",
  "members": ["leaf", "alice", "bob"]
}
```

### `POST /projects`

新增或更新项目群号：

```json
{
  "project": "monster",
  "group_id": 524653233
}
```

### `GET /config`

返回当前配置。第一版可以先开放给内网使用；如果服务暴露范围扩大，需要加认证。

## 网页管理界面建议

第一版保持简单可维护：

- 首页单页即可。
- 三个区域：用户、组、项目。
- 每个区域有列表和新增/更新表单。
- 不做登录，符合“允许任何人增加记录”的需求。
- 需要在页面上明确显示当前服务是内网配置工具，错误提示要清楚。

风险：

- 任何人可改配置，适合可信内网；不适合公网。
- 如果后续需要权限，可以增加一个简单管理 token 或接入公司已有认证。

## 持久化策略

第一版建议直接用 JSON 文件：

- 简单、可人工编辑、方便交接。
- 每次写入时使用临时文件加原子替换，降低配置损坏风险。
- 写入前做字段校验，避免把非法配置写入。

后续如果多人频繁维护或配置量变大，再迁移到 SQLite。

## 日志与排错

建议记录：

- 接收到的 `project`、`title`、提取出的 mentions。
- 展开的 QQ 号列表。
- 未识别的 mentions。
- 下游 QQ 机器人响应状态码和错误摘要。

不要记录：

- 完整 Authorization token。
- 不必要的敏感构建参数。

建议提供：

- `GET /healthz`：返回服务状态。
- `GET /config/validate`：检查配置是否有组成员不存在、QQ 号为空、project 缺群号等问题。

## 运行方式建议

本地开发：

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7848 --reload
```

生产运行可以先用 Windows 计划任务、NSSM 或已有进程管理方式托管。若部署在 Linux，再补 systemd service。

## 测试建议

至少覆盖：

- `@leaf` 解析为单人。
- `@monster_tester` 展开为多人。
- 重复 @ 去重。
- 未知 @ 返回 `unknown_mentions`。
- 未知 project 返回错误。
- 下游 QQ bot 返回失败时，本服务返回 502。

## 实施顺序

1. 初始化 Python/FastAPI 项目结构。
2. 定义 Pydantic 请求模型和配置模型。
3. 实现 JSON 配置读取、校验、写入。
4. 实现 mention 解析和展开。
5. 实现下游 QQ bot 发送。
6. 实现 `/notify`、`/healthz`、`/config`。
7. 实现网页管理界面。
8. 补充 `README.md` 和 `docs/jenkins.md`。
9. 补测试。
10. 本地启动验证 Jenkins curl 和下游 curl 格式。

## 待用户审核的问题

1. Jenkins 入参结构是否接受上面建议的 `project/title/text/extra`？
2. `@monster_tester` 组配置是否只允许配置用户名，还是也要允许直接配置 QQ 号？
3. 未识别的 `@xxx` 是保留原文并继续发送，还是直接报错不发送？
4. 网页管理是否确认不需要登录或 token？
5. 下游 QQ bot token 是否可以从环境变量读取，配置文件只放示例？
6. 是否需要保存通知发送历史？

## 下一位 AI 维护注意事项

- 用户当前要的是“方案待审核”，不要直接开始写业务代码，除非用户后续明确确认实施。
- 本文件是交接上下文，应在后续方案变化时同步更新。
- 仓库目前没有现成服务代码，实施时可以从 FastAPI 项目骨架开始。
- 已新增 VS Code 启动配置 `.vscode/launch.json`，只有一个启动项 `QQ Bot Notifier: uvicorn`，通过平台覆盖字段同时支持 Windows 和 macOS。它使用项目内 `env` 虚拟环境启动 `uvicorn app.main:app --host 0.0.0.0 --port 7848 --reload`；Windows 使用 `env/Scripts/python.exe`，macOS 使用 `env/bin/python`。
- 已新增 macOS launchctl 配置：`deploy/macos/com.leaf.bot-notifier.plist` 使用用户确认的 macOS 项目路径 `/Users/leaf/Documents/qq-bot-notifier`。同时保留模板和安装脚本：`deploy/macos/com.leaf.bot-notifier.plist.template`、`deploy/macos/install-launchctl.sh`、`deploy/macos/uninstall-launchctl.sh`。在 macOS 上需要先创建 `env/bin/python`，再把 plist 放到 `~/Library/LaunchAgents/com.leaf.bot-notifier.plist` 或执行安装脚本生成并加载。
- 已新增 Linux systemd 部署：`deploy/linux/qq-bot-notifier.service`（固定 `/home/leaf/qq-bot-notifier`、用户 `leaf`、端口 `7848`，单进程 uvicorn）、同目录模板 `qq-bot-notifier.service.template`，以及 `install-systemd.sh` / `uninstall-systemd.sh`。单元通过 `EnvironmentFile=-<项目>/.env` 注入 token，`ProtectSystem=full` 等只读加固，`ExecStartPre` 自建 `logs/`。部署说明见 `README.md` 的 “Linux systemd” 一节。
- 已按方案实现第一版服务：核心代码位于 `app/`，默认配置位于 `config/config.json`，Jenkins 文档位于 `docs/jenkins.md`，测试位于 `tests/`。当前默认行为：未知 `@xxx` 保留原文并继续发送；通知组成员配置用户名；网页管理暂不加认证；`QQ_BOT_TOKEN` 环境变量优先覆盖配置文件 token。
- 实际发给 QQ bot 的 payload 会在发送前追加写入 JSONL 日志，默认路径 `logs/qqbot-payloads.jsonl`，可用 `QQ_DELIVERY_LOG` 环境变量覆盖。日志包含时间、下游 URL 和 payload，不记录 Authorization token。
- 已用项目内 `env` 安装运行和测试依赖，并通过 `env\Scripts\python.exe -m pytest -q`，当前结果为 `7 passed`。本地 Windows 验证过 `http://127.0.0.1:7848/healthz` 和网页首页可访问。
- 不要把真实生产 token 写死进仓库；如果需要示例，使用 `.env.example` 或文档占位符。
- 如果编辑 README，注意当前 README 内容可能是编码乱码，建议直接替换为 UTF-8 中文。
- 如果实现网页，保持简单实用，优先可维护性和配置正确性。
- 如果服务只在可信内网运行，可以先不做认证；如果暴露给更广范围，必须补认证。
