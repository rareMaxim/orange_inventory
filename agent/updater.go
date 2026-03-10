package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// --- ФУНКЦІЇ ОНОВЛЕННЯ (спільні) ---

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
func checkForUpdate(config *Config, agentID string) (*UpdateResponse, error) {
	apiURL := config.ServerURL + "/api/method/orange_inventory.update_api.check_update"

	// Формуємо запит
	payload := map[string]string{
		"current_version": AppVersion,
		"agent_id":        agentID,
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
