//go:build windows
// +build windows

package main

import (
	"fmt"
	"net"
	"sort"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/yusufpapurcu/wmi"
	"golang.org/x/sys/windows/registry"
	"os/exec"
	"strings"
)

// --- ФУНКЦІЇ ЗБОРУ ДАНИХ (Windows) ---

// getWindowsEdition отримує редакцію Windows (Home, Pro, Enterprise, etc.)
func getWindowsEdition() string {
	// Спробуємо через реєстр - найнадійніший метод
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows NT\CurrentVersion`, registry.READ)
	if err == nil {
		defer key.Close()

		// Спочатку EditionID (коротка назва: Home, Pro, Enterprise)
		edition, _, err := key.GetStringValue("EditionID")
		if err == nil && edition != "" {
			return edition
		}

		// Або ProductName (повна назва)
		productName, _, err := key.GetStringValue("ProductName")
		if err == nil && productName != "" {
			return productName
		}
	}

	// Fallback через WMI
	type Win32_OS struct {
		Caption string
	}
	var osInfo []Win32_OS
	wmi.Query("SELECT Caption FROM Win32_OperatingSystem", &osInfo)
	if len(osInfo) > 0 {
		return osInfo[0].Caption
	}

	return "Unknown"
}

// getWindowsBuildNumber отримує повну версію Windows (включно з Build Number)
func getWindowsBuildNumber() string {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows NT\CurrentVersion`, registry.READ)
	if err != nil {
		return ""
	}
	defer key.Close()

	// CurrentBuildNumber (наприклад "22631")
	build, _, err := key.GetStringValue("CurrentBuildNumber")
	if err != nil || build == "" {
		return ""
	}

	// UBR - Update Build Revision (наприклад 4890)
	ubr, _, err := key.GetIntegerValue("UBR")
	if err == nil {
		return fmt.Sprintf("%s.%d", build, ubr)
	}

	return build
}

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
			installLocation, _, _ := sk.GetStringValue("InstallLocation")
			installDate, _, _ := sk.GetStringValue("InstallDate")
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
				Name:            name,
				Version:         version,
				Vendor:          vendor,
				InstallDate:     installDate,
				InstallLocation: installLocation,
			})
		}
	}

	return softwareList
}

// getSystemType перетворює код типу системи в текст
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

// getBatteryStatus перетворює код статусу батареї в текст
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

// getMinimalStaticInfo отримує лише дані для генерації agent_id (hostname + серійні номери)
func getMinimalStaticInfo() StaticData {
	hInfo, _ := host.Info()

	var board []Win32_BaseBoard
	wmi.Query("SELECT SerialNumber FROM Win32_BaseBoard", &board)
	boardS := "Unknown"
	if len(board) > 0 {
		boardS = board[0].SerialNumber
	}

	var bios []Win32_BIOS
	wmi.Query("SELECT SerialNumber FROM Win32_BIOS", &bios)
	biosInfo := BIOSInfo{}
	if len(bios) > 0 {
		biosInfo.SerialNumber = bios[0].SerialNumber
	}

	return StaticData{
		Hostname:    hInfo.Hostname,
		BoardSerial: boardS,
		BIOS:        biosInfo,
	}
}

// getStaticInfo збирає статичні дані про систему
func getStaticInfo() StaticData {
	hInfo, _ := host.Info()
	cpuInfo, _ := cpu.Info()
	vmStat, _ := mem.VirtualMemory()
	logicalCores, _ := cpu.Counts(true)

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

	// Certificates
	certList := getCertificates()

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

	// Windows Edition
	osEdition := getWindowsEdition()

	// OS Version з Build Number (наприклад "10.0.22631.4890")
	osVersion := hInfo.PlatformVersion
	if buildNum := getWindowsBuildNumber(); buildNum != "" {
		osVersion = osVersion + "." + buildNum
	}

	return StaticData{
		AgentVersion:    AppVersion,
		Hostname:        hInfo.Hostname,
		Platform:        hInfo.OS,
		OSVersion:       osVersion,
		OSEdition:       osEdition,
		CPUModel:        cpuInfo[0].ModelName,
		CPUCores:        logicalCores,
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
		Certificates:    certList,
	}
}

