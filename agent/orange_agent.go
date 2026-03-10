package main

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"time"
)

// --- КОНСТАНТИ ---
const (
	AppVersion          = "1.12.4"
	TaskName            = "OrangeInventoryAgent"
	TaskNameCommands    = "OrangeInventoryAgent_Commands"
	TaskInterval        = 15 // хвилин (повний збір)
	CommandPollInterval = 1  // хвилин (перевірка команд)
)

// --- ГОЛОВНА ФУНКЦІЯ ---

func main() {
	// Парсимо аргументи командного рядка
	installFlag := flag.Bool("install", false, "Встановити як заплановане завдання Windows (кожні 15 хв)")
	uninstallFlag := flag.Bool("uninstall", false, "Видалити заплановане завдання")
	statusFlag := flag.Bool("status", false, "Показати статус завдання")
	silentFlag := flag.Bool("silent", false, "Тихий режим (без виводу в консоль)")
	versionFlag := flag.Bool("version", false, "Показати версію")
	commandsOnlyFlag := flag.Bool("commands-only", false, "Тільки перевірка команд (без збору даних)")
	flag.Parse()

	// Налаштування логування
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	// Логування у файл (для діагностики scheduled task)
	exePath, _ := getExePath()
	logPath := filepath.Join(filepath.Dir(exePath), "orange_agent.log")

	// Ротація логу: якщо файл > 5MB — перейменовуємо в .old
	rotateLogFile(logPath)

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

	// --- РЕЖИМ ТІЛЬКИ КОМАНДИ (легкий polling) ---
	if *commandsOnlyFlag {
		runCommandsOnly()
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

	// Перевіряємо оновлення першочергово — якщо є нова версія,
	// оновлюємось і перезапускаємось, щоб дані зібрала вже нова версія
	if config != nil {
		checkAndUpdate(config)
	}

	// Збираємо статичні дані
	log.Println("\n=== ЗБІР СТАТИЧНИХ ДАНИХ ===")
	static := getStaticInfo()
	log.Printf("Hostname: %s", static.Hostname)
	log.Printf("OS: %s %s", static.Platform, static.OSVersion)
	log.Printf("CPU: %s (%d cores)", static.CPUModel, static.CPUCores)
	log.Printf("RAM: %.2f GB", float64(static.TotalRAM)/(1024*1024*1024))
	log.Printf("Serial: %s", static.BIOS.SerialNumber)
	log.Printf("Certificates: %d", len(static.Certificates))

	// Збираємо динамічні дані
	log.Println("\n=== ЗБІР ДИНАМІЧНИХ ДАНИХ ===")
	dynamic := getDynamicInfo()
	log.Printf("CPU Usage: %.1f%%", dynamic.CPUUsage)
	log.Printf("RAM Usage: %.1f%%", dynamic.RAMUsage)
	log.Printf("Current User: %s", dynamic.CurrentUser)
	log.Printf("Uptime: %d seconds", dynamic.Uptime)
	log.Printf("Neighbors: %d", len(dynamic.Neighbors))

	// Збираємо дані SNMP якщо є конфігурація
	if config != nil {
		log.Println("\n=== ЗБІР ДАНИХ SNMP (MikroTik тощо) ===")
		agentID := generateAgentID(static)
		targets, err := GetSNMPTargets(config, agentID)
		if err != nil {
			log.Printf("⚠ Не вдалося отримати цілі SNMP: %v", err)
		} else if len(targets) > 0 {
			log.Printf("🔍 Знайдено %d цілей для SNMP сканування", len(targets))
			dynamic.SNMPReports = CollectSNMP(targets)
			log.Printf("✓ Зібрано %d SNMP звітів", len(dynamic.SNMPReports))
		} else {
			log.Println("ℹ Немає цілей для SNMP сканування")
		}
	}

	// Відправляємо на сервер якщо є конфігурація
	if config != nil {
		log.Println("\n=== ВІДПРАВКА НА СЕРВЕР ===")
		if err := sendToServer(config, static, dynamic); err != nil {
			log.Printf("⚠ Помилка відправки (дані збережено в чергу): %v", err)
			// Не виходимо з помилкою - дані в черзі
		} else {
			log.Println("✓ Дані успішно відправлено!")
		}

		// Генеруємо agentID для ідентифікації при синхронізації
		agentID := generateAgentID(static)

		// Синхронізуємо політики блокування ПЗ
		log.Println("\n=== ПОЛІТИКИ БЛОКУВАННЯ ПЗ ===")
		if err := syncBlockedSoftware(config, agentID); err != nil {
			log.Printf("⚠ Помилка синхронізації політик ПЗ: %v", err)
		}

		// Синхронізуємо блокування доменів
		log.Println("\n=== БЛОКУВАННЯ ДОМЕНІВ ===")
		if err := syncBlockedDomains(config, agentID); err != nil {
			log.Printf("⚠ Помилка синхронізації блокувань доменів: %v", err)
		}

		// Обробляємо віддалені команди (з lock для уникнення конфліктів)
		log.Println("\n=== ВІДДАЛЕНІ КОМАНДИ ===")
		if acquireLock("commands") {
			processCommands(config, agentID)
			releaseLock("commands")
		} else {
			log.Println("⚠ Команди обробляються іншим процесом, пропускаємо")
		}
	} else {
		// Локальний вивід JSON для дебагу
		printLocalData(static, dynamic)
	}
}

// checkAndUpdate перевіряє та виконує оновлення
func checkAndUpdate(config *Config) {
	log.Println("\n=== ПЕРЕВІРКА ОНОВЛЕНЬ ===")

	// Отримуємо agent_id для перевірки бета-прав на сервері
	static := getMinimalStaticInfo()
	agentID := generateAgentID(static)

	updateResp, err := checkForUpdate(config, agentID)
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

// generateAgentID генерує унікальний agent_id (має співпадати з логікою на сервері)
func generateAgentID(static StaticData) string {
	hostname := static.Hostname
	boardSerial := static.BoardSerial
	biosSerial := static.BIOS.SerialNumber

	// Комбінуємо дані для хешу
	uniqueString := fmt.Sprintf("%s:%s:%s", hostname, boardSerial, biosSerial)
	hash := md5.Sum([]byte(uniqueString))
	hashPart := hex.EncodeToString(hash[:])[:8]

	return fmt.Sprintf("%s-%s", hostname, hashPart)
}

// runCommandsOnly - легкий режим тільки для перевірки команд
func runCommandsOnly() {
	// Перевіряємо lock щоб не конфліктувати з повним запуском
	if !acquireLock("commands") {
		log.Println("⚠ Інший процес вже працює, пропускаємо")
		return
	}
	defer releaseLock("commands")

	config, err := loadConfig()
	if err != nil {
		log.Printf("⚠ Конфігурацію не знайдено: %v", err)
		return
	}

	// Отримуємо мінімальні дані для agent_id
	static := getMinimalStaticInfo()
	agentID := generateAgentID(static)

	// Обробляємо команди
	processCommands(config, agentID)
}

// acquireLock намагається отримати lock
func acquireLock(name string) bool {
	exePath, _ := getExePath()
	lockPath := filepath.Join(filepath.Dir(exePath), fmt.Sprintf(".%s.lock", name))

	// Перевіряємо чи існує lock файл
	if info, err := os.Stat(lockPath); err == nil {
		// Lock існує - перевіряємо чи не застарів (більше 5 хвилин)
		if time.Since(info.ModTime()) > 5*time.Minute {
			// Застарілий lock - видаляємо
			os.Remove(lockPath)
		} else {
			return false
		}
	}

	// Створюємо lock файл
	f, err := os.Create(lockPath)
	if err != nil {
		return false
	}
	f.Close()
	return true
}

// releaseLock звільняє lock
func releaseLock(name string) {
	exePath, _ := getExePath()
	lockPath := filepath.Join(filepath.Dir(exePath), fmt.Sprintf(".%s.lock", name))
	os.Remove(lockPath)
}

// rotateLogFile перевіряє розмір лог-файлу та виконує ротацію якщо > 5MB
func rotateLogFile(logPath string) {
	const maxLogSize = 5 * 1024 * 1024 // 5MB

	info, err := os.Stat(logPath)
	if err != nil {
		return
	}

	if info.Size() > maxLogSize {
		oldPath := logPath + ".old"
		os.Remove(oldPath)
		os.Rename(logPath, oldPath)
	}
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
