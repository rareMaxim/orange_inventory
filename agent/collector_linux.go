//go:build linux
// +build linux

package main

import (
	"net"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/process"
)

// --- ФУНКЦІЇ ЗБОРУ ДАНИХ (Linux) ---

// getInstalledSoftware отримує список встановленого ПЗ
func getInstalledSoftware() []SoftwareInfo {
	softwareList := []SoftwareInfo{}

	// Спробуємо dpkg (Debian/Ubuntu)
	if packages := getDpkgPackages(); len(packages) > 0 {
		return packages
	}

	// Спробуємо rpm (RHEL/CentOS/Fedora)
	if packages := getRpmPackages(); len(packages) > 0 {
		return packages
	}

	return softwareList
}

// getDpkgPackages отримує пакети через dpkg
func getDpkgPackages() []SoftwareInfo {
	packages := []SoftwareInfo{}

	cmd := exec.Command("dpkg-query", "-W", "-f=${Package}|${Version}|${Maintainer}\n")
	output, err := cmd.Output()
	if err != nil {
		return packages
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		parts := strings.Split(line, "|")
		if len(parts) >= 2 && parts[0] != "" {
			packages = append(packages, SoftwareInfo{
				Name:    parts[0],
				Version: parts[1],
				Vendor:  safeGet(parts, 2),
			})
		}
	}

	return packages
}

// getRpmPackages отримує пакети через rpm
func getRpmPackages() []SoftwareInfo {
	packages := []SoftwareInfo{}

	cmd := exec.Command("rpm", "-qa", "--queryformat", "%{NAME}|%{VERSION}|%{VENDOR}\n")
	output, err := cmd.Output()
	if err != nil {
		return packages
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		parts := strings.Split(line, "|")
		if len(parts) >= 2 && parts[0] != "" {
			packages = append(packages, SoftwareInfo{
				Name:    parts[0],
				Version: parts[1],
				Vendor:  safeGet(parts, 2),
			})
		}
	}

	return packages
}

func safeGet(arr []string, idx int) string {
	if idx < len(arr) {
		return arr[idx]
	}
	return ""
}

// getMinimalStaticInfo отримує лише дані для генерації agent_id (hostname + серійні номери)
func getMinimalStaticInfo() StaticData {
	hInfo, _ := host.Info()

	boardS := readDMI("/sys/class/dmi/id/board_serial")
	if boardS == "" {
		boardS = "Unknown"
	}

	return StaticData{
		Hostname:    hInfo.Hostname,
		BoardSerial: boardS,
		BIOS: BIOSInfo{
			SerialNumber: readDMI("/sys/class/dmi/id/product_serial"),
		},
	}
}

// getStaticInfo збирає статичні дані про систему
func getStaticInfo() StaticData {
	hInfo, _ := host.Info()
	cpuInfo, _ := cpu.Info()
	vmStat, _ := mem.VirtualMemory()
	logicalCores, _ := cpu.Counts(true)

	// Board Serial (з DMI)
	boardS := readDMI("/sys/class/dmi/id/board_serial")
	if boardS == "" {
		boardS = "Unknown"
	}

	// RAM Slots (з /proc/meminfo та dmidecode)
	ramSlots := getRAMSlots()

	// GPU
	gpuNames := getGPUNames()

	// BIOS
	biosInfo := BIOSInfo{
		SerialNumber: readDMI("/sys/class/dmi/id/product_serial"),
		Manufacturer: readDMI("/sys/class/dmi/id/bios_vendor"),
		Version:      readDMI("/sys/class/dmi/id/bios_version"),
		ReleaseDate:  readDMI("/sys/class/dmi/id/bios_date"),
	}

	// System Info
	sysInfo := SystemInfo{
		Manufacturer: readDMI("/sys/class/dmi/id/sys_vendor"),
		Model:        readDMI("/sys/class/dmi/id/product_name"),
		Domain:       getDomain(),
		SystemType:   getLinuxSystemType(),
	}

	// Network Adapters
	netAdapters := getNetworkAdapters()

	// Physical Disks
	physDisks := getPhysicalDisks()

	// Monitors (X11/Wayland)
	monitorList := getMonitors()

	// Installed Software
	softwareList := getInstalledSoftware()

	// Printers (CUPS)
	printerList := getPrinters()

	cpuModel := "Unknown"
	if len(cpuInfo) > 0 {
		cpuModel = cpuInfo[0].ModelName
	}

	return StaticData{
		AgentVersion:    AppVersion,
		Hostname:        hInfo.Hostname,
		Platform:        hInfo.OS,
		OSVersion:       hInfo.PlatformVersion,
		OSEdition:       "", // Linux не має редакцій як Windows
		CPUModel:        cpuModel,
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

	// IP Addresses
	ips := getIPAddresses()

	// Current User
	currentUser := getCurrentUser()

	// Disks
	dStats := getDiskStats()

	// Battery
	batteryInfo := getBatteryInfo()

	// Services (systemd)
	serviceList := getSystemdServices()

	// Top Processes
	processList := getTopProcesses()

	// Startup Items (systemd user units)
	startupList := getStartupItems()

	// Security Status
	security := getSecurityStatus()

	return DynamicData{
		Timestamp:     time.Now().Unix(),
		Uptime:        hInfo.Uptime,
		CurrentUser:   currentUser,
		IPAddresses:   ips,
		RAMUsage:      vmStat.UsedPercent,
		CPUUsage:      cpuUsage,
		Disks:         dStats,
		Battery:       batteryInfo,
		Antivirus:     []AntivirusInfo{}, // Linux зазвичай не має традиційних AV
		RecentUpdates: []UpdateInfo{},    // TODO: реалізувати для apt/yum
		Services:      serviceList,
		TopProcesses:  processList,
		StartupItems:  startupList,
		Neighbors:     getNetworkNeighbors(),
		Security:      security,
	}
}

// --- Допоміжні функції ---

func readDMI(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(data))
}

