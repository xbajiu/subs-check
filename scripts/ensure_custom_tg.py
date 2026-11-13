#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化自愈与代码防冲突保底脚本：
无论上游 (beck-8/subs-check) 如何更新 config.go、config.example.yaml、notify.go 或 README.md，
本脚本都能智能检测并 100% 自动确保用户的 Telegram 推送、自定义代理域名逻辑及个人 GHCR 镜像绝对保留！
"""

import os
import re
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CONFIG_GO_PATH = os.path.join(BASE_DIR, "config", "config.go")
CONFIG_YAML_PATH = os.path.join(BASE_DIR, "config", "config.example.yaml")
NOTIFY_GO_PATH = os.path.join(BASE_DIR, "utils", "notify.go")
README_PATH = os.path.join(BASE_DIR, "README.md")

def ensure_config_go():
    if not os.path.exists(CONFIG_GO_PATH):
        print(f"[!] 未找到 {CONFIG_GO_PATH}")
        return False
    with open(CONFIG_GO_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否已包含关键字段
    if "TelegramBotToken" in content and "TelegramChatID" in content and "ProxyTG" in content:
        print("[OK] config/config.go 已包含 TG 配置字段，无需重复注入。")
        return True

    # 准备注入的字段
    inject_fields = (
        "\tTelegramBotToken     string    `yaml:\"telegram-bot-token\"`\n"
        "\tTelegramChatID       string    `yaml:\"telegram-chat-id\"`\n"
        "\tProxyTG              string    `yaml:\"proxy-tg\"`\n"
    )

    # 尝试在 NotifyTitle 或 AppriseApiServer 或 ListenPort 附近插入
    patterns = [
        r"(NotifyTitle\s+string\s+`yaml:\"notify-title\"`\n)",
        r"(AppriseApiServer\s+string\s+`yaml:\"apprise-api-server\"`\n)",
        r"(type\s+Config\s+struct\s*\{[\s\S]*?)(ListenPort\s+string\s+`yaml:\"listen-port\"`\n)",
    ]

    injected = False
    for pat in patterns:
        if re.search(pat, content):
            content = re.sub(pat, r"\1" + inject_fields, content, count=1)
            injected = True
            break

    if not injected:
        struct_pat = r"(type\s+Config\s+struct\s*\{\n)"
        if re.search(struct_pat, content):
            content = re.sub(struct_pat, r"\1" + inject_fields, content, count=1)
            injected = True

    if injected:
        with open(CONFIG_GO_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] 成功将 TG 字段自动注回 config/config.go！")
        return True
    else:
        print("[Error] 无法定位 Config 结构体进行注入！")
        return False


def ensure_config_yaml():
    if not os.path.exists(CONFIG_YAML_PATH):
        print(f"[!] 未找到 {CONFIG_YAML_PATH}")
        return False
    with open(CONFIG_YAML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if "telegram-bot-token:" in content and "proxy-tg:" in content:
        print("[OK] config/config.example.yaml 已包含 TG 配置模板。")
        return True

    yaml_block = (
        "\n# ---------------- TG 推送设置 (原生直推，无需搭建 Apprise) ----------------\n"
        "# telegram 机器人 Token (通过 @BotFather 获取)\n"
        "telegram-bot-token: \"\"\n"
        "# 接收通知的 Chat ID (个人 ID 或频道/群组 ID，如 123456789 或 -100123456789)\n"
        "telegram-chat-id: \"\"\n"
        "# TG 推送代理域名 (留空默认使用 https://api.telegram.org；国内或网络受限环境可填自建反代域名，如: https://tgproxy.example.com)\n"
        "proxy-tg: \"\"\n"
    )

    if "notify-title:" in content:
        content = re.sub(r"(notify-title:[^\n]*\n)", r"\1" + yaml_block, content, count=1)
    else:
        content += yaml_block

    with open(CONFIG_YAML_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] 成功将 TG 配置模板自动注回 config/config.example.yaml！")
    return True


def ensure_notify_go():
    if not os.path.exists(NOTIFY_GO_PATH):
        print(f"[!] 未找到 {NOTIFY_GO_PATH}")
        return False
    with open(NOTIFY_GO_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if "SendTelegram" in content:
        print("[OK] utils/notify.go 已包含 SendTelegram 逻辑。")
        return True

    tg_code_block = """
	// 1. 原生 Telegram 机器人推送 (配置了 telegram-bot-token 和 telegram-chat-id 则触发)
	if config.GlobalConfig.TelegramBotToken != "" && config.GlobalConfig.TelegramChatID != "" {
		var err error
		retries := config.GlobalConfig.SubUrlsReTry
		if retries <= 0 {
			retries = 3
		}
		for i := 0; i < retries; i++ {
			err = SendTelegram(titleText, bodyText)
			if err == nil {
				slog.Info("Telegram 通知发送成功")
				break
			}
		}
		if err != nil {
			slog.Error(fmt.Sprintf("Telegram 发送通知失败: %v", err))
		}
	}
