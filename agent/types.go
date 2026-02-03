package main

// --- СТРУКТУРИ ДАНИХ ---

// RAMDetails містить інформацію про планку RAM
type RAMDetails struct {
	Capacity uint64 `json:"capacity_bytes"`
	Speed    uint32 `json:"speed_mhz"`
	Vendor   string `json:"vendor"`
}

// BIOSInfo містить інформацію про BIOS
type BIOSInfo struct {
	SerialNumber string `json:"serial_number"`
	Manufacturer string `json:"manufacturer"`
	Version      string `json:"version"`
	ReleaseDate  string `json:"release_date"`
}

// SystemInfo містить інформацію про систему
type SystemInfo struct {
	Manufacturer string `json:"manufacturer"`
	Model        string `json:"model"`
	Domain       string `json:"domain"`
	SystemType   string `json:"system_type"` // Desktop, Laptop, etc.
}

// NetworkAdapterInfo містить інформацію про мережевий адаптер
type NetworkAdapterInfo struct {
	Name       string `json:"name"`
	MACAddress string `json:"mac_address"`
	Enabled    bool   `json:"enabled"`
}

// PhysicalDiskInfo містить інформацію про фізичний диск
type PhysicalDiskInfo struct {
	Model         string `json:"model"`
	SerialNumber  string `json:"serial_number"`
	Size          uint64 `json:"size_bytes"`
	MediaType     string `json:"media_type"`
	InterfaceType string `json:"interface_type"`
}

// MonitorInfo містить інформацію про монітор
type MonitorInfo struct {
	Name   string `json:"name"`
	Width  uint32 `json:"width"`
	Height uint32 `json:"height"`
}

// SoftwareInfo містить інформацію про встановлене ПЗ
type SoftwareInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
	Vendor  string `json:"vendor"`
}

// PrinterInfo містить інформацію про принтер
type PrinterInfo struct {
	Name      string `json:"name"`
	Port      string `json:"port"`
	IsDefault bool   `json:"is_default"`
	IsNetwork bool   `json:"is_network"`
}

// ServiceInfo містить інформацію про службу Windows
type ServiceInfo struct {
	Name        string `json:"name"`
	DisplayName string `json:"display_name"`
	State       string `json:"state"`
	StartMode   string `json:"start_mode"`
}

// StartupInfo містить інформацію про програму автозапуску
type StartupInfo struct {
	Name     string `json:"name"`
	Command  string `json:"command"`
	Location string `json:"location"`
	User     string `json:"user"`
}

// ProcessInfo містить інформацію про процес
type ProcessInfo struct {
	Name       string  `json:"name"`
	PID        uint32  `json:"pid"`
	CPUPercent float64 `json:"cpu_percent"`
	MemoryMB   float64 `json:"memory_mb"`
	User       string  `json:"user"`
}

// SecurityStatus містить інформацію про безпеку системи
type SecurityStatus struct {
	FirewallEnabled   bool   `json:"firewall_enabled"`
	BitLockerStatus   string `json:"bitlocker_status"`
	UACEnabled        bool   `json:"uac_enabled"`
	SecureBootEnabled bool   `json:"secure_boot_enabled"`
}

// DiskStatus містить інформацію про використання диску
type DiskStatus struct {
	Drive       string  `json:"drive"`
	TotalSpace  uint64  `json:"total_bytes"`
	FreeSpace   uint64  `json:"free_bytes"`
	UsedPercent float64 `json:"used_percent"`
}

// BatteryInfo містить інформацію про батарею
type BatteryInfo struct {
	ChargePercent uint16 `json:"charge_percent"`
	Status        string `json:"status"` // Charging, Discharging, Full, No Battery
}

// AntivirusInfo містить інформацію про антивірус
type AntivirusInfo struct {
	Name   string `json:"name"`
	Active bool   `json:"active"`
}

// UpdateInfo містить інформацію про оновлення Windows
type UpdateInfo struct {
	HotFixID    string `json:"hotfix_id"`
	InstalledOn string `json:"installed_on"`
}

// StaticData містить статичні дані про систему (змінюються рідко)
type StaticData struct {
	AgentVersion    string               `json:"agent_version"`
	Hostname        string               `json:"hostname"`
	Platform        string               `json:"os_platform"`
	OSVersion       string               `json:"os_version"`
	OSEdition       string               `json:"os_edition"` // Home, Pro, Enterprise, etc.
	CPUModel        string               `json:"cpu_model"`
	CPUCores        int                  `json:"cpu_cores"`
	TotalRAM        uint64               `json:"total_ram_bytes"`
	RAMSlots        []RAMDetails         `json:"ram_slots"`
	BoardSerial     string               `json:"board_serial"`
	GPU             []string             `json:"gpu_models"`
	BIOS            BIOSInfo             `json:"bios"`
	System          SystemInfo           `json:"system"`
	NetworkAdapters []NetworkAdapterInfo `json:"network_adapters"`
	PhysicalDisks   []PhysicalDiskInfo   `json:"physical_disks"`
	Monitors        []MonitorInfo        `json:"monitors"`
	Software        []SoftwareInfo       `json:"installed_software"`
	Printers        []PrinterInfo        `json:"printers"`
}

// DynamicData містить динамічні дані про систему (змінюються часто)
type DynamicData struct {
	Timestamp     int64           `json:"timestamp"`
	Uptime        uint64          `json:"uptime_seconds"`
	CurrentUser   string          `json:"current_user"`
	IPAddresses   []string        `json:"ip_addresses"`
	RAMUsage      float64         `json:"ram_usage_percent"`
	CPUUsage      float64         `json:"cpu_usage_percent"`
	Disks         []DiskStatus    `json:"disks"`
	Battery       *BatteryInfo    `json:"battery,omitempty"`
	Antivirus     []AntivirusInfo `json:"antivirus"`
	RecentUpdates []UpdateInfo    `json:"recent_updates"`
	Services      []ServiceInfo   `json:"services"`
	TopProcesses  []ProcessInfo   `json:"top_processes"`
	StartupItems  []StartupInfo   `json:"startup_items"`
	Security      SecurityStatus  `json:"security"`
}