func getRAMSlots() []RAMDetails {
	// Базова реалізація - повертаємо загальну пам'ять
	vmStat, _ := mem.VirtualMemory()
	return []RAMDetails{
		{Capacity: vmStat.Total, Speed: 0, Vendor: "Unknown"},
	}
}

func getGPUNames() []string {
	gpus := []string{}

	// Спробуємо lspci
	cmd := exec.Command("lspci")
	output, err := cmd.Output()
	if err != nil {
		return gpus
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		if strings.Contains(line, "VGA") || strings.Contains(line, "3D") {
			// Витягуємо назву GPU
			parts := strings.SplitN(line, ": ", 2)
			if len(parts) == 2 {
				gpus = append(gpus, parts[1])
			}
		}
	}

	return gpus
}

func getDomain() string {
	cmd := exec.Command("hostname", "-d")
	output, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(output))
}

func getLinuxSystemType() string {
	// Перевіряємо чи є батарея (ноутбук)
	if _, err := os.Stat("/sys/class/power_supply/BAT0"); err == nil {
		return "Laptop"
	}

	// Перевіряємо чи це віртуальна машина
	data, _ := os.ReadFile("/sys/class/dmi/id/product_name")
	product := strings.ToLower(string(data))
	if strings.Contains(product, "virtual") || strings.Contains(product, "vmware") ||
		strings.Contains(product, "kvm") || strings.Contains(product, "qemu") {
		return "Virtual Machine"
	}

	return "Desktop"
}

func getNetworkAdapters() []NetworkAdapterInfo {
	adapters := []NetworkAdapterInfo{}

	ifaces, err := net.Interfaces()
	if err != nil {
		return adapters
	}

	for _, iface := range ifaces {
		if iface.Flags&net.FlagLoopback != 0 {
			continue // Пропускаємо loopback
		}

		adapters = append(adapters, NetworkAdapterInfo{
			Name:       iface.Name,
			MACAddress: iface.HardwareAddr.String(),
			Enabled:    iface.Flags&net.FlagUp != 0,
		})
	}

	return adapters
}

func getPhysicalDisks() []PhysicalDiskInfo {
	disks := []PhysicalDiskInfo{}

	// Читаємо з /sys/block
	entries, err := os.ReadDir("/sys/block")
	if err != nil {
		return disks
	}

	for _, entry := range entries {
		name := entry.Name()
		// Пропускаємо loop, ram, etc
		if strings.HasPrefix(name, "loop") || strings.HasPrefix(name, "ram") {
			continue
		}

		// Читаємо розмір
		sizePath := filepath.Join("/sys/block", name, "size")
		sizeData, _ := os.ReadFile(sizePath)
		var size uint64
		if sizeData != nil {
			var sizeBlocks uint64
			if _, err := strings.NewReader(strings.TrimSpace(string(sizeData))).Read([]byte{}); err == nil {
				// Розмір в 512-байт блоках
				sizeBlocks = parseUint64(strings.TrimSpace(string(sizeData)))
				size = sizeBlocks * 512
			}
		}

		// Модель
		modelPath := filepath.Join("/sys/block", name, "device/model")
		model := strings.TrimSpace(readFile(modelPath))

		disks = append(disks, PhysicalDiskInfo{
			Model:         model,
			SerialNumber:  "", // Потребує root для /dev/disk/by-id
			Size:          size,
			MediaType:     detectMediaType(name),
			InterfaceType: detectInterfaceType(name),
		})
	}

	return disks
}

