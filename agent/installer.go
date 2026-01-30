package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// --- ФУНКЦІЇ ВСТАНОВЛЕННЯ ---

// isAdmin перевіряє чи запущено з правами адміністратора
func isAdmin() bool {
	_, err := os.Open("\\\\.\\PHYSICALDRIVE0")
	return err == nil
}

// getExePath повертає повний шлях до executable
func getExePath() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	return filepath.Abs(exe)
}

// installTask створює заплановане завдання Windows
func installTask() error {
	if !isAdmin() {
		return fmt.Errorf("потрібні права адміністратора. Запустіть як Administrator")
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

	// Видаляємо існуюче завдання
	exec.Command("schtasks", "/delete", "/tn", TaskName, "/f").Run()

	// Створюємо нове завдання
	cmd := exec.Command("schtasks", "/create",
		"/tn", TaskName,
		"/tr", fmt.Sprintf("\"%s\"", exePath),
		"/sc", "MINUTE",
		"/mo", fmt.Sprintf("%d", TaskInterval),
		"/ru", "SYSTEM",
		"/rl", "HIGHEST",
		"/f",
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("помилка створення завдання: %w\n%s", err, string(output))
	}

	// Запускаємо завдання одразу
	exec.Command("schtasks", "/run", "/tn", TaskName).Run()

	return nil
}

// uninstallTask видаляє заплановане завдання Windows
func uninstallTask() error {
	if !isAdmin() {
		return fmt.Errorf("потрібні права адміністратора. Запустіть як Administrator")
	}

	// Зупиняємо завдання
	exec.Command("schtasks", "/end", "/tn", TaskName).Run()

	// Видаляємо завдання
	cmd := exec.Command("schtasks", "/delete", "/tn", TaskName, "/f")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("помилка видалення завдання: %w\n%s", err, string(output))
	}

	return nil
}

// showStatus показує статус завдання
func showStatus() {
	cmd := exec.Command("schtasks", "/query", "/tn", TaskName, "/v", "/fo", "LIST")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Завдання '%s' не знайдено\n", TaskName)
		return
	}
	fmt.Println(string(output))
}
