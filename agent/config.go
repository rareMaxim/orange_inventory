package main

import (
	"encoding/json"
	"fmt"
	"os"
)

// --- КОНФІГУРАЦІЯ ---

// Config містить налаштування для підключення до сервера
type Config struct {
	ServerURL         string `json:"server_url"`          // URL Frappe сервера (наприклад: https://your-site.com)
	APIKey            string `json:"api_key"`             // API ключ користувача
	APISecret         string `json:"api_secret"`          // API секрет користувача
	CommandSigningKey string `json:"command_signing_key"` // Ключ для верифікації підписів команд (опціонально)
}

// loadConfig завантажує конфігурацію з файлу config.json
func loadConfig() (*Config, error) {
	// Шукаємо config.json в тій же директорії що і executable
	exePath, err := os.Executable()
	if err != nil {
		return nil, fmt.Errorf("не вдалося отримати шлях до executable: %w", err)
	}

	// Отримуємо директорію executable
	exeDir := exePath[:len(exePath)-len("orange_agent.exe")]
	configPath := exeDir + "config.json"

	// Спробуємо прочитати з директорії executable
	data, err := os.ReadFile(configPath)
	if err != nil {
		// Якщо не знайдено - пробуємо поточну директорію
		data, err = os.ReadFile("config.json")
		if err != nil {
			return nil, fmt.Errorf("не вдалося прочитати config.json: %w", err)
		}
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("невалідний JSON у config.json: %w", err)
	}

	// Перевіряємо обов'язкові поля
	if config.ServerURL == "" {
		return nil, fmt.Errorf("server_url обов'язковий у config.json")
	}
	if config.APIKey == "" || config.APISecret == "" {
		return nil, fmt.Errorf("api_key та api_secret обов'язкові у config.json")
	}

	return &config, nil
}