func parseUint64(s string) uint64 {
	var n uint64
	for _, c := range s {
		if c >= '0' && c <= '9' {
			n = n*10 + uint64(c-'0')
		}
	}
	return n
}

func readFile(path string) string {
	data, _ := os.ReadFile(path)
	return string(data)
}

func detectMediaType(name string) string {
	rotational := readFile(filepath.Join("/sys/block", name, "queue/rotational"))
	if strings.TrimSpace(rotational) == "0" {
		return "SSD"
	}
	return "HDD"
}

func detectInterfaceType(name string) string {
	if strings.HasPrefix(name, "nvme") {
		return "NVMe"
	}
	if strings.HasPrefix(name, "sd") {
		return "SATA/SAS"
	}
	return "Unknown"
}

func getMonitors() []MonitorInfo {
	monitors := []MonitorInfo{}

	// Спробуємо xrandr
	cmd := exec.Command("xrandr", "--current")
	output, err := cmd.Output()
	if err != nil {
		return monitors
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		if strings.Contains(line, " connected") {
			// Парсимо роздільність
			parts := strings.Fields(line)
			name := parts[0]
			for _, p := range parts {
				if strings.Contains(p, "x") && strings.Contains(p, "+") {
					res := strings.Split(p, "+")[0]
					dims := strings.Split(res, "x")
					if len(dims) == 2 {
						monitors = append(monitors, MonitorInfo{
							Name:   name,
							Width:  uint32(parseUint64(dims[0])),
							Height: uint32(parseUint64(dims[1])),
						})
					}
					break
				}
			}
		}
	}

	return monitors
}

func getPrinters() []PrinterInfo {
	printers := []PrinterInfo{}

	cmd := exec.Command("lpstat", "-p", "-d")
	output, err := cmd.Output()
	if err != nil {
		return printers
	}

	lines := strings.Split(string(output), "\n")
	var defaultPrinter string
	for _, line := range lines {
		if strings.HasPrefix(line, "system default destination:") {
			defaultPrinter = strings.TrimPrefix(line, "system default destination: ")
		} else if strings.HasPrefix(line, "printer ") {
			parts := strings.Fields(line)
			if len(parts) >= 2 {
				name := parts[1]
				printers = append(printers, PrinterInfo{
					Name:      name,
					Port:      "", // CUPS не показує порт напряму
					IsDefault: name == defaultPrinter,
					IsNetwork: false, // TODO: визначити
				})
			}
		}
	}

	return printers
}

func getIPAddresses() []string {
	ips := []string{}
	ifaces, _ := net.Interfaces()
	for _, i := range ifaces {
		addrs, _ := i.Addrs()
		for _, addr := range addrs {
			ips = append(ips, addr.String())
		}
	}
	return ips
}

func getCurrentUser() string {
	u, err := user.Current()
	if err != nil {
		return "Unknown"
	}
	return u.Username
}

func getNetworkNeighbors() []NeighborInfo {
	neighbors := []NeighborInfo{}

	data, err := os.ReadFile("/proc/net/arp")
	if err != nil {
		return neighbors
	}

	lines := strings.Split(string(data), "\n")
	// Пропускаємо заголовок
	if len(lines) <= 1 {
		return neighbors
	}

	for _, line := range lines[1:] {
		fields := strings.Fields(line)
		if len(fields) >= 6 {
			ip := fields[0]
			mac := fields[3]
			iface := fields[5]

			// Пропускаємо нульові MAC-адреси
			if mac == "00:00:00:00:00:00" || mac == "" {
				continue
			}

			neighbors = append(neighbors, NeighborInfo{
				IPAddress:  ip,
				MACAddress: mac,
				Interface:  iface,
			})
		}
	}

	return neighbors
}

