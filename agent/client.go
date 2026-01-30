package main

import (
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

// --- КОНСТАНТИ RETRY ---
const (
	MaxRetries     = 5
	InitialBackoff = 1 * time.Second
	MaxBackoff     = 32 * time.Second
	QueueFileName  = "offline_queue.json"
)

// --- КОМУНІКАЦІЯ З СЕРВЕРОМ ---

// ServerResponse представляє відповідь від сервера
type ServerResponse struct {
	Message struct {
		Status    string `json:"status"`
		AssetName string `json:"asset_name"`
		Created   bool   `json:"created"`
		Msg       string `json:"message"`
	} `json:"message"`
	Exception string `json:"exc,omitempty"`
}

// QueuedRequest представляє запит у черзі
type QueuedRequest struct {
	StaticData  string    `json:"static_data"`
	DynamicData string    `json:"dynamic_data"`
	Timestamp   time.Time `json:"timestamp"`
	Attempts    int       `json:"attempts"`
}

// sendToServer відправляє дані на Frappe сервер з retry логікою
func sendToServer(config *Config, static StaticData, dynamic DynamicData) error {
	// Серіалізуємо дані в JSON
	staticJSON, err := json.Marshal(static)
	if err != nil {
		return fmt.Errorf("помилка серіалізації static_data: %w", err)
	}

	dynamicJSON, err := json.Marshal(dynamic)
	if err != nil {
		return fmt.Errorf("помилка серіалізації dynamic_data: %w", err)
	}

	// Спочатку спробуємо відправити дані з черги (якщо є)
	processOfflineQueue(config)

	// Відправляємо поточні дані
	err = sendWithRetry(config, string(staticJSON), string(dynamicJSON))
	if err != nil {
		// Якщо не вдалося - додаємо до черги
		log.Printf("⚠ Не вдалося відправити дані, додаємо до черги: %v", err)
		addToOfflineQueue(string(staticJSON), string(dynamicJSON))
		return err
	}

	return nil
}

// sendWithRetry відправляє запит з exponential backoff
func sendWithRetry(config *Config, staticJSON, dynamicJSON string) error {
	var lastErr error

	for attempt := 0; attempt < MaxRetries; attempt++ {
		if attempt > 0 {
			// Exponential backoff: 1s, 2s, 4s, 8s, 16s...
			backoff := time.Duration(math.Pow(2, float64(attempt-1))) * InitialBackoff
			if backoff > MaxBackoff {
				backoff = MaxBackoff
			}
			log.Printf("⏳ Спроба %d/%d через %v...", attempt+1, MaxRetries, backoff)
			time.Sleep(backoff)
		}

		err := doSendRequest(config, staticJSON, dynamicJSON)
		if err == nil {
			return nil // Успіх
		}

		lastErr = err

		// Якщо це помилка авторизації або бізнес-логіки - не повторюємо
		if isNonRetryableError(err) {
			return err
		}

		log.Printf("⚠ Спроба %d/%d невдала: %v", attempt+1, MaxRetries, err)
	}

	return fmt.Errorf("всі %d спроб невдалі: %w", MaxRetries, lastErr)
}

// compressGzip стискає дані за допомогою gzip
func compressGzip(data []byte) ([]byte, error) {
	var buf bytes.Buffer
	gz := gzip.NewWriter(&buf)
	if _, err := gz.Write(data); err != nil {
		return nil, err
	}
	if err := gz.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// doSendRequest виконує один HTTP запит
func doSendRequest(config *Config, staticJSON, dynamicJSON string) error {
	// Формуємо payload для Frappe API
	payload := map[string]string{
		"static_data":  staticJSON,
		"dynamic_data": dynamicJSON,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("помилка формування payload: %w", err)
	}

	// Стискаємо payload gzip
	originalSize := len(body)
	compressedBody, err := compressGzip(body)
	if err != nil {
		// Якщо стиснення не вдалось - відправляємо без стиснення
		log.Printf("⚠ Помилка стиснення, відправляємо без gzip: %v", err)
		compressedBody = body
	}
	compressedSize := len(compressedBody)
	compressionRatio := float64(originalSize-compressedSize) / float64(originalSize) * 100

	log.Printf("📦 Стиснення: %d → %d байт (%.1f%% економії)", originalSize, compressedSize, compressionRatio)

	// Формуємо URL для API
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.report_machine_data"

	// Створюємо HTTP запит
	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(compressedBody))
	if err != nil {
		return fmt.Errorf("помилка створення запиту: %w", err)
	}

	// Встановлюємо заголовки
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Content-Encoding", "gzip")
	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)
	req.Header.Set("Accept", "application/json")

	// Виконуємо запит з таймаутом
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return &NetworkError{Err: err}
	}
	defer resp.Body.Close()

	// Читаємо відповідь
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("помилка читання відповіді: %w", err)
	}

	// Перевіряємо статус код
	if resp.StatusCode >= 500 {
		// Серверні помилки - можна повторювати
		return &ServerError{StatusCode: resp.StatusCode, Body: string(respBody)}
	}

	if resp.StatusCode != 200 {
		// Клієнтські помилки (4xx) - не повторюємо
		return &ClientError{StatusCode: resp.StatusCode, Body: string(respBody)}
	}

	// Парсимо відповідь
	var serverResp ServerResponse
	if err := json.Unmarshal(respBody, &serverResp); err != nil {
		return fmt.Errorf("невалідна відповідь сервера: %w", err)
	}

	// Перевіряємо на помилки
	if serverResp.Exception != "" {
		return &ClientError{StatusCode: 200, Body: serverResp.Exception}
	}

	// Логуємо успішний результат
	if serverResp.Message.Created {
		log.Printf("✓ Створено новий актив: %s", serverResp.Message.AssetName)
	} else {
		log.Printf("✓ Оновлено актив: %s", serverResp.Message.AssetName)
	}

	return nil
}

