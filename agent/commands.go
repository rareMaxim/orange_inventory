package main

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os/exec"
	"runtime"
	"time"
)

// Command представляє команду від сервера
type Command struct {
	ID        string                 `json:"id"`
	Type      string                 `json:"type"`
	Command   string                 `json:"command"`
	Arguments map[string]interface{} `json:"arguments"`
	Timeout   int                    `json:"timeout"`
	Signature string                 `json:"signature"`  // HMAC-SHA256 підпис
	ExpiresAt string                 `json:"expires_at"` // Термін дії команди
}

// CommandsResponse відповідь сервера зі списком команд
type CommandsResponse struct {
	Message struct {
		Commands []Command `json:"commands"`
		Error    string    `json:"error,omitempty"`
	} `json:"message"`
}

// CommandResult результат виконання команди
type CommandResult struct {
	CommandID   string `json:"command_id"`
	Status      string `json:"status"`
	ExitCode    int    `json:"exit_code"`
	Output      string `json:"output"`
	ErrorOutput string `json:"error_output"`
}

// verifyCommandSignature перевіряє HMAC підпис команди
func verifyCommandSignature(cmd Command, agentID string, signingKey string) bool {
	if signingKey == "" {
		// Якщо ключ не налаштовано - пропускаємо перевірку (зворотна сумісність)
		log.Println("⚠ command_signing_key не налаштовано - підпис не перевіряється")
		return true
	}

	if cmd.Signature == "" {
		log.Println("⚠ Команда без підпису - відхилено")
		return false
	}

	// Формуємо повідомлення для перевірки (має співпадати з сервером)
	message := fmt.Sprintf("%s:%s:%s:%s", cmd.ID, agentID, cmd.Command, cmd.ExpiresAt)

	// Обчислюємо HMAC-SHA256
	h := hmac.New(sha256.New, []byte(signingKey))
	h.Write([]byte(message))
	expectedSignature := hex.EncodeToString(h.Sum(nil))

	// Порівнюємо з отриманим підписом (константний час)
	return hmac.Equal([]byte(expectedSignature), []byte(cmd.Signature))
}

// isCommandExpired перевіряє чи команда протермінована
func isCommandExpired(expiresAt string) bool {
	if expiresAt == "" || expiresAt == "None" {
		return false // Без терміну дії
	}

	// Парсимо час (формат: 2006-01-02 15:04:05)
	expires, err := time.Parse("2006-01-02 15:04:05", expiresAt)
	if err != nil {
		// Спробуємо інший формат з мікросекундами
		expires, err = time.Parse("2006-01-02 15:04:05.000000", expiresAt)
		if err != nil {
			log.Printf("⚠ Не вдалося розпарсити expires_at: %s", expiresAt)
			return true // На всяк випадок відхиляємо
		}
	}

	return time.Now().After(expires)
}

// fetchPendingCommands отримує команди з сервера
func fetchPendingCommands(config *Config, agentID string) ([]Command, error) {
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.get_pending_commands"

	// Формуємо запит
	payload := map[string]string{"agent_id": agentID}
	body, _ := json.Marshal(payload)

	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("сервер повернув %d", resp.StatusCode)
	}

	var result CommandsResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	if result.Message.Error != "" {
		return nil, fmt.Errorf(result.Message.Error)
	}

	return result.Message.Commands, nil
}

