//go:build windows
// +build windows

package main

import (
	"bufio"
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

// BlockedDomain представляє заблокований домен
type BlockedDomain struct {
	Domain            string `json:"domain"`
	Method            string `json:"method"` // hosts, firewall, both
	RedirectIP        string `json:"redirect_ip"`
	IncludeSubdomains bool   `json:"include_subdomains"`
	Reason            string `json:"reason"`
}

// BlockedDomainsResponse відповідь сервера зі списком заблокованих доменів
type BlockedDomainsResponse struct {
	Message struct {
		Domains []BlockedDomain `json:"domains"`
		Version string          `json:"version"`
		Count   int             `json:"count"`
	} `json:"message"`
}

// Константи для блокування доменів
const (
	HostsFilePath        = `C:\Windows\System32\drivers\etc\hosts`
	DomainVersionKey     = "OrangeInventoryDomainVersion"
	HostsMarkerStart     = "# === ORANGE INVENTORY BLOCKED DOMAINS START ==="
	HostsMarkerEnd       = "# === ORANGE INVENTORY BLOCKED DOMAINS END ==="
	FirewallRulePrefix   = "OrangeInventory_Block_"
)

// fetchBlockedDomains отримує список заблокованих доменів з сервера
func fetchBlockedDomains(config *Config, agentID string) (*BlockedDomainsResponse, error) {
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.get_blocked_domains"

	payload := map[string]string{"agent_id": agentID}
	body, _ := json.Marshal(payload)

	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(body))
	if err != nil {
		return nil, fmt.Errorf("помилка створення запиту: %w", err)
	}

	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)
	req.Header.Set("Content-Type", "application/json")
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

	var result BlockedDomainsResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("помилка парсингу відповіді: %w", err)
	}

	return &result, nil
}

// getCurrentDomainVersion отримує поточну версію блокувань доменів з реєстру
func getCurrentDomainVersion() string {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, SRPBasePath, registry.READ)
	if err != nil {
		return ""
	}
	defer key.Close()

	version, _, err := key.GetStringValue(DomainVersionKey)
	if err != nil {
		return ""
	}
	return version
}

// setDomainVersion зберігає версію блокувань доменів в реєстрі
func setDomainVersion(version string) error {
	key, _, err := registry.CreateKey(registry.LOCAL_MACHINE, SRPBasePath, registry.WRITE)
	if err != nil {
		return err
	}
	defer key.Close()

	return key.SetStringValue(DomainVersionKey, version)
}

// updateHostsFile оновлює файл hosts з заблокованими доменами
func updateHostsFile(domains []BlockedDomain) error {
	// Читаємо поточний вміст hosts
	content, err := os.ReadFile(HostsFilePath)
	if err != nil {
		return fmt.Errorf("не вдалося прочитати hosts: %w", err)
	}

	// Видаляємо старі записи Orange Inventory
	lines := strings.Split(string(content), "\n")
	var newLines []string
	inOrangeBlock := false

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == HostsMarkerStart {
			inOrangeBlock = true
			continue
		}
		if trimmed == HostsMarkerEnd {
			inOrangeBlock = false
			continue
		}
		if !inOrangeBlock {
			newLines = append(newLines, line)
		}
	}

	// Видаляємо пусті рядки в кінці
	for len(newLines) > 0 && strings.TrimSpace(newLines[len(newLines)-1]) == "" {
		newLines = newLines[:len(newLines)-1]
	}

	// Додаємо нові записи якщо є домени для блокування через hosts
	var hostsEntries []string
	for _, d := range domains {
		if d.Method == "hosts" || d.Method == "both" {
			redirectIP := d.RedirectIP
			if redirectIP == "" {
				redirectIP = "0.0.0.0"
			}

			// Основний домен
			hostsEntries = append(hostsEntries, fmt.Sprintf("%s\t%s\t# %s", redirectIP, d.Domain, d.Reason))

			// Субдомени
			if d.IncludeSubdomains {
				hostsEntries = append(hostsEntries, fmt.Sprintf("%s\twww.%s\t# %s", redirectIP, d.Domain, d.Reason))
			}
		}
	}

	if len(hostsEntries) > 0 {
		newLines = append(newLines, "")
		newLines = append(newLines, HostsMarkerStart)
		newLines = append(newLines, hostsEntries...)
		newLines = append(newLines, HostsMarkerEnd)
	}

	// Записуємо оновлений файл
	newContent := strings.Join(newLines, "\n")
	if err := os.WriteFile(HostsFilePath, []byte(newContent), 0644); err != nil {
		return fmt.Errorf("не вдалося записати hosts: %w", err)
	}

	// Очищаємо DNS кеш
	flushDNSCache()

	return nil
}

