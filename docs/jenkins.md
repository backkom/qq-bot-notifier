# Jenkins 调用说明

Jenkins 调用本服务：

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

字段：

- `project`：必填，用来查找要发送的 QQ 群号。
- `title`：可选，消息标题。
- `text`：必填，正文。正文里的 `@leaf`、`@monster_tester` 会按配置展开为 QQ at。
- `extra`：可选，附加字段会追加到正文末尾。

下游 QQ 机器人接口由 `config/config.json` 的 `qq_bot.url` 配置。`qq_bot.token` 可以留空，并通过环境变量 `QQ_BOT_TOKEN` 覆盖。

