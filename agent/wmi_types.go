package main

// --- WMI ДОПОМІЖНІ СТРУКТУРИ ---
// Ці структури використовуються для запитів до WMI (Windows Management Instrumentation)

// Win32_BaseBoard - материнська плата
type Win32_BaseBoard struct {
	SerialNumber string
}

// Win32_PhysicalMemory - фізична пам'ять
type Win32_PhysicalMemory struct {
	Capacity     uint64
	Speed        uint32
	Manufacturer string
}

// Win32_VideoController - відеокарта
type Win32_VideoController struct {
	Name                        string
	CurrentHorizontalResolution uint32
	CurrentVerticalResolution   uint32
}

// Win32_BIOS - BIOS інформація
type Win32_BIOS struct {
	SerialNumber      string
	Manufacturer      string
	SMBIOSBIOSVersion string
	ReleaseDate       string
}

// Win32_ComputerSystem - інформація про комп'ютер
type Win32_ComputerSystem struct {
	Manufacturer string
	Model        string
	Domain       string
	PCSystemType uint16
	UserName     string
}

// Win32_NetworkAdapter - мережевий адаптер
type Win32_NetworkAdapter struct {
	Name       string
	MACAddress string
	NetEnabled bool
}

// Win32_DiskDrive - жорсткий диск
type Win32_DiskDrive struct {
	Model         string
	SerialNumber  string
	Size          uint64
	MediaType     string
	InterfaceType string
}

// Win32_Product - встановлене ПЗ (повільний метод, не використовуємо)
type Win32_Product struct {
	Name    string
	Version string
	Vendor  string
}

// Win32_Printer - принтер
type Win32_Printer struct {
	Name     string
	PortName string
	Default  bool
	Network  bool
}

// Win32_Battery - батарея
type Win32_Battery struct {
	EstimatedChargeRemaining uint16
	BatteryStatus            uint16
}

// Win32_QuickFixEngineering - оновлення Windows
type Win32_QuickFixEngineering struct {
	HotFixID    string
	InstalledOn string
}

// AntiVirusProduct - антивірусний продукт (SecurityCenter2)
type AntiVirusProduct struct {
	DisplayName  string
	ProductState uint32
}

// Win32_Service - служба Windows
type Win32_Service struct {
	Name        string
	DisplayName string
	State       string
	StartMode   string
}

// Win32_StartupCommand - програма автозапуску
type Win32_StartupCommand struct {
	Name     string
	Command  string
	Location string
	User     string
}

// Win32_Process - процес
type Win32_Process struct {
	Name           string
	ProcessId      uint32
	WorkingSetSize uint64
}

// Win32_EncryptableVolume - шифрований том (BitLocker)
type Win32_EncryptableVolume struct {
	ProtectionStatus uint32
}

// FirewallProfile - профіль брандмауера
type FirewallProfile struct {
	Enabled uint32
}
