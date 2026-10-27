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
- `POST /private-message`：向指定 QQ 号发送私聊文本消息。
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