"""

    func_pattern = r"(func\s+SendNotify\s*\([^\)]*\)\s*\{)"
    match = re.search(func_pattern, content)
    if not match:
        print("[Error] 无法定位 SendNotify 函数")
        return False

    if "bodyText :=" not in content:
        prep_vars = """
	bodyText := fmt.Sprintf("✅ 可用节点：%d\\n🕒 %s", length, GetCurrentTime())
	titleText := config.GlobalConfig.NotifyTitle
"""
        full_inject = prep_vars + tg_code_block
    else:
        full_inject = tg_code_block

    content = re.sub(func_pattern, r"\1" + full_inject, content, count=1)

    with open(NOTIFY_GO_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] 成功将 Telegram 发送逻辑自动注回 utils/notify.go！")
    return True


def ensure_readme():
    if not os.path.exists(README_PATH):
        print(f"[!] 未找到 {README_PATH}")
        return False
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    changed = False

    # 1. 确保 Docker 镜像指向 xbajiu 的 GHCR 镜像
    if "ghcr.io/beck-8/subs-check" in content:
        content = content.replace("ghcr.io/beck-8/subs-check", "ghcr.io/xbajiu/subs-check")
        changed = True

    # 2. 确保 Telegram 推送章节存在
    if "telegram-bot-token" not in content:
        tg_doc = """
### ✈️ Telegram 原生直接推送（推荐，无需部署 Apprise，支持自定义反代域名）

> **💡 说明：** 类似 CloudFastDDNS 的 Telegram 推送方式，直接填写 Bot Token 与 Chat ID 即可使用；在网络受限环境可配置反向代理域名。

```yaml
# telegram 机器人 Token (通过 @BotFather 获取)
telegram-bot-token: "123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
# 接收通知的 Chat ID (个人 ID 或频道/群组 ID，例如 987654321 或 -100123456789)
telegram-chat-id: "987654321"
# TG 推送代理域名 (留空默认使用 https://api.telegram.org；国内环境可配置自建或公共反代)
proxy-tg: "https://tgproxy.example.com"
```
"""
        if "## 🔔 通知渠道配置（可选）" in content:
            content = content.replace("## 🔔 通知渠道配置（可选）\n<details>\n  <summary>展开查看</summary>",
                                      "## 🔔 通知渠道配置（可选）\n<details>\n  <summary>展开查看</summary>\n" + tg_doc)
            changed = True

    if changed:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] 成功将个人镜像与 TG 文档防冲突自愈至 README.md！")
    else:
        print("[OK] README.md 已包含正确的个人镜像与 TG 说明。")
    return True


def main():
    print("=== 开始执行全量配置与代码保底自愈检查 ===")
    ok1 = ensure_config_go()
    ok2 = ensure_config_yaml()
    ok3 = ensure_notify_go()
    ok4 = ensure_readme()

    if ok1 and ok2 and ok3 and ok4:
        print("=== 所有核心关键代码校验完成：100% 存在且完好！ ===")
        sys.exit(0)
    else:
        print("=== 警告：部分检查未完全通过，请检查日志 ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
