//go:build linux
// +build linux

package main

// getCertificates повертає порожній список на Linux
func getCertificates() []CertificateInfo {
	return []CertificateInfo{}
}
