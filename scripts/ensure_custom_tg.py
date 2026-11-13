#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化自愈与全方位防冲突保底脚本：
无论上游 (beck-8/subs-check) 如何重构或更新，
本脚本都能 100% 自动确保用户的 Telegram 推送、自定义反代域名、GHCR 镜像及文档绝对保留且零冲突！
"""

import os
import re
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CONFIG_GO_PATH = os.path.join(BASE_DIR, "config", "config.go")
CONFIG_YAML_PATH = os.path.join(BASE_DIR, "config", "config.example.yaml")
NOTIFY_GO_PATH = os.path.join(BASE_DIR, "utils", "notify.go")
TELEGRAM_GO_PATH = os.path.join(BASE_DIR, "utils", "telegram.go")
TELEGRAM_TEST_PATH = os.path.join(BASE_DIR, "utils", "telegram_test.go")
README_PATH = os.path.join(BASE_DIR, "README.md")

TELEGRAM_GO_CONTENT = """package utils

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/beck-8/subs-check/config"
)

// TelegramMessage 表示发送给 Telegram Bot API 的请求体
type TelegramMessage struct {
	ChatID    string `json:"chat_id"`
	Text      string `json:"text"`
	ParseMode string `json:"parse_mode,omitempty"`
}

// NormalizeTelegramEndpoint 规范化 Telegram Bot API 推送地址
// 支持空值、纯域名、带 https://、或者包含子路径的自定义反向代理
func NormalizeTelegramEndpoint(proxyTG, botToken string) string {
	proxy := strings.TrimSpace(proxyTG)
	if proxy == "" {
		proxy = "https://api.telegram.org"
	} else {
		// 去除首尾斜杠及多余空白
		proxy = strings.TrimRight(proxy, "/")
		if !strings.HasPrefix(proxy, "http://") && !strings.HasPrefix(proxy, "https://") {
			proxy = "https://" + proxy
		}
	}
	return fmt.Sprintf("%s/bot%s/sendMessage", proxy, botToken)
}

// SendTelegram 发送 Telegram 推送通知
func SendTelegram(title, body string) error {
	token := strings.TrimSpace(config.GlobalConfig.TelegramBotToken)
	chatID := strings.TrimSpace(config.GlobalConfig.TelegramChatID)
	if token == "" || chatID == "" {
		return nil
	}

	var messageText string
	if title != "" {
		messageText = fmt.Sprintf("%s\\n\\n%s", title, body)
	} else {
		messageText = body
	}

	msg := TelegramMessage{
		ChatID: chatID,
		Text:   messageText,
	}

	data, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("构建 Telegram 请求体失败: %w", err)
	}

	endpoint := NormalizeTelegramEndpoint(config.GlobalConfig.ProxyTG, token)

	client := &http.Client{
		Timeout: 20 * time.Second,
	}

	resp, err := client.Post(endpoint, "application/json", bytes.NewBuffer(data))
	if err != nil {
		return fmt.Errorf("请求 Telegram API 失败 (请检查网络或代理域名): %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Telegram 推送返回状态码 %d: %s", resp.StatusCode, string(respBody))
	}

	var tgResp struct {
		OK          bool   `json:"ok"`
		Description string `json:"description"`
	}
	if err := json.Unmarshal(respBody, &tgResp); err == nil && !tgResp.OK {
		return fmt.Errorf("Telegram 返回错误: %s", tgResp.Description)
	}

	return nil
}
"""

TELEGRAM_TEST_CONTENT = """package utils

import (
	"testing"
)