// getDynamicInfo збирає динамічні дані про систему
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
	type Win32_ComputerSystemUser struct {
		UserName string
	}
	var compSystems []Win32_ComputerSystemUser
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

	// Windows Services (важливі служби)
	var services []Win32_Service
	wmi.Query("SELECT Name, DisplayName, State, StartMode FROM Win32_Service WHERE StartMode='Auto' OR State='Running'", &services)
	serviceList := []ServiceInfo{}
	for _, s := range services {
		serviceList = append(serviceList, ServiceInfo{
			Name:        s.Name,
			DisplayName: s.DisplayName,
			State:       s.State,
			StartMode:   s.StartMode,
		})
	}

	// Startup Items (програми автозапуску)
	var startups []Win32_StartupCommand
	wmi.Query("SELECT Name, Command, Location, User FROM Win32_StartupCommand", &startups)
	startupList := []StartupInfo{}
	for _, s := range startups {
		startupList = append(startupList, StartupInfo{
			Name:     s.Name,
			Command:  s.Command,
			Location: s.Location,
			User:     s.User,
		})
	}

	// Top Processes (топ 10 по пам'яті)
	var processes []Win32_Process
	wmi.Query("SELECT Name, ProcessId, WorkingSetSize FROM Win32_Process", &processes)

	// Сортуємо по пам'яті (від більшого до меншого)
	sort.Slice(processes, func(i, j int) bool {
		return processes[i].WorkingSetSize > processes[j].WorkingSetSize
	})

	processList := []ProcessInfo{}
	for _, p := range processes {
		if len(processList) >= 10 {
			break
		}
		memMB := float64(p.WorkingSetSize) / 1024 / 1024
		if memMB > 10 {
			processList = append(processList, ProcessInfo{
				Name:     p.Name,
				PID:      p.ProcessId,
				MemoryMB: memMB,
			})
		}
	}

	// Security Status
	security := getSecurityStatus()

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
		Services:      serviceList,
		TopProcesses:  processList,
		StartupItems:  startupList,
		Neighbors:     getNetworkNeighbors(),
		Security:      security,
	}
}

// getNetworkNeighbors збирає динамічні дані про систему
func getNetworkNeighbors() []NeighborInfo {
	neighbors := []NeighborInfo{}

	cmd := exec.Command("arp", "-a")
	output, err := cmd.Output()
	if err != nil {
		return neighbors
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		fields := strings.Fields(line)
		if len(fields) >= 3 {
			// Windows arp -a output format:
			// Internet Address      Physical Address      Type
			// 192.168.1.1           00-11-22-33-44-55     dynamic
			ip := fields[0]
			mac := strings.ReplaceAll(fields[1], "-", ":")
			
			// Перевірка чи це IP-адреса (базовий варіант)
			if strings.Count(ip, ".") == 3 && strings.Count(mac, ":") == 5 {
				neighbors = append(neighbors, NeighborInfo{
					IPAddress:  ip,
					MACAddress: strings.ToLower(mac),
				})
			}
		}
	}

	return neighbors
}

// getSecurityStatus збирає інформацію про безпеку системи
func getSecurityStatus() SecurityStatus {
	security := SecurityStatus{}

	// Firewall status
	var fwProfiles []FirewallProfile
	wmi.QueryNamespace("SELECT Enabled FROM FirewallProduct", &fwProfiles, "root\\SecurityCenter2")
	if len(fwProfiles) > 0 {
		security.FirewallEnabled = fwProfiles[0].Enabled != 0
	} else {
		// Альтернативна перевірка через реєстр
		key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile`, registry.READ)
		if err == nil {
			val, _, err := key.GetIntegerValue("EnableFirewall")
			key.Close()
			if err == nil {
				security.FirewallEnabled = val == 1
			}
		}
	}

	// BitLocker status (C: drive)
	var volumes []Win32_EncryptableVolume
	wmi.QueryNamespace("SELECT ProtectionStatus FROM Win32_EncryptableVolume WHERE DriveLetter='C:'", &volumes, "root\\CIMV2\\Security\\MicrosoftVolumeEncryption")
	if len(volumes) > 0 {
		switch volumes[0].ProtectionStatus {
		case 0:
			security.BitLockerStatus = "Off"
		case 1:
			security.BitLockerStatus = "On"
		case 2:
			security.BitLockerStatus = "Unknown"
		default:
			security.BitLockerStatus = "N/A"
		}
	} else {
		security.BitLockerStatus = "Not Available"
	}

	// UAC status
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System`, registry.READ)
	if err == nil {
		val, _, err := key.GetIntegerValue("EnableLUA")
		key.Close()
		if err == nil {
			security.UACEnabled = val == 1
		}
	}

	// Secure Boot status
	sbKey, err := registry.OpenKey(registry.LOCAL_MACHINE, `SYSTEM\CurrentControlSet\Control\SecureBoot\State`, registry.READ)
	if err == nil {
		val, _, err := sbKey.GetIntegerValue("UEFISecureBootEnabled")
		sbKey.Close()
		if err == nil {
			security.SecureBootEnabled = val == 1
		}
	}

	return security
}
