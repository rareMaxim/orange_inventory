//go:build windows
// +build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// --- ФУНКЦІЇ ВСТАНОВЛЕННЯ (Windows) ---

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

// installTask створює заплановані завдання Windows
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

	// Видаляємо існуючі завдання
	exec.Command("schtasks", "/delete", "/tn", TaskName, "/f").Run()
	exec.Command("schtasks", "/delete", "/tn", TaskNameCommands, "/f").Run()

	// 1. Створюємо завдання для повного збору даних (кожні 15 хв)
	fmt.Printf("Створення завдання '%s' (кожні %d хв)...\n", TaskName, TaskInterval)
	cmd := exec.Command("schtasks", "/create",
		"/tn", TaskName,
		"/tr", fmt.Sprintf("\"%s\" --silent", exePath),
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

	// 2. Створюємо завдання для перевірки команд (кожну хвилину)
	fmt.Printf("Створення завдання '%s' (кожні %d хв)...\n", TaskNameCommands, CommandPollInterval)
	cmd = exec.Command("schtasks", "/create",
		"/tn", TaskNameCommands,
		"/tr", fmt.Sprintf("\"%s\" --commands-only --silent", exePath),
		"/sc", "MINUTE",
		"/mo", fmt.Sprintf("%d", CommandPollInterval),
		"/ru", "SYSTEM",
		"/rl", "HIGHEST",
		"/f",
	)

	output, err = cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("помилка створення завдання команд: %w\n%s", err, string(output))
	}

	// Запускаємо повний збір одразу
	exec.Command("schtasks", "/run", "/tn", TaskName).Run()

	return nil
}

// uninstallTask видаляє заплановані завдання Windows
func uninstallTask() error {
	if !isAdmin() {
		return fmt.Errorf("потрібні права адміністратора. Запустіть як Administrator")
	}

	// Зупиняємо та видаляємо обидва завдання
	exec.Command("schtasks", "/end", "/tn", TaskName).Run()
	exec.Command("schtasks", "/end", "/tn", TaskNameCommands).Run()

	// Видаляємо основне завдання
	cmd := exec.Command("schtasks", "/delete", "/tn", TaskName, "/f")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("⚠ Не вдалося видалити '%s': %s\n", TaskName, string(output))
	} else {
		fmt.Printf("✓ Видалено '%s'\n", TaskName)
	}

	// Видаляємо завдання команд
	cmd = exec.Command("schtasks", "/delete", "/tn", TaskNameCommands, "/f")
	output, err = cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("⚠ Не вдалося видалити '%s': %s\n", TaskNameCommands, string(output))
	} else {
		fmt.Printf("✓ Видалено '%s'\n", TaskNameCommands)
	}

	return nil
}

// showStatus показує статус завдань
func showStatus() {
	fmt.Println("=== Основне завдання (збір даних) ===")
	cmd := exec.Command("schtasks", "/query", "/tn", TaskName, "/v", "/fo", "LIST")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Завдання '%s' не знайдено\n\n", TaskName)
	} else {
		fmt.Println(string(output))
	}

	fmt.Println("=== Завдання команд (polling) ===")
	cmd = exec.Command("schtasks", "/query", "/tn", TaskNameCommands, "/v", "/fo", "LIST")
	output, err = cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Завдання '%s' не знайдено\n", TaskNameCommands)
	} else {
		fmt.Println(string(output))
	}
}
