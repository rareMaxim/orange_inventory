package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gosnmp/gosnmp"
)

// GetDiscoverySettings отримує налаштування сканування з сервера
func GetDiscoverySettings(config *Config, agentID string) (*DiscoverySettings, error) {
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.snmp.get_discovery_settings"

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, err
	}

	q := req.URL.Query()
	q.Add("agent_id", agentID)
	req.URL.RawQuery = q.Encode()

	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)
	req.Header.Set("Accept", "application/json")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("помилка сервера: %d", resp.StatusCode)
	}

	var result struct {
		Message *DiscoverySettings `json:"message"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	// Відповідь може бути порожнім об'єктом {} якщо налаштувань немає
	if result.Message == nil || len(result.Message.Subnets) == 0 {
		return nil, nil // Немає налаштувань для сканування
	}

	return result.Message, nil
}

// ReportDiscovery відправляє звіт про знайдені пристрої
func ReportDiscovery(config *Config, agentID string, reports []DiscoveryReport) error {
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.snmp.report_discovery"

	data, err := json.Marshal(reports)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", apiURL, nil)
	if err != nil {
		return err
	}

	q := req.URL.Query()
	q.Add("agent_id", agentID)
	q.Add("report_data", string(data))
	req.URL.RawQuery = q.Encode()

	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("bad status: %d", resp.StatusCode)
	}
	return nil
}

// RunNetworkDiscovery запускає сканування
func RunNetworkDiscovery(config *Config, agentID string) {
	log.Println("\n=== AUTO-DISCOVERY SCAN ===")
	settings, err := GetDiscoverySettings(config, agentID)
	if err != nil {
		log.Printf("⚠ Не вдалося отримати налаштування Discovery: %v", err)
		return
	}
	if settings == nil {
		log.Println("ℹ Auto-Discovery не налаштовано для цього агента")
		return
	}

	log.Printf("🔍 Початок Auto-Discovery. Підмережі: %d, Ком'юніті: %d", len(settings.Subnets), len(settings.Communities))

	var allIPs []string
	for _, subnet := range settings.Subnets {
		ips, err := generateIPsFromCIDR(subnet)
		if err != nil {
			log.Printf("⚠ Некоректна підмережа %s: %v", subnet, err)
			continue
		}
		allIPs = append(allIPs, ips...)
	}

	if len(allIPs) == 0 {
		log.Println("ℹ Немає IP для сканування")
		return
	}

	log.Printf("📡 Буде перевірено %d IP-адрес...", len(allIPs))

	var wg sync.WaitGroup
	reportsChan := make(chan DiscoveryReport, len(allIPs))
	sem := make(chan struct{}, 100) // Обмежуємо кількість паралельних сканувань (goroutines)

	for _, ip := range allIPs {
		wg.Add(1)
		go func(targetIP string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			// Пробуємо всі ком'юніті для цього IP
			for _, comm := range settings.Communities {
				report := probeSNMP(targetIP, comm)
				if report != nil {
					reportsChan <- *report
					break // Знайшли з одним ком'юніті, інші не пробуємо
				}
			}
		}(ip)
	}

	wg.Wait()
	close(reportsChan)

	var reports []DiscoveryReport
	for r := range reportsChan {
		reports = append(reports, r)
		log.Printf("✓ Знайдено пристрій: %s (%s) з ком'юніті '%s'", r.IP, r.SysName, r.Community)
	}

	if len(reports) > 0 {
		log.Printf("📤 Відправка звіту про %d знайдених пристроїв...", len(reports))
		if err := ReportDiscovery(config, agentID, reports); err != nil {
			log.Printf("⚠ Помилка відправки звіту Auto-Discovery: %v", err)
		} else {
			log.Println("✓ Звіт Auto-Discovery успішно відправлено!")
		}
	} else {
		log.Println("ℹ Нових пристроїв не знайдено.")
	}
}

// probeSNMP перевіряє IP по SNMP і повертає базову інформацію, якщо пристрій відповідає
func probeSNMP(ip string, community string) *DiscoveryReport {
	gs := &gosnmp.GoSNMP{
		Target:    ip,
		Port:      161,
		Community: community,
		Version:   gosnmp.Version2c,
		Timeout:   time.Duration(1) * time.Second, // Короткий таймаут для швидкого сканування
		Retries:   1,
	}

	err := gs.Connect()
	if err != nil {
		return nil
	}
	defer gs.Conn.Close()

	// 1.3.6.1.2.1.1.1.0 - sysDescr
	// 1.3.6.1.2.1.1.5.0 - sysName
	oids := []string{"1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1.5.0"}
	result, err := gs.Get(oids)
	if err != nil || len(result.Variables) == 0 {
		return nil
	}

	var sysDescr, sysName string
	for _, v := range result.Variables {
		switch v.Name {
		case ".1.3.6.1.2.1.1.1.0":
			if v.Type == gosnmp.OctetString {
				sysDescr = string(v.Value.([]byte))
			}
		case ".1.3.6.1.2.1.1.5.0":
			if v.Type == gosnmp.OctetString {
				sysName = string(v.Value.([]byte))
			}
		}
	}

	// Quick check for MAC address from interface table index 1 or 2 as fallback identifier
	var firstMac string
	macs, err := gs.WalkAll(".1.3.6.1.2.1.2.2.1.6")
	if err == nil && len(macs) > 0 {
		for _, m := range macs {
			if m.Type == gosnmp.OctetString {
				b := m.Value.([]byte)
				if len(b) > 0 {
					var hexParts []string
					for _, bItem := range b {
						hexParts = append(hexParts, fmt.Sprintf("%02X", bItem))
					}
					hwaddr := strings.Join(hexParts, ":")
					if hwaddr != "00:00:00:00:00:00" {
						firstMac = hwaddr
						break
					}
				}
			}
		}
	}

	return &DiscoveryReport{
		IP:        ip,
		Community: community,
		SysName:   sysName,
		SysDescr:  sysDescr,
		MAC:       firstMac,
	}
}

// generateIPsFromCIDR генерує список IP-адрес для заданої мережі (IP або CIDR)
func generateIPsFromCIDR(cidr string) ([]string, error) {
	if !strings.Contains(cidr, "/") {
		// Якщо передано лише IP без маски, повертаємо його
		parsedIP := net.ParseIP(cidr)
		if parsedIP == nil {
			return nil, fmt.Errorf("invalid IP or CIDR: %s", cidr)
		}
		return []string{cidr}, nil
	}

	ip, ipnet, err := net.ParseCIDR(cidr)
	if err != nil {
		return nil, err
	}

	var ips []string
	// Отримуємо розмір маски
	ones, _ := ipnet.Mask.Size()

	for ip := ip.Mask(ipnet.Mask); ipnet.Contains(ip); inc(ip) {
		// Для IPv4 розраховуємо мережу та broadcast
		if len(ip) == net.IPv4len || ip.To4() != nil {
			// Якщо це не /32 і не /31, пропускаємо адресу мережі та broadcast
			if ones < 31 {
				if ip.Equal(ipnet.IP) {
					continue
				}
				broadcast := make(net.IP, len(ip))
				copy(broadcast, ip)
				for i := range broadcast {
					broadcast[i] |= ^ipnet.Mask[i]
				}
				if ip.Equal(broadcast) {
					continue
				}
			}
		}
		ips = append(ips, ip.String())
	}
	return ips, nil
}

func inc(ip net.IP) {
	for j := len(ip) - 1; j >= 0; j-- {
		ip[j]++
		if ip[j] > 0 {
			break
		}
	}
}