func getDiskStats() []DiskStatus {
	dStats := []DiskStatus{}
	parts, _ := disk.Partitions(false)
	for _, p := range parts {
		u, _ := disk.Usage(p.Mountpoint)
		if u != nil && u.Total > 0 {
			dStats = append(dStats, DiskStatus{
				Drive:       p.Mountpoint,
				TotalSpace:  u.Total,
				FreeSpace:   u.Free,
				UsedPercent: u.UsedPercent,
			})
		}
	}
	return dStats
}

func getBatteryInfo() *BatteryInfo {
	// Перевіряємо наявність батареї
	capacityPath := "/sys/class/power_supply/BAT0/capacity"
	statusPath := "/sys/class/power_supply/BAT0/status"

	capacityData, err := os.ReadFile(capacityPath)
	if err != nil {
		return nil
	}

	statusData, _ := os.ReadFile(statusPath)

	return &BatteryInfo{
		ChargePercent: uint16(parseUint64(strings.TrimSpace(string(capacityData)))),
		Status:        strings.TrimSpace(string(statusData)),
	}
}

func getSystemdServices() []ServiceInfo {
	services := []ServiceInfo{}

	cmd := exec.Command("systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--no-legend")
	output, err := cmd.Output()
	if err != nil {
		return services
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		fields := strings.Fields(line)
		if len(fields) >= 4 {
			services = append(services, ServiceInfo{
				Name:        strings.TrimSuffix(fields[0], ".service"),
				DisplayName: strings.Join(fields[4:], " "),
				State:       fields[2],
				StartMode:   "Auto",
			})
		}
	}

	return services
}

func getTopProcesses() []ProcessInfo {
	allProcs := []ProcessInfo{}

	procs, err := process.Processes()
	if err != nil {
		return allProcs
	}

	for _, p := range procs {
		name, _ := p.Name()
		memInfo, _ := p.MemoryInfo()
		if memInfo == nil {
			continue
		}

		memMB := float64(memInfo.RSS) / 1024 / 1024
		if memMB > 10 {
			allProcs = append(allProcs, ProcessInfo{
				Name:     name,
				PID:      uint32(p.Pid),
				MemoryMB: memMB,
			})
		}
	}

	// Сортуємо по пам'яті (від більшого до меншого) та беремо топ 10
	sort.Slice(allProcs, func(i, j int) bool {
		return allProcs[i].MemoryMB > allProcs[j].MemoryMB
	})

	if len(allProcs) > 10 {
		allProcs = allProcs[:10]
	}

	return allProcs
}

func getStartupItems() []StartupInfo {
	// Повертаємо systemd user units або /etc/xdg/autostart
	items := []StartupInfo{}

	// Читаємо /etc/xdg/autostart
	entries, err := os.ReadDir("/etc/xdg/autostart")
	if err != nil {
		return items
	}

	for _, entry := range entries {
		if strings.HasSuffix(entry.Name(), ".desktop") {
			name := strings.TrimSuffix(entry.Name(), ".desktop")
			items = append(items, StartupInfo{
				Name:     name,
				Location: "/etc/xdg/autostart",
			})
		}
	}

	return items
}

func getSecurityStatus() SecurityStatus {
	security := SecurityStatus{}

	// Firewall (iptables/nftables/ufw)
	if _, err := exec.Command("ufw", "status").Output(); err == nil {
		cmd := exec.Command("ufw", "status")
		output, _ := cmd.Output()
		security.FirewallEnabled = strings.Contains(string(output), "Status: active")
	} else {
		// Перевіряємо iptables
		cmd := exec.Command("iptables", "-L", "-n")
		output, err := cmd.Output()
		if err == nil && len(output) > 0 {
			security.FirewallEnabled = true
		}
	}

	// LUKS (еквівалент BitLocker)
	cmd := exec.Command("lsblk", "-o", "NAME,TYPE")
	output, _ := cmd.Output()
	if strings.Contains(string(output), "crypt") {
		security.BitLockerStatus = "LUKS Encrypted"
	} else {
		security.BitLockerStatus = "Not Encrypted"
	}

	// SELinux/AppArmor
	if data, err := os.ReadFile("/sys/fs/selinux/enforce"); err == nil {
		if strings.TrimSpace(string(data)) == "1" {
			security.UACEnabled = true // SELinux enforcing
		}
	} else if _, err := os.Stat("/sys/kernel/security/apparmor"); err == nil {
		security.UACEnabled = true // AppArmor enabled
	}

	// Secure Boot
	sbOutput, err := exec.Command("mokutil", "--sb-state").Output()
	if err == nil {
		security.SecureBootEnabled = strings.Contains(string(sbOutput), "SecureBoot enabled")
	}

	return security
}