// --- ТИПИ ПОМИЛОК ---

// NetworkError - помилка мережі (можна повторювати)
type NetworkError struct {
	Err error
}

func (e *NetworkError) Error() string {
	return fmt.Sprintf("помилка мережі: %v", e.Err)
}

// ServerError - серверна помилка 5xx (можна повторювати)
type ServerError struct {
	StatusCode int
	Body       string
}

func (e *ServerError) Error() string {
	return fmt.Sprintf("серверна помилка %d: %s", e.StatusCode, e.Body)
}

// ClientError - клієнтська помилка 4xx (не повторювати)
type ClientError struct {
	StatusCode int
	Body       string
}

func (e *ClientError) Error() string {
	return fmt.Sprintf("клієнтська помилка %d: %s", e.StatusCode, e.Body)
}

// isNonRetryableError перевіряє чи помилку не варто повторювати
func isNonRetryableError(err error) bool {
	_, isClientErr := err.(*ClientError)
	return isClientErr
}

// --- OFFLINE QUEUE ---

// getQueuePath повертає шлях до файлу черги
func getQueuePath() string {
	exePath, _ := getExePath()
	return filepath.Join(filepath.Dir(exePath), QueueFileName)
}

// loadOfflineQueue завантажує чергу з файлу
func loadOfflineQueue() []QueuedRequest {
	queuePath := getQueuePath()
	data, err := os.ReadFile(queuePath)
	if err != nil {
		return []QueuedRequest{}
	}

	var queue []QueuedRequest
	if err := json.Unmarshal(data, &queue); err != nil {
		return []QueuedRequest{}
	}

	return queue
}

// saveOfflineQueue зберігає чергу у файл
func saveOfflineQueue(queue []QueuedRequest) error {
	queuePath := getQueuePath()
	data, err := json.MarshalIndent(queue, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(queuePath, data, 0644)
}

// addToOfflineQueue додає запит до черги
func addToOfflineQueue(staticJSON, dynamicJSON string) {
	queue := loadOfflineQueue()

	// Обмежуємо розмір черги (максимум 100 записів)
	if len(queue) >= 100 {
		// Видаляємо найстаріший запис
		queue = queue[1:]
	}

	queue = append(queue, QueuedRequest{
		StaticData:  staticJSON,
		DynamicData: dynamicJSON,
		Timestamp:   time.Now(),
		Attempts:    0,
	})

	if err := saveOfflineQueue(queue); err != nil {
		log.Printf("⚠ Не вдалося зберегти чергу: %v", err)
	} else {
		log.Printf("📥 Запит додано до черги (всього в черзі: %d)", len(queue))
	}
}

// processOfflineQueue обробляє запити з черги
func processOfflineQueue(config *Config) {
	queue := loadOfflineQueue()
	if len(queue) == 0 {
		return
	}

	log.Printf("📤 Обробка черги: %d запитів...", len(queue))

	var newQueue []QueuedRequest
	successCount := 0

	for _, req := range queue {
		// Пропускаємо занадто старі запити (> 24 години)
		if time.Since(req.Timestamp) > 24*time.Hour {
			log.Printf("⏭ Пропускаємо застарілий запит від %v", req.Timestamp)
			continue
		}

		// Пробуємо відправити (без retry, бо це вже черга)
		err := doSendRequest(config, req.StaticData, req.DynamicData)
		if err != nil {
			req.Attempts++
			// Якщо занадто багато спроб - видаляємо
			if req.Attempts >= 10 {
				log.Printf("⏭ Видаляємо запит після %d спроб", req.Attempts)
				continue
			}
			newQueue = append(newQueue, req)
		} else {
			successCount++
		}
	}

	if successCount > 0 {
		log.Printf("✓ Успішно відправлено %d запитів з черги", successCount)
	}

	// Зберігаємо оновлену чергу
	if err := saveOfflineQueue(newQueue); err != nil {
		log.Printf("⚠ Не вдалося оновити чергу: %v", err)
	}

	if len(newQueue) > 0 {
		log.Printf("📋 Залишилось в черзі: %d запитів", len(newQueue))
	}
}

// GetQueueStatus повертає статус черги
func GetQueueStatus() (int, time.Time) {
	queue := loadOfflineQueue()
	if len(queue) == 0 {
		return 0, time.Time{}
	}
	return len(queue), queue[0].Timestamp
}
