//go:build linux
// +build linux

package main

import (
	"log"
)

// syncBlockedSoftware на Linux - заглушка
// Linux не має вбудованої підтримки Software Restriction Policies як Windows
// Для блокування ПЗ на Linux потрібні інші механізми (AppArmor, SELinux, тощо)
func syncBlockedSoftware(config *Config, agentID string) error {
	log.Println("ℹ Блокування ПЗ не підтримується на Linux")
	// TODO: Реалізувати блокування через:
	// - AppArmor profiles
	// - SELinux policies
	// - cgroups
	// - LD_PRELOAD tricks
	return nil
}

// syncBlockedDomains на Linux - заглушка
// TODO: Реалізувати блокування через /etc/hosts та iptables
func syncBlockedDomains(config *Config, agentID string) error {
	log.Println("ℹ Блокування доменів на Linux - заплановано")
	// TODO: Реалізувати блокування через:
	// - /etc/hosts
	// - iptables/nftables
	// - dnsmasq
	return nil
}
