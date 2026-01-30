package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// --- ФУНКЦІЇ ОНОВЛЕННЯ ---

// UpdateResponse представляє відповідь від сервера про оновлення
type UpdateResponse struct {
	Message struct {
		UpdateAvailable bool   `json:"update_available"`
		LatestVersion   string `json:"latest_version"`
		IsMandatory     bool   `json:"is_mandatory"`
		DownloadURL     string `json:"download_url"`
		FileSize        int64  `json:"file_size"`
		Checksum        string `json:"checksum"`
		ReleaseNotes    string `json:"release_notes"`
		Msg             string `json:"message"`
	} `json:"message"`
}

// checkForUpdate перевіряє наявність оновлень на сервері
func checkForUpdate(config *Config) (*UpdateResponse, error) {
	apiURL := config.ServerURL + "/api/method/orange_inventory.update_api.check_update"

	// Формуємо запит
	payload := map[string]string{
		"current_version": AppVersion,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

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

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var updateResp UpdateResponse
	if err := json.Unmarshal(respBody, &updateResp); err != nil {
		return nil, err
	}

	return &updateResp, nil
}

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

	// Запускаємо batch скрипт у фоновому режимі через cmd /c start
	// /min - мінімізоване вікно, /b - без нового вікна
	cmd := exec.Command("cmd", "/c", "start", "/min", "", "cmd", "/c", batPath)
	cmd.Dir = exeDir
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("не вдалося запустити update.bat: %w", err)
	}

	log.Println("✓ Оновлення запущено. Наступний запуск використає нову версію.")
	return nil
}

// compareVersions порівнює дві версії
// Повертає: 1 якщо v1 > v2, -1 якщо v1 < v2, 0 якщо рівні
func compareVersions(v1, v2 string) int {
	parse := func(v string) []int {
		parts := strings.Split(strings.ReplaceAll(v, "-", "."), ".")
		result := make([]int, 0, len(parts))
		for _, p := range parts {
			if n, err := strconv.Atoi(p); err == nil {
				result = append(result, n)
			}
		}
		return result
	}

	p1 := parse(v1)
	p2 := parse(v2)

	maxLen := len(p1)
	if len(p2) > maxLen {
		maxLen = len(p2)
	}

	for i := 0; i < maxLen; i++ {
		var n1, n2 int
		if i < len(p1) {
			n1 = p1[i]
		}
		if i < len(p2) {
			n2 = p2[i]
		}

		if n1 > n2 {
			return 1
		}
		if n1 < n2 {
			return -1
		}
	}

	return 0
}
