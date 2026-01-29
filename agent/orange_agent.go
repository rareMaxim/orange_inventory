package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/yusufpapurcu/wmi"
	"golang.org/x/sys/windows/registry"
)

// --- КОНСТАНТИ ---
const (
	AppVersion   = "1.2"
	TaskName     = "OrangeInventoryAgent"
	TaskInterval = 15 // хвилин
)

// --- КОНФІГУРАЦІЯ ---

// Config містить налаштування для підключення до сервера
type Config struct {
	ServerURL string `json:"server_url"` // URL Frappe сервера (наприклад: https://your-site.com)
	APIKey    string `json:"api_key"`    // API ключ користувача
	APISecret string `json:"api_secret"` // API секрет користувача
}

// --- СТРУКТУРИ ДАНИХ ---

type RAMDetails struct {
	Capacity uint64 `json:"capacity_bytes"`
	Speed    uint32 `json:"speed_mhz"`
	Vendor   string `json:"vendor"`
}

type BIOSInfo struct {
	SerialNumber string `json:"serial_number"`
	Manufacturer string `json:"manufacturer"`
	Version      string `json:"version"`
	ReleaseDate  string `json:"release_date"`
}

type SystemInfo struct {
	Manufacturer string `json:"manufacturer"`
	Model        string `json:"model"`
	Domain       string `json:"domain"`
	SystemType   string `json:"system_type"` // Desktop, Laptop, etc.
}

type NetworkAdapterInfo struct {
	Name       string `json:"name"`
	MACAddress string `json:"mac_address"`
	Enabled    bool   `json:"enabled"`
}

type PhysicalDiskInfo struct {
	Model         string `json:"model"`
	SerialNumber  string `json:"serial_number"`
	Size          uint64 `json:"size_bytes"`
	MediaType     string `json:"media_type"`
	InterfaceType string `json:"interface_type"`
}

type MonitorInfo struct {
	Name   string `json:"name"`
	Width  uint32 `json:"width"`
	Height uint32 `json:"height"`
}

type SoftwareInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
	Vendor  string `json:"vendor"`
}

type PrinterInfo struct {
	Name      string `json:"name"`
	Port      string `json:"port"`
	IsDefault bool   `json:"is_default"`
	IsNetwork bool   `json:"is_network"`
}

type StaticData struct {
	Hostname        string              `json:"hostname"`
	Platform        string              `json:"os_platform"`
	OSVersion       string              `json:"os_version"`
	CPUModel        string              `json:"cpu_model"`
	CPUCores        int                 `json:"cpu_cores"`
	TotalRAM        uint64              `json:"total_ram_bytes"`
	RAMSlots        []RAMDetails        `json:"ram_slots"`
	BoardSerial     string              `json:"board_serial"`
	GPU             []string            `json:"gpu_models"`
	BIOS            BIOSInfo            `json:"bios"`
	System          SystemInfo          `json:"system"`
	NetworkAdapters []NetworkAdapterInfo `json:"network_adapters"`
	PhysicalDisks   []PhysicalDiskInfo  `json:"physical_disks"`
	Monitors        []MonitorInfo       `json:"monitors"`
	Software        []SoftwareInfo      `json:"installed_software"`
	Printers        []PrinterInfo       `json:"printers"`
}

type DiskStatus struct {
	Drive       string  `json:"drive"`
	TotalSpace  uint64  `json:"total_bytes"`
	FreeSpace   uint64  `json:"free_bytes"`
	UsedPercent float64 `json:"used_percent"`
}

type BatteryInfo struct {
	ChargePercent uint16 `json:"charge_percent"`
	Status        string `json:"status"` // Charging, Discharging, Full, No Battery
}

type AntivirusInfo struct {
	Name   string `json:"name"`
	Active bool   `json:"active"`
}

type UpdateInfo struct {
	HotFixID    string `json:"hotfix_id"`
	InstalledOn string `json:"installed_on"`
}

