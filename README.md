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

- `POST /notify`：接收 Jenkins 通知并转发。
- `GET /`：网页管理用户、通知组、项目群号。
- `GET /config`：查看当前配置，token 会被隐藏。
- `GET /config/validate`：校验配置。
- `GET /healthz`：健康检查。

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
