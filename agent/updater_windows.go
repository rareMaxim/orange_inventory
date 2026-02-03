//go:build windows
// +build windows

package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// downloadUpdate завантажує нову версію агента
func downloadUpdate(config *Config, downloadURL string, expectedChecksum string) (string, error) {
	// Повний URL
	fullURL := config.ServerURL + downloadURL

	req, err := http.NewRequest("GET", fullURL, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)

	client := &http.Client{Timeout: 5 * time.Minute}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("сервер повернув статус %d", resp.StatusCode)
	}

	// Зберігаємо у тимчасовий файл
	exePath, _ := getExePath()
	tempPath := filepath.Join(filepath.Dir(exePath), "orange_agent_new.exe")

	outFile, err := os.Create(tempPath)
	if err != nil {
		return "", fmt.Errorf("не вдалося створити файл: %w", err)
	}

	// Одночасно записуємо і рахуємо checksum
	hasher := sha256.New()
	writer := io.MultiWriter(outFile, hasher)

	_, err = io.Copy(writer, resp.Body)
	outFile.Close()
	if err != nil {
		os.Remove(tempPath)
		return "", fmt.Errorf("помилка завантаження: %w", err)
	}

	// Перевіряємо checksum
	actualChecksum := hex.EncodeToString(hasher.Sum(nil))
	if expectedChecksum != "" && actualChecksum != expectedChecksum {
		os.Remove(tempPath)
		return "", fmt.Errorf("checksum не співпадає: очікувався %s, отримано %s", expectedChecksum, actualChecksum)
	}

	return tempPath, nil
}

// performUpdate виконує оновлення агента
func performUpdate(newExePath string) error {
	exePath, err := getExePath()
	if err != nil {
		return err
	}

	exeDir := filepath.Dir(exePath)
	oldPath := filepath.Join(exeDir, "orange_agent_old.exe")
	batPath := filepath.Join(exeDir, "update.bat")

	// Отримуємо PID поточного процесу для очікування завершення
	pid := os.Getpid()

	// Створюємо batch скрипт для оновлення
	// Скрипт чекає завершення поточного процесу, замінює файли і запускає новий exe
	batContent := fmt.Sprintf(`@echo off
setlocal

set "LOG_FILE=%s\update.log"
echo [%%date%% %%time%%] Update started >> "%%LOG_FILE%%"

:: Чекаємо поки поточний процес завершиться (до 30 секунд)
echo [%%date%% %%time%%] Waiting for process %d to exit... >> "%%LOG_FILE%%"
set /a count=0
:waitloop
tasklist /FI "PID eq %d" 2>nul | find "%d" >nul
if not errorlevel 1 (
    set /a count+=1
    if %%count%% lss 30 (
        timeout /t 1 /nobreak >nul
        goto waitloop
    )
    echo [%%date%% %%time%%] WARNING: Process still running after 30s >> "%%LOG_FILE%%"
)
echo [%%date%% %%time%%] Process exited >> "%%LOG_FILE%%"

:: Видаляємо стару резервну копію
if exist "%s" (
    del /f /q "%s"
    echo [%%date%% %%time%%] Deleted old backup >> "%%LOG_FILE%%"
)

:: Перейменовуємо поточний exe в old
if exist "%s" (
    move /y "%s" "%s"
    echo [%%date%% %%time%%] Moved current to old >> "%%LOG_FILE%%"
)

:: Переміщуємо новий exe на місце поточного
move /y "%s" "%s"
if errorlevel 1 (
    echo [%%date%% %%time%%] ERROR: Failed to move new exe >> "%%LOG_FILE%%"
    :: Відновлюємо старий файл
    if exist "%s" move /y "%s" "%s"
    goto cleanup
)
echo [%%date%% %%time%%] Moved new exe to current >> "%%LOG_FILE%%"

:: Видаляємо стару версію (опціонально)
if exist "%s" del /f /q "%s"

echo [%%date%% %%time%%] Update completed successfully >> "%%LOG_FILE%%"

:cleanup
:: Видаляємо цей batch файл
(goto) 2>nul & del /f /q "%%~f0"
`, exeDir, pid, pid, pid,
		oldPath, oldPath,
		exePath, exePath, oldPath,
		newExePath, exePath,
		oldPath, oldPath, exePath,
		oldPath, oldPath)

	// Записуємо batch скрипт
	if err := os.WriteFile(batPath, []byte(batContent), 0755); err != nil {
		return fmt.Errorf("не вдалося створити update.bat: %w", err)
	}
	// Отримуємо шлях до системного cmd.exe
	comSpec := os.Getenv("COMSPEC")
	if comSpec == "" {
		comSpec = "C:\\Windows\\System32\\cmd.exe" // fallback, якщо змінна порожня
	}
	// Запускаємо batch скрипт у фоновому режимі через cmd /c start
	// /min - мінімізоване вікно, /b - без нового вікна
	cmd := exec.Command(comSpec, "/c", "start", "/min", "", "cmd", "/c", batPath)
	cmd.Dir = exeDir
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("не вдалося запустити update.bat: %w", err)
	}

	log.Println("✓ Оновлення запущено. Наступний запуск використає нову версію.")
	return nil
}