// flushDNSCache очищає кеш DNS
func flushDNSCache() {
	cmd := exec.Command("ipconfig", "/flushdns")
	cmd.Run() // Ігноруємо помилки
}

// addFirewallRule додає правило брандмауера для блокування домену
func addFirewallRule(domain BlockedDomain) error {
	ruleName := FirewallRulePrefix + strings.ReplaceAll(domain.Domain, ".", "_")

	// Спочатку видаляємо старе правило якщо є
	removeCmd := exec.Command("netsh", "advfirewall", "firewall", "delete", "rule", fmt.Sprintf("name=%s", ruleName))
	removeCmd.Run() // Ігноруємо помилки

	// Отримуємо IP адреси домену
	ips := resolveDomainIPs(domain.Domain)
	if domain.IncludeSubdomains {
		wwwIPs := resolveDomainIPs("www." + domain.Domain)
		ips = append(ips, wwwIPs...)
	}

	if len(ips) == 0 {
		log.Printf("⚠ Не вдалося отримати IP для %s", domain.Domain)
		return nil
	}

	// Створюємо правило для блокування вихідного трафіку
	remoteIPs := strings.Join(ips, ",")
	addCmd := exec.Command("netsh", "advfirewall", "firewall", "add", "rule",
		fmt.Sprintf("name=%s", ruleName),
		"dir=out",
		"action=block",
		fmt.Sprintf("remoteip=%s", remoteIPs),
		"enable=yes",
		fmt.Sprintf("description=Orange Inventory: %s", domain.Reason),
	)

	if output, err := addCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("не вдалося додати правило: %v - %s", err, string(output))
	}

	return nil
}

// resolveDomainIPs отримує IP адреси домену через nslookup
func resolveDomainIPs(domain string) []string {
	var ips []string

	cmd := exec.Command("nslookup", domain)
	output, err := cmd.Output()
	if err != nil {
		return ips
	}

	// Парсимо вивід nslookup
	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	afterAddresses := false
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		// Шукаємо секцію з адресами
		if strings.HasPrefix(line, "Addresses:") || strings.HasPrefix(line, "Address:") {
			afterAddresses = true
			// Якщо адреса на тому ж рядку
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				ip := strings.TrimSpace(parts[1])
				if isValidIP(ip) && !isLocalIP(ip) {
					ips = append(ips, ip)
				}
			}
			continue
		}

		// Додаткові IP адреси
		if afterAddresses && line != "" {
			if isValidIP(line) && !isLocalIP(line) {
				ips = append(ips, line)
			}
		}
	}

	return ips
}

// isValidIP перевіряє чи рядок є валідною IP адресою
func isValidIP(s string) bool {
	parts := strings.Split(s, ".")
	if len(parts) != 4 {
		return false
	}
	for _, p := range parts {
		if len(p) == 0 || len(p) > 3 {
			return false
		}
		for _, c := range p {
			if c < '0' || c > '9' {
				return false
			}
		}
	}
	return true
}

// isLocalIP перевіряє чи IP локальний (DNS сервер)
func isLocalIP(ip string) bool {
	return strings.HasPrefix(ip, "127.") || strings.HasPrefix(ip, "192.168.") || strings.HasPrefix(ip, "10.")
}

