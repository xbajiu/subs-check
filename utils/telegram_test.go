package utils

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