func TestNormalizeTelegramEndpoint(t *testing.T) {
	tests := []struct {
		proxy    string
		token    string
		expected string
	}{
		{
			proxy:    "",
			token:    "123456:ABC-DEF",
			expected: "https://api.telegram.org/bot123456:ABC-DEF/sendMessage",
		},
		{
			proxy:    "api.telegram.org",
			token:    "123456:ABC-DEF",
			expected: "https://api.telegram.org/bot123456:ABC-DEF/sendMessage",
		},
		{
			proxy:    "https://api.telegram.org/",
			token:    "123456:ABC-DEF",
			expected: "https://api.telegram.org/bot123456:ABC-DEF/sendMessage",
		},
		{
			proxy:    "tg.yourdomain.com",
			token:    "123456:ABC-DEF",
			expected: "https://tg.yourdomain.com/bot123456:ABC-DEF/sendMessage",
		},
		{
			proxy:    "http://tg.yourdomain.com:8080",
			token:    "123456:ABC-DEF",
			expected: "http://tg.yourdomain.com:8080/bot123456:ABC-DEF/sendMessage",
		},
		{
			proxy:    "https://tg.yourdomain.com/custom-prefix/",
			token:    "123456:ABC-DEF",
			expected: "https://tg.yourdomain.com/custom-prefix/bot123456:ABC-DEF/sendMessage",
		},
	}

	for _, tt := range tests {
		got := NormalizeTelegramEndpoint(tt.proxy, tt.token)
		if got != tt.expected {
			t.Errorf("NormalizeTelegramEndpoint(%q, %q) = %q; expected %q", tt.proxy, tt.token, got, tt.expected)
		}
	}
}
"""

def clean_conflict_markers(content):
    """清除意外残留的 Git 冲突标记"""
    # 移除 <<<<<<< HEAD ... ======= ... >>>>>>>
    content = re.sub(r"<<<<<<< [^\n]+\n([\s\S]*?)=======\n([\s\S]*?)>>>>>>> [^\n]+\n", r"\2\n", content)
    return content

def ensure_telegram_files():
    """确保 utils/telegram.go 和 utils/telegram_test.go 绝不丢失"""
    os.makedirs(os.path.dirname(TELEGRAM_GO_PATH), exist_ok=True)
    if not os.path.exists(TELEGRAM_GO_PATH) or "NormalizeTelegramEndpoint" not in open(TELEGRAM_GO_PATH, "r", encoding="utf-8").read():
        with open(TELEGRAM_GO_PATH, "w", encoding="utf-8") as f:
            f.write(TELEGRAM_GO_CONTENT.strip() + "\n")
        print("[+] 成功还原/创建 utils/telegram.go！")
    else:
        print("[OK] utils/telegram.go 存在且完好。")

    if not os.path.exists(TELEGRAM_TEST_PATH):
        with open(TELEGRAM_TEST_PATH, "w", encoding="utf-8") as f:
            f.write(TELEGRAM_TEST_CONTENT.strip() + "\n")
        print("[+] 成功还原 utils/telegram_test.go！")
    return True

def ensure_config_go():
    if not os.path.exists(CONFIG_GO_PATH):
        print(f"[!] 未找到 {CONFIG_GO_PATH}")
        return False
    with open(CONFIG_GO_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = clean_conflict_markers(content)

    if "TelegramBotToken" in content and "TelegramChatID" in content and "ProxyTG" in content:
        print("[OK] config/config.go 已包含 TG 配置字段。")
        return True

    inject_fields = (
        "\tTelegramBotToken     string    `yaml:\"telegram-bot-token\"`\n"
        "\tTelegramChatID       string    `yaml:\"telegram-chat-id\"`\n"
        "\tProxyTG              string    `yaml:\"proxy-tg\"`\n"
    )

    patterns = [
        r"(NotifyTitle\s+string\s+`yaml:\"notify-title\"`\n)",
        r"(AppriseApiServer\s+string\s+`yaml:\"apprise-api-server\"`\n)",
        r"(type\s+Config\s+struct\s*\{[\s\S]*?)(ListenPort\s+string\s+`yaml:\"listen-port\"`\n)",
        r"(type\s+Config\s+struct\s*\{\n)",
    ]

    injected = False
    for pat in patterns:
        if re.search(pat, content):
            content = re.sub(pat, r"\1" + inject_fields, content, count=1)
            injected = True
            break

    if injected:
        with open(CONFIG_GO_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] 成功将 TG 字段自动注回 config/config.go！")
        return True
    return False

def ensure_config_yaml():
    if not os.path.exists(CONFIG_YAML_PATH):
        print(f"[!] 未找到 {CONFIG_YAML_PATH}")
        return False
    with open(CONFIG_YAML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = clean_conflict_markers(content)

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

    content = clean_conflict_markers(content)

    # 1. 确保必要包导入
    required_imports = ['"log/slog"', '"fmt"', '"github.com/beck-8/subs-check/config"']
    for req in required_imports:
        if req not in content:
            content = re.sub(r"(import\s*\([\s\S]*?)\)", r"\1\t" + req + "\n)", content, count=1)

    # 2. 确保 Telegram 推送调用
    if "SendTelegram" in content:
        print("[OK] utils/notify.go 已包含 SendTelegram 逻辑。")
        with open(NOTIFY_GO_PATH, "w", encoding="utf-8") as f:
            f.write(content)
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

    content = clean_conflict_markers(content)
    changed = False

    # 1. 替换 Docker 镜像
    if "ghcr.io/beck-8/subs-check" in content:
        content = content.replace("ghcr.io/beck-8/subs-check", "ghcr.io/xbajiu/subs-check")
        changed = True

    # 2. 补全 Telegram 推送章节
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
    print("=== 开始执行全量防冲突与自愈保底审查 ===")
    ok0 = ensure_telegram_files()
    ok1 = ensure_config_go()
    ok2 = ensure_config_yaml()
    ok3 = ensure_notify_go()
    ok4 = ensure_readme()

    if ok0 and ok1 and ok2 and ok3 and ok4:
        print("=== 所有核心关键代码审查通过：100% 具备防冲突自愈能力！ ===")
        sys.exit(0)
    else:
        print("=== 警告：部分检查未完全通过 ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
