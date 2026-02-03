//go:build windows
// +build windows

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os/exec"
	"strings"
	"time"

	"golang.org/x/sys/windows/registry"
)

// BlockedSoftware представляє заблоковану програму
type BlockedSoftware struct {
	Name        string   `json:"name"`
	Executables []string `json:"executables"`
	Reason      string   `json:"reason"`
}

// BlockedResponse відповідь сервера зі списком заблокованих програм
type BlockedResponse struct {
	Message struct {
		Blocked []BlockedSoftware `json:"blocked"`
		Version string            `json:"version"`
		Count   int               `json:"count"`
	} `json:"message"`
}

// Константи для Software Restriction Policies
const (
	SRPBasePath      = `SOFTWARE\Policies\Microsoft\Windows\Safer\CodeIdentifiers`
	SRP0Path         = SRPBasePath + `\0\Paths`
	PolicyVersionKey = "OrangeInventoryPolicyVersion"
)

// fetchBlockedSoftware отримує список заблокованого ПЗ з сервера
func fetchBlockedSoftware(config *Config) (*BlockedResponse, error) {
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.get_blocked_software"

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, fmt.Errorf("помилка створення запиту: %w", err)
	}

	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)
	req.Header.Set("Accept", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("помилка HTTP запиту: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("сервер повернув %d: %s", resp.StatusCode, string(body))
	}

	var result BlockedResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("помилка парсингу відповіді: %w", err)
	}

	return &result, nil
}

// getCurrentPolicyVersion отримує поточну версію політик з реєстру
func getCurrentPolicyVersion() string {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, SRPBasePath, registry.READ)
	if err != nil {
		return ""
	}
	defer key.Close()

	version, _, err := key.GetStringValue(PolicyVersionKey)
	if err != nil {
		return ""
	}
	return version
}

// setPolicyVersion зберігає версію політик в реєстрі
func setPolicyVersion(version string) error {
	key, _, err := registry.CreateKey(registry.LOCAL_MACHINE, SRPBasePath, registry.WRITE)
	if err != nil {
		return err
	}
	defer key.Close()

	return key.SetStringValue(PolicyVersionKey, version)
}

// enableSRP вмикає Software Restriction Policies
func enableSRP() error {
	// Створюємо базовий ключ SRP
	key, _, err := registry.CreateKey(registry.LOCAL_MACHINE, SRPBasePath, registry.WRITE)
	if err != nil {
		return fmt.Errorf("не вдалося створити ключ SRP: %w", err)
	}
	defer key.Close()

	// DefaultLevel = 262144 (Unrestricted) - дозволяємо все за замовчуванням
	if err := key.SetDWordValue("DefaultLevel", 262144); err != nil {
		return err
	}

	// PolicyScope = 0 (всі користувачі крім адміністраторів)
	if err := key.SetDWordValue("PolicyScope", 0); err != nil {
		return err
	}

	// TransparentEnabled = 1 (перевіряти DLL)
	if err := key.SetDWordValue("TransparentEnabled", 1); err != nil {
		return err
	}

	// ExecutableTypes - типи файлів для перевірки
	execTypes := []string{"ADE", "ADP", "BAS", "BAT", "CHM", "CMD", "COM", "CPL", "CRT",
		"EXE", "HLP", "HTA", "INF", "INS", "ISP", "LNK", "MDB", "MDE", "MSC", "MSI",
		"MSP", "MST", "OCX", "PCD", "PIF", "REG", "SCR", "SHS", "URL", "VB", "WSC"}
	if err := key.SetStringsValue("ExecutableTypes", execTypes); err != nil {
		return err
	}

	// Створюємо підключ для Disallowed (Level 0)
	_, _, err = registry.CreateKey(registry.LOCAL_MACHINE, SRP0Path, registry.WRITE)
	if err != nil {
		return fmt.Errorf("не вдалося створити ключ Paths: %w", err)
	}

	return nil
}

