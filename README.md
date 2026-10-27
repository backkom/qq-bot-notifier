# qq-bot-notifier

内网 QQ 群机器人通知转发服务。Jenkins 发送简单 JSON 到本服务，本服务根据配置解析 `@leaf`、`@monster_tester` 这类目标，转换成 QQ 机器人需要的 `send_group_msg` 消息结构并转发。

## 运行

Windows:

```bash
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7848 --reload
```

macOS:

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7848 --reload
```

真实机器人 token 建议通过环境变量提供：

```bash
export QQ_BOT_TOKEN="your-token"
```

实际发送给 QQ bot 的 payload 会追加写入本地 JSONL 日志，默认路径为 `logs/qqbot-payloads.jsonl`。可以通过环境变量覆盖：

```bash
export QQ_DELIVERY_LOG="logs/qqbot-payloads.jsonl"
```

## 接口

- `POST /notify`：接收 Jenkins 通知并转发到项目群。
- `POST /private-message`：向指定 QQ 号发送私聊文本消息。
- `GET /`：网页管理用户、通知组、项目群号。
- `GET /config`：查看当前配置，token 会被隐藏。
- `GET /config/validate`：校验配置。
- `GET /healthz`：健康检查。

机器人 token 默认读取 `config/config.json` 的 `qq_bot.token`；若进程环境存在 `QQ_BOT_TOKEN`，加载时会覆盖该值（适合共享机器等不想把密钥落盘的场景）。

### POST /notify

将 `text` 中的 `@目标` 解析为机器人消息段后，发送到 `projects.<project>.group_id` 对应的 QQ 群。`@目标` 先按 `users` 里的用户名匹配（换成该用户 QQ 的 @），再按 `mention_groups` 的组名匹配（展开 @ 组内全部成员，重复 QQ 自动去重）；无法识别的 `@xxx` 会以原文保留并继续发送，同时出现在响应的 `unknown_mentions` 里。

```bash
curl -X POST "http://192.168.50.5:7848/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "family",
    "title": "构建失败",
    "text": "@leaf test。"
  }'
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| project | 是 | 项目名，必须已在配置的 `projects` 中登记 |
| text | 是 | 消息正文，支持 `@用户名` / `@通知组名` |
| title | 否 | 标题，发送时排在正文之前 |
| extra | 否 | 附加对象，按 `键: 值` 逐行追加到正文之后（空值跳过） |

成功响应示例（`qq_bot_status` 为下游机器人的 HTTP 状态码）：

```json
{
  "ok": true,
  "project": "family",
  "group_id": 524653233,
  "mentioned_users": ["leaf"],
  "mentioned_qqs": ["172310132"],
  "unknown_mentions": [],
  "qq_bot_status": 200
}
```

失败响应：`project` 未登记返回 `404`；配置校验不通过返回 `500`；下游机器人调用失败（网络错误或非 2xx/4xx 拒绝）返回 `502`，并会额外触发一次失败告警。

### POST /private-message

向指定 QQ 号发送私聊文本。请求发往与 `qq_bot.url` 同主机同端口的 `/send_private_msg`，除 HTTP 状态码外还会校验 NapCat 返回体的 `status == "ok"` 且 `retcode == 0`。

```bash
curl -X POST "http://192.168.50.5:7848/private-message" \
  -H "Content-Type: application/json" \
  -d '{
    "qq": "172310132",
    "text": "构建已经完成，请及时查看。"
  }'
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| qq | 是 | 目标 QQ 号，纯数字字符串（不以 0 开头） |
| text | 是 | 私聊文本内容，不能为空 |

成功响应示例：

```json
{
  "ok": true,
  "qq": "172310132",
  "qq_bot_status": 200
}
```

失败响应：`qq`/`text` 格式不符返回 `422`；机器人发送失败返回 `502`。

实际发出去的 payload（含成功与失败）会追加记录到 `logs/qqbot-payloads.jsonl`（可用 `QQ_DELIVERY_LOG` 覆盖路径），不记录 Authorization token。

Jenkins 示例见 [docs/jenkins.md](docs/jenkins.md)。

## VS Code

已提供 `.vscode/launch.json`，启动项为 `QQ Bot Notifier: uvicorn`。该启动项同时支持 Windows 和 macOS：

- Windows 使用 `${workspaceFolder}/env/Scripts/python.exe`
- macOS 使用 `${workspaceFolder}/env/bin/python`

## macOS launchctl

已提供固定路径版本：

```bash
cp deploy/macos/com.sevenpirates.bot-notifier.plist ~/Library/LaunchAgents/
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.sevenpirates.bot-notifier.plist
launchctl kickstart -k "gui/$(id -u)/com.sevenpirates.bot-notifier"
```

也可以在 macOS 上运行：

```bash
bash deploy/macos/install-launchctl.sh
```

## Linux systemd

服务单元位于 `deploy/linux/qq-bot-notifier.service`，已按部署路径 `/home/leaf/qq-bot-notifier`、运行用户 `leaf`、端口 `7848` 填好，可直接拷贝：

```bash
sudo install -m 0644 deploy/linux/qq-bot-notifier.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now qq-bot-notifier
```

若路径或用户不同，用安装脚本按实际环境渲染模板（`qq-bot-notifier.service.template`）：

```bash
# 默认取当前用户与项目所在目录，可用 RUN_USER / PORT / PYTHON_BIN 覆盖
sudo bash deploy/linux/install-systemd.sh
```

常用操作：

```bash
sudo systemctl restart qq-bot-notifier     # 重启
sudo systemctl status qq-bot-notifier      # 状态
journalctl -u qq-bot-notifier -f           # 跟随日志
curl -fsS http://127.0.0.1:7848/healthz    # 健康检查
sudo bash deploy/linux/uninstall-systemd.sh  # 卸载（保留项目文件）
```

注意：

- 单元固定单进程运行，不要加 `--workers`：缓存消息保存在进程内，并由 `logs/received-messages.json` 持久化。
- `.env` 通过 `EnvironmentFile=-.../.env` 注入（缺失不阻断启动），`QQ_BOT_TOKEN` 也可写在 `config/config.json`。
- 服务运行目录即项目根目录，`app/templates`、`config/config.json`、`logs/` 都依赖相对路径，改动 `WorkingDirectory` 会导致启动失败。
- 首次部署前先准备虚拟环境：`python3 -m venv env && env/bin/pip install -r requirements.txt`。
