package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
)

// --- КОНСТАНТИ ---
const (
	AppVersion   = "1.8"
	TaskName     = "OrangeInventoryAgent"
	TaskInterval = 15 // хвилин
)

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
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	// Логування у файл (для діагностики scheduled task)
	exePath, _ := getExePath()
	logPath := filepath.Join(filepath.Dir(exePath), "orange_agent.log")
	logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err == nil {
		if *silentFlag {
			log.SetOutput(logFile)
		} else {
			// Вивід і в консоль, і у файл
			log.SetOutput(io.MultiWriter(os.Stdout, logFile))
		}
		defer logFile.Close()
	} else if *silentFlag {
		log.SetOutput(io.Discard)
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
	runAgent()
}

// runAgent виконує основну логіку агента
func runAgent() {
	log.Printf("Orange Inventory Agent v%s", AppVersion)
	log.Println("============================")

	// Перевіряємо статус черги
	queueSize, oldestTime := GetQueueStatus()
	if queueSize > 0 {
		log.Printf("📋 В черзі очікують відправки: %d запитів (найстаріший: %v)", queueSize, oldestTime.Format("2006-01-02 15:04"))
	}

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
			log.Printf("⚠ Помилка відправки (дані збережено в чергу): %v", err)
			// Не виходимо з помилкою - дані в черзі
		} else {
			log.Println("✓ Дані успішно відправлено!")
		}

		// Перевіряємо оновлення
		checkAndUpdate(config)
	} else {
		// Локальний вивід JSON для дебагу
		printLocalData(static, dynamic)
	}
}

// checkAndUpdate перевіряє та виконує оновлення
func checkAndUpdate(config *Config) {
	log.Println("\n=== ПЕРЕВІРКА ОНОВЛЕНЬ ===")
	updateResp, err := checkForUpdate(config)
	if err != nil {
		log.Printf("⚠ Не вдалося перевірити оновлення: %v", err)
		return
	}

	if !updateResp.Message.UpdateAvailable {
		log.Printf("✓ Версія актуальна (%s)", AppVersion)
		return
	}

	log.Printf("📦 Доступна нова версія: %s (поточна: %s)", updateResp.Message.LatestVersion, AppVersion)
	if updateResp.Message.ReleaseNotes != "" {
		log.Printf("   Зміни: %s", updateResp.Message.ReleaseNotes)
	}

	// Завантажуємо оновлення
	log.Println("⬇ Завантаження оновлення...")
	newExePath, err := downloadUpdate(config, updateResp.Message.DownloadURL, updateResp.Message.Checksum)
	if err != nil {
		log.Printf("✗ Помилка завантаження: %v", err)
		return
	}
	log.Println("✓ Завантажено успішно!")

	// Виконуємо оновлення
	if err := performUpdate(newExePath); err != nil {
		log.Printf("✗ Помилка оновлення: %v", err)
		os.Remove(newExePath)
		return
	}

	// Виходимо, щоб batch скрипт міг замінити exe
	os.Exit(0)
}

// printLocalData виводить дані локально для дебагу
func printLocalData(static StaticData, dynamic DynamicData) {
	log.Println("\n=== STATIC DATA JSON ===")
	sJson, _ := json.MarshalIndent(static, "", "  ")
	fmt.Println(string(sJson))

	log.Println("\n=== DYNAMIC DATA JSON ===")
	dJson, _ := json.MarshalIndent(dynamic, "", "  ")
	fmt.Println(string(dJson))
}