// blockExecutable блокує конкретний виконуваний файл
func blockExecutable(executable string, reason string) error {
	// Створюємо унікальний GUID для правила
	guid := generateGUID(executable)
	rulePath := SRP0Path + `\` + guid

	key, _, err := registry.CreateKey(registry.LOCAL_MACHINE, rulePath, registry.WRITE)
	if err != nil {
		return fmt.Errorf("не вдалося створити правило: %w", err)
	}
	defer key.Close()

	// ItemData - шлях до файлу (використовуємо wildcard)
	itemData := "*\\" + executable
	if err := key.SetStringValue("ItemData", itemData); err != nil {
		return err
	}

	// SaferFlags = 0
	if err := key.SetDWordValue("SaferFlags", 0); err != nil {
		return err
	}

	// Description
	if err := key.SetStringValue("Description", "Orange Inventory: "+reason); err != nil {
		return err
	}

	// LastModified
	if err := key.SetQWordValue("LastModified", uint64(time.Now().Unix())); err != nil {
		return err
	}

	return nil
}

// generateGUID генерує унікальний GUID для правила
func generateGUID(input string) string {
	// Простий хеш для створення псевдо-GUID
	hash := 0
	for _, c := range input {
		hash = 31*hash + int(c)
	}
	return fmt.Sprintf("{%08X-0000-0000-0000-000000000000}", uint32(hash))
}

// clearAllBlockRules видаляє всі правила блокування Orange Inventory
func clearAllBlockRules() error {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, SRP0Path, registry.READ)
	if err != nil {
		// Ключ не існує - нічого видаляти
		return nil
	}

	subkeys, err := key.ReadSubKeyNames(-1)
	key.Close()
	if err != nil {
		return err
	}

	for _, subkey := range subkeys {
		subPath := SRP0Path + `\` + subkey
		subKey, err := registry.OpenKey(registry.LOCAL_MACHINE, subPath, registry.READ)
		if err != nil {
			continue
		}

		desc, _, _ := subKey.GetStringValue("Description")
		subKey.Close()

		// Видаляємо тільки наші правила
		if strings.HasPrefix(desc, "Orange Inventory:") {
			registry.DeleteKey(registry.LOCAL_MACHINE, subPath)
		}
	}

	return nil
}

// applyBlockPolicies застосовує політики блокування
func applyBlockPolicies(blocked []BlockedSoftware) error {
	// Вмикаємо SRP якщо потрібно
	if err := enableSRP(); err != nil {
		return fmt.Errorf("не вдалося увімкнути SRP: %w", err)
	}

	// Очищаємо старі правила
	if err := clearAllBlockRules(); err != nil {
		log.Printf("⚠ Помилка очищення старих правил: %v", err)
	}

	// Додаємо нові правила
	blockedCount := 0
	for _, item := range blocked {
		for _, exe := range item.Executables {
			if err := blockExecutable(exe, item.Reason); err != nil {
				log.Printf("⚠ Не вдалося заблокувати %s: %v", exe, err)
			} else {
				blockedCount++
			}
		}
	}

	log.Printf("🔒 Застосовано %d правил блокування", blockedCount)

	// Оновлюємо Group Policy
	refreshGroupPolicy()

	return nil
}

// refreshGroupPolicy оновлює групові політики
func refreshGroupPolicy() {
	cmd := exec.Command("gpupdate", "/force")
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out

	if err := cmd.Run(); err != nil {
		log.Printf("⚠ Помилка оновлення GP: %v", err)
	}
}

// killBlockedProcesses завершує запущені заблоковані процеси
// Це backup метод коли SRP не працює (Windows Home, Windows 11)
func killBlockedProcesses(blocked []BlockedSoftware) int {
	killedCount := 0

	for _, item := range blocked {
		for _, exe := range item.Executables {
			// tasklist не чутливий до регістру, але вивід може містити будь-який регістр
			// Використовуємо case-insensitive пошук
			checkCmd := exec.Command("tasklist", "/FI", fmt.Sprintf("IMAGENAME eq %s", exe), "/FO", "CSV", "/NH")
			output, err := checkCmd.Output()
			if err != nil {
				continue
			}

			// Якщо процес знайдено (вивід не порожній і не містить "INFO: No tasks")
			outputStr := strings.ToLower(string(output))
			exeLower := strings.ToLower(exe)
			if strings.Contains(outputStr, exeLower) && !strings.Contains(outputStr, "no tasks") {
				// Завершуємо процес (taskkill не чутливий до регістру)
				killCmd := exec.Command("taskkill", "/F", "/IM", exe)
				if err := killCmd.Run(); err != nil {
					log.Printf("⚠ Не вдалося завершити %s: %v", exe, err)
				} else {
					log.Printf("🔪 Завершено процес: %s (%s)", exe, item.Reason)
					killedCount++
				}
			}
		}
	}

	return killedCount
}

// isWindowsHome перевіряє чи це Windows Home (де SRP не працює)
func isWindowsHome() bool {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows NT\CurrentVersion`, registry.READ)
	if err != nil {
		return false
	}
	defer key.Close()

	edition, _, err := key.GetStringValue("EditionID")
	if err != nil {
		return false
	}

	edition = strings.ToLower(edition)
	// Home, HomeBasic, HomePremium, CoreSingleLanguage, Core
	return strings.Contains(edition, "home") || strings.Contains(edition, "core")
}

