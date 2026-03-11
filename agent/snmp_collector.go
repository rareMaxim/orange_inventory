package main

import (
	"fmt"
	"log"
	"net"
	"strings"
	"time"

	"github.com/gosnmp/gosnmp"
)

// CollectSNMP виконує опитування списку пристроїв паралельно
func CollectSNMP(targets []SNMPTarget) []SNMPReport {
	if len(targets) == 0 {
		return nil
	}

	results := make([]SNMPReport, len(targets))
	
	for i, target := range targets {
		log.Printf("📡 SNMP: Опитування %s (%s)...", target.AssetName, target.IP)
		report, err := pollDevice(target)
		if err != nil {
			log.Printf("⚠ SNMP: Помилка опитування %s: %v", target.IP, err)
			results[i] = SNMPReport{
				AssetName: target.AssetName,
				IP:        target.IP,
				Error:     err.Error(),
			}
		} else {
			results[i] = *report
		}
	}

	return results
}

func pollDevice(target SNMPTarget) (*SNMPReport, error) {
	gs := &gosnmp.GoSNMP{
		Target:    target.IP,
		Port:      161,
		Community: target.Community,
		Version:   gosnmp.Version2c,
		Timeout:   time.Duration(3) * time.Second,
		Retries:   2,
		MaxOids:   60,
	}

	err := gs.Connect()
	if err != nil {
		return nil, fmt.Errorf("connect error: %w", err)
	}
	defer gs.Conn.Close()

	// 1. Отримуємо імена інтерфейсів (ifName або ifDescr як fallback)
	// ifName: 1.3.6.1.2.1.31.1.1.1.1
	// ifDescr: 1.3.6.1.2.1.2.2.1.2
	names, err := gs.WalkAll(".1.3.6.1.2.1.31.1.1.1.1")
	if err != nil || len(names) == 0 {
		names, err = gs.WalkAll(".1.3.6.1.2.1.2.2.1.2")
	}
	if err != nil {
		return nil, fmt.Errorf("walk interface names error: %w", err)
	}

	// 2. Отримуємо MAC-адреси (ifPhysAddress)
	// ifPhysAddress OID: 1.3.6.1.2.1.2.2.1.6
	macs, err := gs.WalkAll(".1.3.6.1.2.1.2.2.1.6")
	if err != nil {
		return nil, fmt.Errorf("walk ifPhysAddress error: %w", err)
	}

	// 3. Отримуємо стани (ifOperStatus)
	// ifOperStatus OID: 1.3.6.1.2.1.2.2.1.8
	statuses, err := gs.WalkAll(".1.3.6.1.2.1.2.2.1.8")
	if err != nil {
		return nil, fmt.Errorf("walk ifOperStatus error: %w", err)
	}

	// 4. Отримуємо швидкість (ifSpeed)
	// ifSpeed OID: 1.3.6.1.2.1.2.2.1.5 (для швидкостей до 4Gbps)
	speeds, err := gs.WalkAll(".1.3.6.1.2.1.2.2.1.5")
	if err != nil {
		return nil, fmt.Errorf("walk ifSpeed error: %w", err)
	}

	report := &SNMPReport{
		AssetName: target.AssetName,
		IP:        target.IP,
	}

	// Карта індексів інтерфейсів
	ifaces := make(map[int]*SNMPInterface)

	// Допоміжна функція для отримання індексу з OID
	getIndex := func(oid string) int {
		parts := strings.Split(oid, ".")
		if len(parts) > 0 {
			var idx int
			fmt.Sscanf(parts[len(parts)-1], "%d", &idx)
			return idx
		}
		return 0
	}

	for _, pdu := range names {
		idx := getIndex(pdu.Name)
		ifaces[idx] = &SNMPInterface{
			Index: idx,
			Name:  string(pdu.Value.([]byte)),
		}
	}

	for _, pdu := range macs {
		idx := getIndex(pdu.Name)
		if iface, ok := ifaces[idx]; ok {
			val := pdu.Value.([]byte)
			if len(val) == 6 {
				iface.MAC = net.HardwareAddr(val).String()
			}
		}
	}

	for _, pdu := range statuses {
		idx := getIndex(pdu.Name)
		if iface, ok := ifaces[idx]; ok {
			iface.Status = int(gosnmp.ToBigInt(pdu.Value).Int64())
		}
	}

	for _, pdu := range speeds {
		idx := getIndex(pdu.Name)
		if iface, ok := ifaces[idx]; ok {
			iface.Speed = uint64(gosnmp.ToBigInt(pdu.Value).Int64())
		}
	}

	for _, iface := range ifaces {
		// Пропускаємо інтерфейси без імен або технічні (lo, bridge0 без MAC тощо)
		if iface.Name == "" || (iface.MAC == "" && iface.Status != 1) {
			continue
		}
		report.Interfaces = append(report.Interfaces, *iface)
	}

	// 5. Отримуємо сусідів (Bridge FDB Table)
	// dot1dTpFdbAddress: 1.3.6.1.2.1.17.4.3.1.1
	fdbAddresses, err := gs.WalkAll(".1.3.6.1.2.1.17.4.3.1.1")
	if err == nil {
		for _, pdu := range fdbAddresses {
			val, ok := pdu.Value.([]byte)
			if ok && len(val) == 6 {
				mac := net.HardwareAddr(val).String()
				// Пропускаємо власні MAC-адреси пристрою
				isOwnMac := false
				for _, iface := range report.Interfaces {
					if strings.EqualFold(iface.MAC, mac) {
						isOwnMac = true
						break
					}
				}
				if !isOwnMac {
					report.Neighbors = append(report.Neighbors, NeighborInfo{
						MACAddress: mac,
						Interface:  "SNMP-Discovery",
					})
				}
			}
		}
	}

	return report, nil
}
