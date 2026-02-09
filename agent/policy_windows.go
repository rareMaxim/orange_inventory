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
	"os"
	"os/exec"
	"path/filepath"
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

// Константи для DisallowRun Policy
const (
	ExplorerPolicyPath = `SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer`
	DisallowRunPath    = ExplorerPolicyPath + `\DisallowRun`
)

// Префікс для правил брандмауера блокування програм
const AppFirewallRulePrefix = "OrangeInv_AppBlock_"

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

// enableDisallowRun вмикає політику DisallowRun в реєстрі
func enableDisallowRun() error {
	// Створюємо ключ Explorer Policies
	key, _, err := registry.CreateKey(registry.LOCAL_MACHINE, ExplorerPolicyPath, registry.WRITE)
	if err != nil {
		return fmt.Errorf("не вдалося створити ключ Explorer Policies: %w", err)
	}
	defer key.Close()

	// DisallowRun = 1 (увімкнути)
	if err := key.SetDWordValue("DisallowRun", 1); err != nil {
		return fmt.Errorf("не вдалося встановити DisallowRun: %w", err)
	}

	// Створюємо підключ DisallowRun для списку програм
	_, _, err = registry.CreateKey(registry.LOCAL_MACHINE, DisallowRunPath, registry.WRITE)
	if err != nil {
		return fmt.Errorf("не вдалося створити ключ DisallowRun: %w", err)
	}

	return nil
}

// addDisallowRunEntries додає виконувані файли до списку DisallowRun
func addDisallowRunEntries(blocked []BlockedSoftware) (int, error) {
	key, _, err := registry.CreateKey(registry.LOCAL_MACHINE, DisallowRunPath, registry.WRITE)
	if err != nil {
		return 0, fmt.Errorf("не вдалося відкрити ключ DisallowRun: %w", err)
	}
	defer key.Close()

	count := 0
	for _, item := range blocked {
		for _, exe := range item.Executables {
			count++
			// Використовуємо порядковий номер як ім'я значення
			valueName := fmt.Sprintf("%d", count)
			if err := key.SetStringValue(valueName, exe); err != nil {
				log.Printf("⚠ Не вдалося додати %s до DisallowRun: %v", exe, err)
				count--
			}
		}
	}

	return count, nil
}

// clearDisallowRunEntries очищає всі записи DisallowRun
func clearDisallowRunEntries() error {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, DisallowRunPath, registry.READ)
	if err != nil {
		// Ключ не існує — нічого очищати
		return nil
	}

	// Зчитуємо всі значення
	valueNames, err := key.ReadValueNames(-1)
	key.Close()
	if err != nil {
		return fmt.Errorf("не вдалося прочитати значення DisallowRun: %w", err)
	}

	// Відкриваємо для запису та видаляємо всі значення
	key, err = registry.OpenKey(registry.LOCAL_MACHINE, DisallowRunPath, registry.WRITE)
	if err != nil {
		return fmt.Errorf("не вдалося відкрити DisallowRun для запису: %w", err)
	}
	defer key.Close()

	for _, name := range valueNames {
		if err := key.DeleteValue(name); err != nil {
			log.Printf("⚠ Не вдалося видалити значення %s з DisallowRun: %v", name, err)
		}
	}

	return nil
}

// disableDisallowRun вимикає політику DisallowRun
func disableDisallowRun() error {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, ExplorerPolicyPath, registry.WRITE)
	if err != nil {
		return nil // Ключ не існує — вже вимкнено
	}
	defer key.Close()

	// DisallowRun = 0 (вимкнути)
	return key.SetDWordValue("DisallowRun", 0)
}

// findExecutablePaths шукає виконуваний файл у типових каталогах Windows
func findExecutablePaths(exeName string) []string {
	var found []string
	seen := make(map[string]bool)

	// Системні каталоги
	searchRoots := []string{
		os.Getenv("ProgramFiles"),
		os.Getenv("ProgramFiles(x86)"),
		os.Getenv("ProgramW6432"),
	}

	// Додаємо AppData для кожного користувача (C:\Users\*)
	usersDir := filepath.Join(os.Getenv("SystemDrive")+"\\", "Users")
	if entries, err := os.ReadDir(usersDir); err == nil {
		for _, entry := range entries {
			if !entry.IsDir() {
				continue
			}
			name := entry.Name()
			if name == "Public" || name == "Default" || name == "Default User" || name == "All Users" {
				continue
			}
			userDir := filepath.Join(usersDir, name)
			searchRoots = append(searchRoots,
				filepath.Join(userDir, "AppData", "Roaming"),
				filepath.Join(userDir, "AppData", "Local"),
				filepath.Join(userDir, "Desktop"),
			)
		}
	}

	exeLower := strings.ToLower(exeName)

	for _, root := range searchRoots {
		if root == "" {
			continue
		}
		// Обмежуємо глибину пошуку (до 4 рівнів) щоб не витрачати час
		filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return filepath.SkipDir
			}
			// Обмежуємо глибину
			rel, _ := filepath.Rel(root, path)
			if strings.Count(rel, string(filepath.Separator)) > 4 {
				return filepath.SkipDir
			}
			if !info.IsDir() && strings.ToLower(info.Name()) == exeLower {
				absPath := strings.ToLower(path)
				if !seen[absPath] {
					seen[absPath] = true
					found = append(found, path)
				}
			}
			return nil
		})
	}

	return found
}