// syncBlockedSoftware синхронізує список заблокованого ПЗ з сервером
func syncBlockedSoftware(config *Config) error {
	log.Println("🔄 Перевірка заблокованого ПЗ...")

	// Отримуємо список з сервера
	response, err := fetchBlockedSoftware(config)
	if err != nil {
		return fmt.Errorf("помилка отримання списку: %w", err)
	}

	// Перевіряємо чи змінилась версія
	currentVersion := getCurrentPolicyVersion()
	if currentVersion == response.Message.Version && currentVersion != "" {
		log.Printf("✓ Політики актуальні (версія: %s)", currentVersion)

		// Навіть якщо політики актуальні - перевіряємо та завершуємо запущені заблоковані процеси
		if response.Message.Count > 0 {
			if killed := killBlockedProcesses(response.Message.Blocked); killed > 0 {
				log.Printf("🔪 Завершено %d заблокованих процесів", killed)
			}
		}
		return nil
	}

	log.Printf("📥 Отримано %d заблокованих програм", response.Message.Count)

	// Визначаємо метод блокування
	useProcessKill := isWindowsHome()
	if useProcessKill {
		log.Println("⚠ Windows Home виявлено - SRP не підтримується, використовуємо завершення процесів")
	}

	if response.Message.Count == 0 {
		// Немає заблокованих - очищаємо всі правила
		log.Println("🔓 Знімаємо всі блокування...")
		if err := clearAllBlockRules(); err != nil {
			log.Printf("⚠ Помилка очищення правил: %v", err)
		} else {
			log.Println("✓ Всі блокування знято")
		}
		// Оновлюємо Group Policy щоб зміни застосувались
		refreshGroupPolicy()
	} else {
		// Застосовуємо політики SRP (навіть на Home - для майбутньої сумісності)
		if err := applyBlockPolicies(response.Message.Blocked); err != nil {
			log.Printf("⚠ Помилка застосування SRP політик: %v", err)
		}

		// ЗАВЖДИ завершуємо запущені заблоковані процеси (працює на всіх версіях Windows)
		if killed := killBlockedProcesses(response.Message.Blocked); killed > 0 {
			log.Printf("🔪 Завершено %d заблокованих процесів", killed)
		}
	}

	// Зберігаємо версію
	if err := setPolicyVersion(response.Message.Version); err != nil {
		log.Printf("⚠ Не вдалося зберегти версію політик: %v", err)
	}

	return nil
}
