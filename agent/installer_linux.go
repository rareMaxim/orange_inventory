//go:build linux
// +build linux

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// --- ФУНКЦІЇ ВСТАНОВЛЕННЯ (Linux) ---

const systemdServiceContent = `[Unit]
Description=Orange Inventory Agent
After=network.target

[Service]
Type=oneshot
ExecStart=%s --silent
User=root

[Install]
WantedBy=multi-user.target
`

const systemdTimerContent = `[Unit]
Description=Orange Inventory Agent Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=%dm
AccuracySec=1min

[Install]
WantedBy=timers.target
`

// isAdmin перевіряє чи запущено з правами root
func isAdmin() bool {
	return os.Geteuid() == 0
}

// getExePath повертає повний шлях до executable
func getExePath() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	return filepath.Abs(exe)
}

// installTask створює systemd timer
func installTask() error {
	if !isAdmin() {
		return fmt.Errorf("потрібні права root. Запустіть з sudo")
	}

	exePath, err := getExePath()
	if err != nil {
		return fmt.Errorf("не вдалося отримати шлях до exe: %w", err)
	}

	// Перевіряємо наявність config.json
	configPath := filepath.Join(filepath.Dir(exePath), "config.json")
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return fmt.Errorf("config.json не знайдено. Створіть його перед встановленням")
	}

	// Копіюємо бінарник в /usr/local/bin
	destPath := "/usr/local/bin/orange_agent"
	if err := copyFile(exePath, destPath); err != nil {
		return fmt.Errorf("не вдалося скопіювати бінарник: %w", err)
	}
	os.Chmod(destPath, 0755)

	// Копіюємо конфіг
	destConfigPath := "/etc/orange_inventory/config.json"
	os.MkdirAll("/etc/orange_inventory", 0755)
	if err := copyFile(configPath, destConfigPath); err != nil {
		return fmt.Errorf("не вдалося скопіювати конфіг: %w", err)
	}

	// Створюємо systemd service
	servicePath := "/etc/systemd/system/orange-agent.service"
	serviceContent := fmt.Sprintf(systemdServiceContent, destPath)
	if err := os.WriteFile(servicePath, []byte(serviceContent), 0644); err != nil {
		return fmt.Errorf("не вдалося створити service файл: %w", err)
	}

	// Створюємо systemd timer
	timerPath := "/etc/systemd/system/orange-agent.timer"
	timerContent := fmt.Sprintf(systemdTimerContent, TaskInterval)
	if err := os.WriteFile(timerPath, []byte(timerContent), 0644); err != nil {
		return fmt.Errorf("не вдалося створити timer файл: %w", err)
	}

	// Перезавантажуємо systemd
	exec.Command("systemctl", "daemon-reload").Run()

	// Включаємо та запускаємо timer
	exec.Command("systemctl", "enable", "orange-agent.timer").Run()
	exec.Command("systemctl", "start", "orange-agent.timer").Run()

	// Запускаємо одразу
	exec.Command("systemctl", "start", "orange-agent.service").Run()

	return nil
}

// uninstallTask видаляє systemd timer та service
func uninstallTask() error {
	if !isAdmin() {
		return fmt.Errorf("потрібні права root. Запустіть з sudo")
	}

	// Зупиняємо та вимикаємо timer
	exec.Command("systemctl", "stop", "orange-agent.timer").Run()
	exec.Command("systemctl", "disable", "orange-agent.timer").Run()

	// Зупиняємо service
	exec.Command("systemctl", "stop", "orange-agent.service").Run()

	// Видаляємо файли
	os.Remove("/etc/systemd/system/orange-agent.service")
	os.Remove("/etc/systemd/system/orange-agent.timer")
	os.Remove("/usr/local/bin/orange_agent")

	// Перезавантажуємо systemd
	exec.Command("systemctl", "daemon-reload").Run()

	return nil
}

// showStatus показує статус timer
func showStatus() {
	fmt.Println("=== Timer Status ===")
	cmd := exec.Command("systemctl", "status", "orange-agent.timer")
	output, _ := cmd.CombinedOutput()
	fmt.Println(string(output))

	fmt.Println("\n=== Service Status ===")
	cmd = exec.Command("systemctl", "status", "orange-agent.service")
	output, _ = cmd.CombinedOutput()
	fmt.Println(string(output))

	fmt.Println("\n=== Timer List ===")
	cmd = exec.Command("systemctl", "list-timers", "orange-agent.timer")
	output, _ = cmd.CombinedOutput()
	fmt.Println(string(output))
}

// copyFile копіює файл
func copyFile(src, dst string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, data, 0644)
}
