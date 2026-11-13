package utils

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
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
		messageText = fmt.Sprintf("%s\n\n%s", title, body)
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

	// 进一步检查 Telegram API 返回的 JSON 格式 {"ok": true, ...}
	var tgResp struct {
		OK          bool   `json:"ok"`
		Description string `json:"description"`
	}
	if err := json.Unmarshal(respBody, &tgResp); err == nil && !tgResp.OK {
		return fmt.Errorf("Telegram 返回错误: %s", tgResp.Description)
	}

	return nil
}