type DynamicData struct {
	Timestamp    int64          `json:"timestamp"`
	Uptime       uint64         `json:"uptime_seconds"`
	CurrentUser  string         `json:"current_user"`
	IPAddresses  []string       `json:"ip_addresses"`
	RAMUsage     float64        `json:"ram_usage_percent"`
	CPUUsage     float64        `json:"cpu_usage_percent"`
	Disks        []DiskStatus   `json:"disks"`
	Battery      *BatteryInfo   `json:"battery,omitempty"`
	Antivirus    []AntivirusInfo `json:"antivirus"`
	RecentUpdates []UpdateInfo  `json:"recent_updates"`
}

// --- WMI ДОПОМІЖНІ СТРУКТУРИ ---

type Win32_BaseBoard struct{ SerialNumber string }
type Win32_PhysicalMemory struct {
	Capacity     uint64
	Speed        uint32
	Manufacturer string
}
type Win32_VideoController struct {
	Name                        string
	CurrentHorizontalResolution uint32
	CurrentVerticalResolution   uint32
}

type Win32_BIOS struct {
	SerialNumber      string
	Manufacturer      string
	SMBIOSBIOSVersion string
	ReleaseDate       string
}

type Win32_ComputerSystem struct {
	Manufacturer string
	Model        string
	Domain       string
	PCSystemType uint16
	UserName     string
}

type Win32_NetworkAdapter struct {
	Name       string
	MACAddress string
	NetEnabled bool
}

type Win32_DiskDrive struct {
	Model        string
	SerialNumber string
	Size         uint64
	MediaType    string
	InterfaceType string
}


type Win32_Product struct {
	Name    string
	Version string
	Vendor  string
}

type Win32_Printer struct {
	Name      string
	PortName  string
	Default   bool
	Network   bool
}

type Win32_Battery struct {
	EstimatedChargeRemaining uint16
	BatteryStatus            uint16
}

type Win32_QuickFixEngineering struct {
	HotFixID    string
	InstalledOn string
}

type AntiVirusProduct struct {
	DisplayName string
	ProductState uint32
}

// --- ФУНКЦІЇ ЗБОРУ ---