// addFirewallBlockRule створює правило брандмауера для блокування програми
func addFirewallBlockRule(exePath string, exeName string) error {
	ruleName := AppFirewallRulePrefix + exeName

	cmd := exec.Command("netsh", "advfirewall", "firewall", "add", "rule",
		"name="+ruleName,
		"dir=out",
		"action=block",
		"program="+exePath,
		"enable=yes",
	)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("netsh error: %v — %s", err, out.String())
	}
	return nil
}

// clearFirewallBlockRules видаляє всі правила брандмауера OrangeInv_AppBlock_*
func clearFirewallBlockRules() error {
	// Отримуємо список всіх правил
	cmd := exec.Command("netsh", "advfirewall", "firewall", "show", "rule", "name=all", "dir=out")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("не вдалося отримати правила брандмауера: %w", err)
	}

	// Шукаємо наші правила за префіксом
	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		if strings.Contains(line, "Rule Name:") && strings.Contains(line, AppFirewallRulePrefix) {
			// Витягуємо ім'я правила
			parts := strings.SplitN(line, ":", 2)
			if len(parts) != 2 {
				continue
			}
			ruleName := strings.TrimSpace(parts[1])

			delCmd := exec.Command("netsh", "advfirewall", "firewall", "delete", "rule",
				"name="+ruleName,
				"dir=out",
			)
			if err := delCmd.Run(); err != nil {
				log.Printf("⚠ Не вдалося видалити правило %s: %v", ruleName, err)
			}
		}
	}

	return nil
}

// applyFirewallBlocks застосовує правила брандмауера для заблокованих програм
func applyFirewallBlocks(blocked []BlockedSoftware) int {
	rulesCount := 0

	for _, item := range blocked {
		for _, exe := range item.Executables {
			paths := findExecutablePaths(exe)
			if len(paths) == 0 {
				// Exe не знайдено на диску — пропускаємо
				log.Printf("⚠ Брандмауер: %s не знайдено на диску, правило не створено", exe)
				continue
			}
			for _, exePath := range paths {
				if err := addFirewallBlockRule(exePath, exe); err != nil {
					log.Printf("⚠ Не вдалося створити правило брандмауера для %s: %v", exePath, err)
				} else {
					log.Printf("🔥 Заблоковано мережу для: %s", exePath)
					rulesCount++
				}
			}
		}
	}

	return rulesCount
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

	log.Printf("🔒 Застосовано %d правил блокування SRP", blockedCount)

	// Застосовуємо DisallowRun політику (працює на всіх версіях Windows)
	if err := enableDisallowRun(); err != nil {
		log.Printf("⚠ Не вдалося увімкнути DisallowRun: %v", err)
	} else {
		if err := clearDisallowRunEntries(); err != nil {
			log.Printf("⚠ Помилка очищення DisallowRun: %v", err)
		}
		drCount, err := addDisallowRunEntries(blocked)
		if err != nil {
			log.Printf("⚠ Помилка додавання записів DisallowRun: %v", err)
		} else {
			log.Printf("🔒 Застосовано %d правил DisallowRun", drCount)
		}
	}

	// Застосовуємо правила брандмауера (блокування мережевої активності)
	if err := clearFirewallBlockRules(); err != nil {
		log.Printf("⚠ Помилка очищення правил брандмауера: %v", err)
	}
	if fwCount := applyFirewallBlocks(blocked); fwCount > 0 {
		log.Printf("🔥 Застосовано %d правил брандмауера", fwCount)
	}

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
			log.Printf("⚠ Помилка очищення правил SRP: %v", err)
		}
		// Очищаємо DisallowRun
		if err := clearDisallowRunEntries(); err != nil {
			log.Printf("⚠ Помилка очищення DisallowRun: %v", err)
		}
		if err := disableDisallowRun(); err != nil {
			log.Printf("⚠ Помилка вимкнення DisallowRun: %v", err)
		}
		// Очищаємо правила брандмауера
		if err := clearFirewallBlockRules(); err != nil {
			log.Printf("⚠ Помилка очищення правил брандмауера: %v", err)
		}
		log.Println("✓ Всі блокування знято")
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