// reportCommandResult повідомляє результат на сервер
func reportCommandResult(config *Config, result CommandResult) error {
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.report_command_result"

	body, _ := json.Marshal(result)

	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(body))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("сервер повернув %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

// executeCommand виконує команду
func executeCommand(cmd Command) CommandResult {
	result := CommandResult{
		CommandID: cmd.ID,
		Status:    "Running",
	}

	timeout := time.Duration(cmd.Timeout) * time.Second
	if timeout == 0 {
		timeout = 60 * time.Second
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	var execCmd *exec.Cmd

	switch cmd.Type {
	case "PowerShell":
		if runtime.GOOS == "windows" {
			execCmd = exec.CommandContext(ctx, "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd.Command)
		} else {
			// Linux - використовуємо pwsh якщо є, інакше bash
			execCmd = exec.CommandContext(ctx, "bash", "-c", cmd.Command)
		}

	case "CMD":
		if runtime.GOOS == "windows" {
			execCmd = exec.CommandContext(ctx, "cmd", "/c", cmd.Command)
		} else {
			execCmd = exec.CommandContext(ctx, "sh", "-c", cmd.Command)
		}

	case "Restart Service":
		if runtime.GOOS == "windows" {
			execCmd = exec.CommandContext(ctx, "powershell", "-Command",
				fmt.Sprintf("Restart-Service -Name '%s' -Force", cmd.Command))
		} else {
			execCmd = exec.CommandContext(ctx, "systemctl", "restart", cmd.Command)
		}

	case "Reboot":
		if runtime.GOOS == "windows" {
			execCmd = exec.CommandContext(ctx, "shutdown", "/r", "/t", "30", "/c", "Orange Inventory: Remote reboot")
		} else {
			execCmd = exec.CommandContext(ctx, "shutdown", "-r", "+1", "Orange Inventory: Remote reboot")
		}

	case "Shutdown":
		if runtime.GOOS == "windows" {
			execCmd = exec.CommandContext(ctx, "shutdown", "/s", "/t", "30", "/c", "Orange Inventory: Remote shutdown")
		} else {
			execCmd = exec.CommandContext(ctx, "shutdown", "-h", "+1", "Orange Inventory: Remote shutdown")
		}

	default:
		result.Status = "Failed"
		result.ErrorOutput = fmt.Sprintf("Невідомий тип команди: %s", cmd.Type)
		return result
	}

	// Виконуємо команду
	var stdout, stderr bytes.Buffer
	execCmd.Stdout = &stdout
	execCmd.Stderr = &stderr

	err := execCmd.Run()

	result.Output = stdout.String()
	result.ErrorOutput = stderr.String()

	if ctx.Err() == context.DeadlineExceeded {
		result.Status = "Timeout"
		result.ExitCode = -1
		return result
	}

	if err != nil {
		result.Status = "Failed"
		if exitError, ok := err.(*exec.ExitError); ok {
			result.ExitCode = exitError.ExitCode()
		} else {
			result.ExitCode = -1
			result.ErrorOutput = err.Error()
		}
	} else {
		result.Status = "Completed"
		result.ExitCode = 0
	}

	return result
}

// processCommands отримує та виконує команди
func processCommands(config *Config, agentID string) {
	commands, err := fetchPendingCommands(config, agentID)
	if err != nil {
		log.Printf("⚠ Помилка отримання команд: %v", err)
		return
	}

	if len(commands) == 0 {
		return
	}

	log.Printf("📥 Отримано %d команд для виконання", len(commands))

	for _, cmd := range commands {
		log.Printf("▶ Обробка команди %s (%s)", cmd.ID, cmd.Type)

		// Перевірка терміну дії
		if isCommandExpired(cmd.ExpiresAt) {
			log.Printf("  ⏰ Команда протермінована - пропускаємо")
			result := CommandResult{
				CommandID:   cmd.ID,
				Status:      "Failed",
				ExitCode:    -1,
				ErrorOutput: "Команда протермінована на момент виконання",
			}
			reportCommandResult(config, result)
			continue
		}

		// Перевірка підпису
		if !verifyCommandSignature(cmd, agentID, config.CommandSigningKey) {
			log.Printf("  🔒 Невалідний підпис команди - відхилено")
			result := CommandResult{
				CommandID:   cmd.ID,
				Status:      "Failed",
				ExitCode:    -1,
				ErrorOutput: "Невалідний підпис команди",
			}
			reportCommandResult(config, result)
			continue
		}

		log.Printf("  ✓ Підпис верифіковано, виконуємо...")
		result := executeCommand(cmd)

		log.Printf("  Результат: %s (exit code: %d)", result.Status, result.ExitCode)

		// Повідомляємо результат на сервер
		if err := reportCommandResult(config, result); err != nil {
			log.Printf("⚠ Не вдалося повідомити результат: %v", err)
		}
	}
}
