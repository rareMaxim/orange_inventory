//go:build windows
// +build windows

package main

import (
	"crypto/sha1"
	"crypto/x509"
	"encoding/hex"
	"encoding/pem"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
)

const certDir = `C:\My Certificates and CRLs 13`

// getCertificates збирає сертифікати з теки certDir
func getCertificates() []CertificateInfo {
	certs := []CertificateInfo{}

	// Перевіряємо чи існує тека
	if _, err := os.Stat(certDir); os.IsNotExist(err) {
		log.Printf("⚠ Тека сертифікатів не знайдена: %s", certDir)
		return certs
	}

	// Шукаємо .cer файли
	pattern := filepath.Join(certDir, "*.cer")
	matches, err := filepath.Glob(pattern)
	if err != nil {
		log.Printf("⚠ Помилка пошуку сертифікатів: %v", err)
		return certs
	}

	for _, filePath := range matches {
		cert, err := parseCertFile(filePath)
		if err != nil {
			log.Printf("⚠ Не вдалося прочитати сертифікат %s: %v", filepath.Base(filePath), err)
			continue
		}
		certs = append(certs, *cert)
	}

	return certs
}

// parseCertFile парсить .cer файл (DER або PEM формат)
func parseCertFile(filePath string) (*CertificateInfo, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("помилка читання: %w", err)
	}

	var x509Cert *x509.Certificate

	// Спробуємо PEM формат
	block, _ := pem.Decode(data)
	if block != nil {
		x509Cert, err = x509.ParseCertificate(block.Bytes)
		if err != nil {
			return nil, fmt.Errorf("помилка парсингу PEM: %w", err)
		}
	} else {
		// Спробуємо DER формат
		x509Cert, err = x509.ParseCertificate(data)
		if err != nil {
			return nil, fmt.Errorf("помилка парсингу DER: %w", err)
		}
	}

	// Обчислюємо SHA1 відбиток
	thumbprint := sha1.Sum(x509Cert.Raw)

	// Отримуємо Subject CN
	subjectCN := x509Cert.Subject.CommonName
	if subjectCN == "" {
		subjectCN = x509Cert.Subject.String()
	}

	// Отримуємо Issuer CN
	issuerCN := x509Cert.Issuer.CommonName
	if issuerCN == "" {
		issuerCN = x509Cert.Issuer.String()
	}

	return &CertificateInfo{
		SubjectCN:    subjectCN,
		IssuerCN:     issuerCN,
		SerialNumber: fmt.Sprintf("%X", x509Cert.SerialNumber),
		NotBefore:    x509Cert.NotBefore.Format("2006-01-02"),
		NotAfter:     x509Cert.NotAfter.Format("2006-01-02"),
		Thumbprint:   strings.ToUpper(hex.EncodeToString(thumbprint[:])),
		FileName:     filepath.Base(filePath),
	}, nil
}
