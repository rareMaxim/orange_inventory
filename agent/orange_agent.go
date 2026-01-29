package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/yusufpapurcu/wmi"
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
type Win32_VideoController struct{ Name string }

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

type Win32_DesktopMonitor struct {
	Name         string
	ScreenWidth  uint32
	ScreenHeight uint32
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

	// Monitors
	var monitors []Win32_DesktopMonitor
	wmi.Query("SELECT Name, ScreenWidth, ScreenHeight FROM Win32_DesktopMonitor", &monitors)
	monitorList := []MonitorInfo{}
	for _, m := range monitors {
		monitorList = append(monitorList, MonitorInfo{
			Name:   m.Name,
			Width:  m.ScreenWidth,
			Height: m.ScreenHeight,
		})
	}

	// Installed Software (може бути повільним)
	var software []Win32_Product
	wmi.Query("SELECT Name, Version, Vendor FROM Win32_Product", &software)
	softwareList := []SoftwareInfo{}
	for _, s := range software {
		if s.Name != "" {
			softwareList = append(softwareList, SoftwareInfo{
				Name:    s.Name,
				Version: s.Version,
				Vendor:  s.Vendor,
			})
		}
	}

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

	// Отримання Користувача
	users, _ := host.Users()
	user := "None"
	if len(users) > 0 {
		user = users[0].User
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

// --- ГОЛОВНА ФУНКЦІЯ ---

func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.Println("Orange Inventory Agent v1.0")
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