// getInstalledSoftware отримує список ПЗ з реєстру Windows (швидкий метод)
func getInstalledSoftware() []SoftwareInfo {
	softwareList := []SoftwareInfo{}
	seen := make(map[string]bool)

	// Шляхи в реєстрі для встановленого ПЗ
	regPaths := []struct {
		root registry.Key
		path string
	}{
		{registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`},
		{registry.LOCAL_MACHINE, `SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall`},
		{registry.CURRENT_USER, `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`},
	}

	for _, rp := range regPaths {
		key, err := registry.OpenKey(rp.root, rp.path, registry.READ)
		if err != nil {
			continue
		}

		subkeys, err := key.ReadSubKeyNames(-1)
		key.Close()
		if err != nil {
			continue
		}

		for _, subkey := range subkeys {
			subPath := rp.path + `\` + subkey
			sk, err := registry.OpenKey(rp.root, subPath, registry.READ)
			if err != nil {
				continue
			}

			name, _, _ := sk.GetStringValue("DisplayName")
			version, _, _ := sk.GetStringValue("DisplayVersion")
			vendor, _, _ := sk.GetStringValue("Publisher")
			systemComponent, _, _ := sk.GetIntegerValue("SystemComponent")
			sk.Close()

			// Пропускаємо системні компоненти та порожні імена
			if name == "" || systemComponent == 1 {
				continue
			}

			// Уникаємо дублікатів
			key := name + "|" + version
			if seen[key] {
				continue
			}
			seen[key] = true

			softwareList = append(softwareList, SoftwareInfo{
				Name:    name,
				Version: version,
				Vendor:  vendor,
			})
		}
	}

	return softwareList
}

func getSystemType(code uint16) string {
	types := map[uint16]string{
		1: "Desktop",
		2: "Laptop",
		3: "Workstation",
		4: "Enterprise Server",
		5: "SOHO Server",
		6: "Appliance PC",
		7: "Performance Server",
		8: "Maximum",
	}
	if t, ok := types[code]; ok {
		return t
	}
	return "Unknown"
}

func getStaticInfo() StaticData {
	hInfo, _ := host.Info()
	cpuInfo, _ := cpu.Info()
	vmStat, _ := mem.VirtualMemory()

	// Board Serial
	var board []Win32_BaseBoard
	wmi.Query("SELECT SerialNumber FROM Win32_BaseBoard", &board)
	boardS := "Unknown"
	if len(board) > 0 {
		boardS = board[0].SerialNumber
	}

	// RAM Slots
	var memWmi []Win32_PhysicalMemory
	wmi.Query("SELECT Capacity, Speed, Manufacturer FROM Win32_PhysicalMemory", &memWmi)
	ramSlots := []RAMDetails{}
	for _, m := range memWmi {
		ramSlots = append(ramSlots, RAMDetails{Capacity: m.Capacity, Speed: m.Speed, Vendor: m.Manufacturer})
	}

	// GPU
	var gpus []Win32_VideoController
	wmi.Query("SELECT Name FROM Win32_VideoController", &gpus)
	gpuNames := []string{}
	for _, g := range gpus {
		gpuNames = append(gpuNames, g.Name)
	}

	// BIOS
	var bios []Win32_BIOS
	wmi.Query("SELECT SerialNumber, Manufacturer, SMBIOSBIOSVersion, ReleaseDate FROM Win32_BIOS", &bios)
	biosInfo := BIOSInfo{}
	if len(bios) > 0 {
		biosInfo = BIOSInfo{
			SerialNumber: bios[0].SerialNumber,
			Manufacturer: bios[0].Manufacturer,
			Version:      bios[0].SMBIOSBIOSVersion,
			ReleaseDate:  bios[0].ReleaseDate,
		}
	}

	// System Info
	var sys []Win32_ComputerSystem
	wmi.Query("SELECT Manufacturer, Model, Domain, PCSystemType FROM Win32_ComputerSystem", &sys)
	sysInfo := SystemInfo{}
	if len(sys) > 0 {
		sysInfo = SystemInfo{
			Manufacturer: sys[0].Manufacturer,
			Model:        sys[0].Model,
			Domain:       sys[0].Domain,
			SystemType:   getSystemType(sys[0].PCSystemType),
		}
	}

	// Network Adapters
	var adapters []Win32_NetworkAdapter
	wmi.Query("SELECT Name, MACAddress, NetEnabled FROM Win32_NetworkAdapter WHERE MACAddress IS NOT NULL", &adapters)
	netAdapters := []NetworkAdapterInfo{}
	for _, a := range adapters {
		netAdapters = append(netAdapters, NetworkAdapterInfo{
			Name:       a.Name,
			MACAddress: a.MACAddress,
			Enabled:    a.NetEnabled,
		})
	}

	// Physical Disks
	var disks []Win32_DiskDrive
	wmi.Query("SELECT Model, SerialNumber, Size, MediaType, InterfaceType FROM Win32_DiskDrive", &disks)
	physDisks := []PhysicalDiskInfo{}
	for _, d := range disks {
		physDisks = append(physDisks, PhysicalDiskInfo{
			Model:         d.Model,
			SerialNumber:  d.SerialNumber,
			Size:          d.Size,
			MediaType:     d.MediaType,
			InterfaceType: d.InterfaceType,
		})
	}

	// Monitors (використовуємо VideoController для отримання роздільності)
	var videoControllers []Win32_VideoController
	wmi.Query("SELECT Name, CurrentHorizontalResolution, CurrentVerticalResolution FROM Win32_VideoController", &videoControllers)
	monitorList := []MonitorInfo{}
	for _, vc := range videoControllers {
		if vc.CurrentHorizontalResolution > 0 {
			monitorList = append(monitorList, MonitorInfo{
				Name:   vc.Name,
				Width:  vc.CurrentHorizontalResolution,
				Height: vc.CurrentVerticalResolution,
			})
		}
	}

	// Installed Software (швидкий метод через реєстр)
	softwareList := getInstalledSoftware()

	// Printers
	var printers []Win32_Printer
	wmi.Query("SELECT Name, PortName, Default, Network FROM Win32_Printer", &printers)
	printerList := []PrinterInfo{}
	for _, p := range printers {
		printerList = append(printerList, PrinterInfo{
			Name:      p.Name,
			Port:      p.PortName,
			IsDefault: p.Default,
			IsNetwork: p.Network,
		})
	}

	return StaticData{
		Hostname:        hInfo.Hostname,
		Platform:        hInfo.OS,
		OSVersion:       hInfo.PlatformVersion,
		CPUModel:        cpuInfo[0].ModelName,
		CPUCores:        len(cpuInfo),
		TotalRAM:        vmStat.Total,
		RAMSlots:        ramSlots,
		BoardSerial:     boardS,
		GPU:             gpuNames,
		BIOS:            biosInfo,
		System:          sysInfo,
		NetworkAdapters: netAdapters,
		PhysicalDisks:   physDisks,
		Monitors:        monitorList,
		Software:        softwareList,
		Printers:        printerList,
	}
}

func getBatteryStatus(code uint16) string {
	statuses := map[uint16]string{
		1: "Discharging",
		2: "AC Power",
		3: "Fully Charged",
		4: "Low",
		5: "Critical",
		6: "Charging",
		7: "Charging High",
		8: "Charging Low",
		9: "Charging Critical",
	}
	if s, ok := statuses[code]; ok {
		return s
	}
	return "Unknown"
}

func getDynamicInfo() DynamicData {
	hInfo, _ := host.Info()
	vmStat, _ := mem.VirtualMemory()

	// CPU Usage
	cpuPercent, _ := cpu.Percent(time.Second, false)
	cpuUsage := 0.0
	if len(cpuPercent) > 0 {
		cpuUsage = cpuPercent[0]
	}

	// Отримання IP
	ips := []string{}
	ifaces, _ := net.Interfaces()
	for _, i := range ifaces {
		addrs, _ := i.Addrs()
		for _, addr := range addrs {
			ips = append(ips, addr.String())
		}
	}

	// Отримання Користувача через WMI
	type Win32_ComputerSystem struct {
		UserName string
	}
	var compSystems []Win32_ComputerSystem
	wmi.Query("SELECT UserName FROM Win32_ComputerSystem", &compSystems)
	user := "Unknown"
	if len(compSystems) > 0 && compSystems[0].UserName != "" {
		user = compSystems[0].UserName
	}

	// Отримання Дисків
	parts, _ := disk.Partitions(false)
	dStats := []DiskStatus{}
	for _, p := range parts {
		u, _ := disk.Usage(p.Mountpoint)
		if u.Total > 0 {
			dStats = append(dStats, DiskStatus{
				Drive: p.Mountpoint, TotalSpace: u.Total, FreeSpace: u.Free, UsedPercent: u.UsedPercent,
			})
		}
	}

	// Battery (для ноутбуків)
	var batteries []Win32_Battery
	wmi.Query("SELECT EstimatedChargeRemaining, BatteryStatus FROM Win32_Battery", &batteries)
	var batteryInfo *BatteryInfo
	if len(batteries) > 0 {
		batteryInfo = &BatteryInfo{
			ChargePercent: batteries[0].EstimatedChargeRemaining,
			Status:        getBatteryStatus(batteries[0].BatteryStatus),
		}
	}

	// Antivirus (SecurityCenter2)
	var avProducts []AntiVirusProduct
	wmi.QueryNamespace("SELECT DisplayName, ProductState FROM AntiVirusProduct", &avProducts, "root\\SecurityCenter2")
	antivirusList := []AntivirusInfo{}
	for _, av := range avProducts {
		// ProductState: біти 4-7 визначають стан (0x10 = активний)
		isActive := (av.ProductState & 0x1000) != 0
		antivirusList = append(antivirusList, AntivirusInfo{
			Name:   av.DisplayName,
			Active: isActive,
		})
	}

	// Recent Windows Updates (останні 10)
	var updates []Win32_QuickFixEngineering
	wmi.Query("SELECT HotFixID, InstalledOn FROM Win32_QuickFixEngineering", &updates)
	updateList := []UpdateInfo{}
	count := 0
	for _, u := range updates {
		if count >= 10 {
			break
		}
		if u.HotFixID != "" {
			updateList = append(updateList, UpdateInfo{
				HotFixID:    u.HotFixID,
				InstalledOn: u.InstalledOn,
			})
			count++
		}
	}

	return DynamicData{
		Timestamp:     time.Now().Unix(),
		Uptime:        hInfo.Uptime,
		CurrentUser:   user,
		IPAddresses:   ips,
		RAMUsage:      vmStat.UsedPercent,
		CPUUsage:      cpuUsage,
		Disks:         dStats,
		Battery:       batteryInfo,
		Antivirus:     antivirusList,
		RecentUpdates: updateList,
	}
}

// --- ФУНКЦІЇ ВІДПРАВКИ ДАНИХ ---

// loadConfig завантажує конфігурацію з файлу config.json
func loadConfig() (*Config, error) {
	// Шукаємо config.json в тій же директорії що і executable
	exePath, err := os.Executable()
	if err != nil {
		return nil, fmt.Errorf("не вдалося отримати шлях до executable: %w", err)
	}

	// Отримуємо директорію executable
	exeDir := exePath[:len(exePath)-len("orange_agent.exe")]
	configPath := exeDir + "config.json"

	// Спробуємо прочитати з директорії executable
	data, err := os.ReadFile(configPath)
	if err != nil {
		// Якщо не знайдено - пробуємо поточну директорію
		data, err = os.ReadFile("config.json")
		if err != nil {
			return nil, fmt.Errorf("не вдалося прочитати config.json: %w", err)
		}
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("невалідний JSON у config.json: %w", err)
	}

	// Перевіряємо обов'язкові поля
	if config.ServerURL == "" {
		return nil, fmt.Errorf("server_url обов'язковий у config.json")
	}
	if config.APIKey == "" || config.APISecret == "" {
		return nil, fmt.Errorf("api_key та api_secret обов'язкові у config.json")
	}

	return &config, nil
}

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

// sendToServer відправляє дані на Frappe сервер
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

	// Формуємо payload для Frappe API
	payload := map[string]string{
		"static_data":  string(staticJSON),
		"dynamic_data": string(dynamicJSON),
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("помилка формування payload: %w", err)
	}

	// Формуємо URL для API
	apiURL := config.ServerURL + "/api/method/orange_inventory.agent_api.report_machine_data"

	// Створюємо HTTP запит
	req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("помилка створення запиту: %w", err)
	}

	// Встановлюємо заголовки
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "token "+config.APIKey+":"+config.APISecret)
	req.Header.Set("Accept", "application/json")

	// Виконуємо запит з таймаутом
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("помилка виконання запиту: %w", err)
	}
	defer resp.Body.Close()

	// Читаємо відповідь
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("помилка читання відповіді: %w", err)
	}

	// Перевіряємо статус код
	if resp.StatusCode != 200 {
		return fmt.Errorf("сервер повернув помилку %d: %s", resp.StatusCode, string(respBody))
	}

	// Парсимо відповідь
	var serverResp ServerResponse
	if err := json.Unmarshal(respBody, &serverResp); err != nil {
		return fmt.Errorf("невалідна відповідь сервера: %w", err)
	}

	// Перевіряємо на помилки
	if serverResp.Exception != "" {
		return fmt.Errorf("сервер повернув виключення: %s", serverResp.Exception)
	}

	// Логуємо успішний результат
	if serverResp.Message.Created {
		log.Printf("✓ Створено новий актив: %s", serverResp.Message.AssetName)
	} else {
		log.Printf("✓ Оновлено актив: %s", serverResp.Message.AssetName)
	}

	return nil
}

// --- ФУНКЦІЇ ОНОВЛЕННЯ ---

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

	// Створюємо batch скрипт для оновлення
	// Batch скрипт виконується після завершення поточного процесу
	batContent := fmt.Sprintf(`@echo off
echo Оновлення Orange Inventory Agent...
timeout /t 2 /nobreak >nul

:: Видаляємо стару резервну копію
if exist "%s" del /f /q "%s"

:: Перейменовуємо поточний exe в old
move /y "%s" "%s"

:: Переміщуємо новий exe на місце поточного
move /y "%s" "%s"

:: Перезапускаємо завдання
schtasks /end /tn "%s" >nul 2>&1
schtasks /run /tn "%s"

:: Видаляємо batch файл
del /f /q "%s"
`, oldPath, oldPath, exePath, oldPath, newExePath, exePath, TaskName, TaskName, batPath)

	// Записуємо batch скрипт
	if err := os.WriteFile(batPath, []byte(batContent), 0755); err != nil {
		return fmt.Errorf("не вдалося створити update.bat: %w", err)
	}

	// Запускаємо batch скрипт у фоновому режимі
	cmd := exec.Command("cmd", "/c", "start", "/b", "", batPath)
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("не вдалося запустити update.bat: %w", err)
	}

	log.Println("✓ Оновлення запущено. Агент буде перезапущено...")
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

// --- ФУНКЦІЇ ВСТАНОВЛЕННЯ ---

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

// installTask створює заплановане завдання Windows
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

	// Видаляємо існуюче завдання
	exec.Command("schtasks", "/delete", "/tn", TaskName, "/f").Run()

	// Створюємо нове завдання
	cmd := exec.Command("schtasks", "/create",
		"/tn", TaskName,
		"/tr", fmt.Sprintf("\"%s\"", exePath),
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

	// Запускаємо завдання одразу
	exec.Command("schtasks", "/run", "/tn", TaskName).Run()

	return nil
}

// uninstallTask видаляє заплановане завдання Windows
func uninstallTask() error {
	if !isAdmin() {
		return fmt.Errorf("потрібні права адміністратора. Запустіть як Administrator")
	}

	// Зупиняємо завдання
	exec.Command("schtasks", "/end", "/tn", TaskName).Run()

	// Видаляємо завдання
	cmd := exec.Command("schtasks", "/delete", "/tn", TaskName, "/f")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("помилка видалення завдання: %w\n%s", err, string(output))
	}

	return nil
}

// showStatus показує статус завдання
func showStatus() {
	cmd := exec.Command("schtasks", "/query", "/tn", TaskName, "/v", "/fo", "LIST")
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Завдання '%s' не знайдено\n", TaskName)
		return
	}
	fmt.Println(string(output))
}

// --- ГОЛОВНА ФУНКЦІЯ ---

func main() {
	// Парсимо аргументи командного рядка
	installFlag := flag.Bool("install", false, "Встановити як заплановане завдання Windows (кожні 15 хв)")
	uninstallFlag := flag.Bool("uninstall", false, "Видалити заплановане завдання")
	statusFlag := flag.Bool("status", false, "Показати статус завдання")
	silentFlag := flag.Bool("silent", false, "Тихий режим (без виводу в консоль)")
	versionFlag := flag.Bool("version", false, "Показати версію")
	flag.Parse()

	// Налаштування логування
	if *silentFlag {
		log.SetOutput(io.Discard)
	} else {
		log.SetFlags(log.LstdFlags | log.Lshortfile)
	}

	// Обробка команд
	if *versionFlag {
		fmt.Printf("Orange Inventory Agent v%s\n", AppVersion)
		return
	}

	if *statusFlag {
		showStatus()
		return
	}

	if *installFlag {
		fmt.Println("============================================")
		fmt.Printf(" Orange Inventory Agent v%s - Install\n", AppVersion)
		fmt.Println("============================================")
		fmt.Println()

		if err := installTask(); err != nil {
			fmt.Printf("[ERROR] %v\n", err)
			os.Exit(1)
		}

		fmt.Println("[SUCCESS] Агент успішно встановлено!")
		fmt.Println()
		fmt.Printf("  Завдання:  %s\n", TaskName)
		fmt.Printf("  Інтервал:  Кожні %d хвилин\n", TaskInterval)
		fmt.Println("  Запуск:    Від імені SYSTEM")
		fmt.Println()
		fmt.Println("Команди:")
		fmt.Println("  --status     Перевірити статус")
		fmt.Println("  --uninstall  Видалити завдання")
		return
	}

	if *uninstallFlag {
		fmt.Println("============================================")
		fmt.Printf(" Orange Inventory Agent v%s - Uninstall\n", AppVersion)
		fmt.Println("============================================")
		fmt.Println()

		if err := uninstallTask(); err != nil {
			fmt.Printf("[ERROR] %v\n", err)
			os.Exit(1)
		}

		fmt.Println("[SUCCESS] Агент успішно видалено!")
		return
	}

	// --- ЗВИЧАЙНИЙ РЕЖИМ: ЗБІР ТА ВІДПРАВКА ДАНИХ ---

	log.Printf("Orange Inventory Agent v%s", AppVersion)
	log.Println("============================")

	// Завантажуємо конфігурацію
	config, err := loadConfig()
	if err != nil {
		log.Printf("⚠ Конфігурацію не знайдено: %v", err)
		log.Println("Запуск в режимі локального виводу (без відправки на сервер)")
		config = nil
	} else {
		log.Printf("✓ Конфігурація завантажена (сервер: %s)", config.ServerURL)
	}

	// Збираємо статичні дані
	log.Println("\n=== ЗБІР СТАТИЧНИХ ДАНИХ ===")
	static := getStaticInfo()
	log.Printf("Hostname: %s", static.Hostname)
	log.Printf("OS: %s %s", static.Platform, static.OSVersion)
	log.Printf("CPU: %s (%d cores)", static.CPUModel, static.CPUCores)
	log.Printf("RAM: %.2f GB", float64(static.TotalRAM)/(1024*1024*1024))
	log.Printf("Serial: %s", static.BIOS.SerialNumber)

	// Збираємо динамічні дані
	log.Println("\n=== ЗБІР ДИНАМІЧНИХ ДАНИХ ===")
	dynamic := getDynamicInfo()
	log.Printf("CPU Usage: %.1f%%", dynamic.CPUUsage)
	log.Printf("RAM Usage: %.1f%%", dynamic.RAMUsage)
	log.Printf("Current User: %s", dynamic.CurrentUser)
	log.Printf("Uptime: %d seconds", dynamic.Uptime)

	// Відправляємо на сервер якщо є конфігурація
	if config != nil {
		log.Println("\n=== ВІДПРАВКА НА СЕРВЕР ===")
		if err := sendToServer(config, static, dynamic); err != nil {
			log.Printf("✗ Помилка відправки: %v", err)
			os.Exit(1)
		}
		log.Println("✓ Дані успішно відправлено!")

		// Перевіряємо оновлення
		log.Println("\n=== ПЕРЕВІРКА ОНОВЛЕНЬ ===")
		updateResp, err := checkForUpdate(config)
		if err != nil {
			log.Printf("⚠ Не вдалося перевірити оновлення: %v", err)
		} else if updateResp.Message.UpdateAvailable {
			log.Printf("📦 Доступна нова версія: %s (поточна: %s)", updateResp.Message.LatestVersion, AppVersion)
			if updateResp.Message.ReleaseNotes != "" {
				log.Printf("   Зміни: %s", updateResp.Message.ReleaseNotes)
			}

			// Завантажуємо оновлення
			log.Println("⬇ Завантаження оновлення...")
			newExePath, err := downloadUpdate(config, updateResp.Message.DownloadURL, updateResp.Message.Checksum)
			if err != nil {
				log.Printf("✗ Помилка завантаження: %v", err)
			} else {
				log.Println("✓ Завантажено успішно!")

				// Виконуємо оновлення
				if err := performUpdate(newExePath); err != nil {
					log.Printf("✗ Помилка оновлення: %v", err)
					os.Remove(newExePath)
				}
				// Виходимо, щоб batch скрипт міг замінити exe
				os.Exit(0)
			}
		} else {
			log.Printf("✓ Версія актуальна (%s)", AppVersion)
		}
	} else {
		// Локальний вивід JSON для дебагу
		log.Println("\n=== STATIC DATA JSON ===")
		sJson, _ := json.MarshalIndent(static, "", "  ")
		fmt.Println(string(sJson))

		log.Println("\n=== DYNAMIC DATA JSON ===")
		dJson, _ := json.MarshalIndent(dynamic, "", "  ")
		fmt.Println(string(dJson))
	}
}
