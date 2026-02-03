//go:build linux
// +build linux

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
	tempPath := filepath.Join(filepath.Dir(exePath), "orange_agent_new")

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

	// Робимо файл виконуваним
	os.Chmod(tempPath, 0755)

	return tempPath, nil
}

// performUpdate виконує оновлення агента
func performUpdate(newExePath string) error {
	exePath, err := getExePath()
	if err != nil {
		return err
	}

	exeDir := filepath.Dir(exePath)
	oldPath := filepath.Join(exeDir, "orange_agent_old")
	scriptPath := filepath.Join(exeDir, "update.sh")

	// Отримуємо PID поточного процесу для очікування завершення
	pid := os.Getpid()

	// Створюємо shell скрипт для оновлення
	scriptContent := fmt.Sprintf(`#!/bin/bash
LOG_FILE="%s/update.log"
echo "[$(date)] Update started" >> "$LOG_FILE"

# Чекаємо поки поточний процес завершиться (до 30 секунд)
echo "[$(date)] Waiting for process %d to exit..." >> "$LOG_FILE"
count=0
while kill -0 %d 2>/dev/null; do
    count=$((count + 1))
    if [ $count -ge 30 ]; then
        echo "[$(date)] WARNING: Process still running after 30s" >> "$LOG_FILE"
        break
    fi
    sleep 1
done
echo "[$(date)] Process exited" >> "$LOG_FILE"

# Видаляємо стару резервну копію
if [ -f "%s" ]; then
    rm -f "%s"
    echo "[$(date)] Deleted old backup" >> "$LOG_FILE"
fi

# Перейменовуємо поточний бінарник в old
if [ -f "%s" ]; then
    mv -f "%s" "%s"
    echo "[$(date)] Moved current to old" >> "$LOG_FILE"
fi

# Переміщуємо новий бінарник на місце поточного
mv -f "%s" "%s"
if [ $? -ne 0 ]; then
    echo "[$(date)] ERROR: Failed to move new binary" >> "$LOG_FILE"
    # Відновлюємо старий файл
    if [ -f "%s" ]; then
        mv -f "%s" "%s"
    fi
    exit 1
fi
echo "[$(date)] Moved new binary to current" >> "$LOG_FILE"

# Видаляємо стару версію
rm -f "%s"

# Оновлюємо systemd якщо встановлено
if [ -f "/etc/systemd/system/orange-agent.service" ]; then
    # Копіюємо новий бінарник
    cp -f "%s" "/usr/local/bin/orange_agent"
    chmod 755 "/usr/local/bin/orange_agent"
    systemctl daemon-reload
fi

echo "[$(date)] Update completed successfully" >> "$LOG_FILE"

# Видаляємо цей скрипт
rm -f "%s"
`, exeDir, pid, pid,
		oldPath, oldPath,
		exePath, exePath, oldPath,
		newExePath, exePath,
		oldPath, oldPath, exePath,
		oldPath,
		exePath,
		scriptPath)

	// Записуємо shell скрипт
	if err := os.WriteFile(scriptPath, []byte(scriptContent), 0755); err != nil {
		return fmt.Errorf("не вдалося створити update.sh: %w", err)
	}

	// Запускаємо скрипт у фоновому режимі
	cmd := exec.Command("/bin/bash", scriptPath)
	cmd.Dir = exeDir
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("не вдалося запустити update.sh: %w", err)
	}

	log.Println("✓ Оновлення запущено. Наступний запуск використає нову версію.")
	return nil
}