// removeFirewallRule видаляє правило брандмауера
func removeFirewallRule(domain string) error {
	ruleName := FirewallRulePrefix + strings.ReplaceAll(domain, ".", "_")
	cmd := exec.Command("netsh", "advfirewall", "firewall", "delete", "rule", fmt.Sprintf("name=%s", ruleName))
	cmd.Run() // Ігноруємо помилки
	return nil
}

// clearAllFirewallRules видаляє всі правила Orange Inventory
func clearAllFirewallRules() {
	// Отримуємо список всіх правил
	cmd := exec.Command("netsh", "advfirewall", "firewall", "show", "rule", "name=all")
	output, err := cmd.Output()
	if err != nil {
		return
	}

	// Шукаємо наші правила
	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, "Rule Name:") && strings.Contains(line, FirewallRulePrefix) {
			// Витягуємо назву правила
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				ruleName := strings.TrimSpace(parts[1])
				delCmd := exec.Command("netsh", "advfirewall", "firewall", "delete", "rule", fmt.Sprintf("name=%s", ruleName))
				delCmd.Run()
			}
		}
	}
}

// applyDomainBlocking застосовує блокування доменів
func applyDomainBlocking(domains []BlockedDomain) error {
	// Оновлюємо hosts файл
	if err := updateHostsFile(domains); err != nil {
		log.Printf("⚠ Помилка оновлення hosts: %v", err)
	}

	// Очищаємо старі правила firewall
	clearAllFirewallRules()

	// Додаємо нові правила firewall
	firewallCount := 0
	for _, d := range domains {
		if d.Method == "firewall" || d.Method == "both" {
			if err := addFirewallRule(d); err != nil {
				log.Printf("⚠ Помилка додавання правила firewall для %s: %v", d.Domain, err)
			} else {
				firewallCount++
			}
		}
	}

	hostsCount := 0
	for _, d := range domains {
		if d.Method == "hosts" || d.Method == "both" {
			hostsCount++
		}
	}

	log.Printf("🌐 Заблоковано доменів: %d через hosts, %d через firewall", hostsCount, firewallCount)

	return nil
}

// syncBlockedDomains синхронізує список заблокованих доменів з сервером
func syncBlockedDomains(config *Config, agentID string) error {
	log.Println("🔄 Перевірка заблокованих доменів...")

	// Отримуємо список з сервера
	response, err := fetchBlockedDomains(config, agentID)
	if err != nil {
		return fmt.Errorf("помилка отримання списку: %w", err)
	}

	// Перевіряємо чи змінилась версія
	currentVersion := getCurrentDomainVersion()
	if currentVersion == response.Message.Version && currentVersion != "" {
		log.Printf("✓ Блокування доменів актуальні (версія: %s)", currentVersion)
		return nil
	}

	log.Printf("📥 Отримано %d заблокованих доменів", response.Message.Count)

	if response.Message.Count == 0 {
		// Немає заблокованих - очищаємо
		log.Println("🔓 Знімаємо всі блокування доменів...")
		updateHostsFile([]BlockedDomain{}) // Очищаємо hosts
		clearAllFirewallRules()            // Очищаємо firewall
		log.Println("✓ Всі блокування доменів знято")
	} else {
		// Застосовуємо блокування
		if err := applyDomainBlocking(response.Message.Domains); err != nil {
			return fmt.Errorf("помилка застосування блокувань: %w", err)
		}
	}

	// Зберігаємо версію
	if err := setDomainVersion(response.Message.Version); err != nil {
		log.Printf("⚠ Не вдалося зберегти версію блокувань: %v", err)
	}

	return nil
}

// getHostsPath повертає шлях до hosts файлу (для тестування)
func getHostsPath() string {
	systemRoot := os.Getenv("SystemRoot")
	if systemRoot == "" {
		systemRoot = `C:\Windows`
	}
	return filepath.Join(systemRoot, "System32", "drivers", "etc", "hosts")
}
