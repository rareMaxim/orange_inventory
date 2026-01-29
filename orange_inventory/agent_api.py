# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
API для приймання даних від агентів моніторингу.

Агент на Windows-машинах збирає системну інформацію та надсилає її
на цей endpoint для:
1. Створення/оновлення запису oiAgent
2. Автоматичне прив'язування до існуючого активу по serial_no (опціонально)
3. Збереження snapshot динамічних даних
"""

import hashlib
import json

import frappe
from frappe.utils import now_datetime


def _generate_agent_id(static: dict) -> str:
	"""
	Генерує унікальний agent_id на основі hostname та board_serial.

	Args:
	        static: словник зі статичними даними

	Returns:
	        str: agent_id у форматі "hostname-hash[:8]"
	"""
	hostname = static.get("hostname", "unknown")
	board_serial = static.get("board_serial", "")
	bios_serial = static.get("bios", {}).get("serial_number", "")

	# Комбінуємо дані для хешу
	unique_string = f"{hostname}:{board_serial}:{bios_serial}"
	hash_part = hashlib.md5(unique_string.encode()).hexdigest()[:8]

	return f"{hostname}-{hash_part}"


def _get_valid_serial(static: dict) -> str | None:
	"""
	Отримує валідний серійний номер зі статичних даних.

	Args:
	        static: словник зі статичними даними

	Returns:
	        str | None: серійний номер або None
	"""
	invalid_serials = ["Unknown", "To Be Filled By O.E.M.", "Default string", ""]

	# Пріоритет: BIOS serial > board serial
	serial_no = None
	if static.get("bios") and static["bios"].get("serial_number"):
		serial_no = static["bios"]["serial_number"]

	if not serial_no or serial_no in invalid_serials:
		serial_no = static.get("board_serial")

	if serial_no in invalid_serials:
		return None

	return serial_no


@frappe.whitelist()
def report_machine_data(static_data: str, dynamic_data: str | None = None):
	"""
	Приймає дані від агента моніторингу.

	Логіка роботи:
	1. Генерує agent_id на основі hostname + серійних номерів
	2. Створює або оновлює запис oiAgent
	3. Якщо agent не прив'язаний до активу - шукає актив по serial_no
	4. Зберігає snapshot динамічних даних

	Args:
	        static_data: JSON рядок зі статичними даними:
	                - hostname: ім'я комп'ютера
	                - os_platform: операційна система
	                - os_version: версія ОС
	                - cpu_model: модель процесора
	                - cpu_cores: кількість ядер
	                - total_ram_bytes: загальна RAM в байтах
	                - board_serial: серійний номер материнської плати
	                - bios: {serial_number, manufacturer, version}
	                - system: {manufacturer, model}
	                - gpu_models: список відеокарт
	                - physical_disks: список дисків
	                - network_adapters: список мережевих адаптерів

	        dynamic_data: JSON рядок з динамічними даними (опціонально):
	                - timestamp: час вимірювання
	                - uptime_seconds: час роботи системи
	                - current_user: поточний користувач
	                - ip_addresses: список IP адрес
	                - ram_usage_percent: використання RAM
	                - cpu_usage_percent: використання CPU
	                - disks: список станів дисків

	Returns:
	        dict: {
	                "status": "success",
	                "agent_name": "hostname-abc12345",
	                "agent_id": "DESKTOP-ABC-12345678",
	                "asset_name": "ASSET-00001" або None,
	                "created": True/False,
	                "message": "..."
	        }
	"""
	# Парсимо JSON дані
	try:
		static = json.loads(static_data)
	except json.JSONDecodeError:
		frappe.throw("Невалідний JSON у static_data", frappe.ValidationError)

	dynamic = None
	if dynamic_data:
		try:
			dynamic = json.loads(dynamic_data)
		except json.JSONDecodeError:
			frappe.log_error("Невалідний JSON у dynamic_data", "Agent API")
			dynamic = None

	# Генеруємо agent_id
	agent_id = _generate_agent_id(static)

	# Отримуємо серійний номер
	serial_no = _get_valid_serial(static)

	# --- ПОШУК/СТВОРЕННЯ АГЕНТА ---
	created = False
	agent_name = frappe.db.get_value("oiAgent", {"agent_id": agent_id}, "name")

	if agent_name:
		agent = frappe.get_doc("oiAgent", agent_name)
	else:
		# Створюємо нового агента
		agent = frappe.new_doc("oiAgent")
		agent.agent_id = agent_id
		agent.first_seen = now_datetime()
		created = True

	# --- ОНОВЛЮЄМО ДАНІ АГЕНТА ---
	agent.hostname = static.get("hostname")
	agent.status = "Активний"
	agent.last_seen = now_datetime()

	os_platform = static.get("os_platform", "")
	os_version = static.get("os_version", "")
	agent.os = f"{os_platform} {os_version}".strip()

	agent.cpu_model = static.get("cpu_model")
	agent.cpu_cores = static.get("cpu_cores")

	# Конвертуємо RAM з байтів в GB
	total_ram_bytes = static.get("total_ram_bytes", 0)
	if total_ram_bytes:
		agent.ram_total_gb = round(total_ram_bytes / (1024**3), 2)

	# Системна інформація
	system_info = static.get("system", {})
	agent.system_manufacturer = system_info.get("manufacturer")
	agent.system_model = system_info.get("model")
	agent.system_type = static.get("system_type")

	# Серійні номери
	bios_info = static.get("bios", {})
	agent.bios_serial = bios_info.get("serial_number")
	agent.board_serial = static.get("board_serial")

	# Повні дані
	agent.raw_data = json.dumps(static, ensure_ascii=False, indent=2)

	# --- АВТОМАТИЧНЕ ПРИВ'ЯЗУВАННЯ ДО АКТИВУ ---
	asset_name = None
	if not agent.asset and serial_no:
		# Шукаємо актив по serial_no
		asset_name = frappe.db.get_value("oiAsset", {"serial_no": serial_no}, "name")
		if asset_name:
			agent.asset = asset_name
			# Також оновлюємо зв'язок в oiAsset
			frappe.db.set_value("oiAsset", asset_name, "agent", agent.name if agent.name else agent_id)
	else:
		asset_name = agent.asset

	# Зберігаємо агента
	agent.save(ignore_permissions=True)

	# Якщо новий агент і ми прив'язали його до активу - оновлюємо актив
	if created and asset_name:
		frappe.db.set_value("oiAsset", asset_name, "agent", agent.name)

	# Зберігаємо snapshot динамічних даних
	if dynamic:
		_save_snapshot(agent.name, dynamic)

	frappe.db.commit()

	return {
		"status": "success",
		"agent_name": agent.name,
		"agent_id": agent_id,
		"asset_name": asset_name,
		"created": created,
		"message": "Новий агент створено" if created else "Агент оновлено",
	}


def _save_snapshot(agent_name: str, dynamic: dict):
	"""
	Зберігає snapshot динамічних даних.

	Args:
	        agent_name: ID агента
	        dynamic: словник з динамічними даними
	"""
	try:
		snapshot = frappe.get_doc(
			{
				"doctype": "oiAgentSnapshot",
				"agent": agent_name,
				"timestamp": now_datetime(),
				"cpu_usage": dynamic.get("cpu_usage_percent"),
				"ram_usage": dynamic.get("ram_usage_percent"),
				"current_user": dynamic.get("current_user"),
				"ip_addresses": json.dumps(dynamic.get("ip_addresses", []), ensure_ascii=False),
				"disk_usage": json.dumps(dynamic.get("disks", []), ensure_ascii=False),
				"uptime_seconds": dynamic.get("uptime_seconds"),
			}
		)
		snapshot.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error("Не вдалося зберегти oiAgentSnapshot", "Agent API")


@frappe.whitelist()
def get_agent_by_id(agent_id: str):
	"""
	Перевіряє чи існує агент з вказаним agent_id.

	Args:
	        agent_id: ідентифікатор агента

	Returns:
	        dict: {
	                "exists": True/False,
	                "agent_name": "hostname-abc12345" або None,
	                "asset_name": "ASSET-00001" або None
	        }
	"""
	result = frappe.db.get_value("oiAgent", {"agent_id": agent_id}, ["name", "asset"], as_dict=True)
	if result:
		return {"exists": True, "agent_name": result.name, "asset_name": result.asset}
	return {"exists": False, "agent_name": None, "asset_name": None}


@frappe.whitelist()
def get_asset_by_serial(serial_no: str):
	"""
	Перевіряє чи існує актив з вказаним серійним номером.

	Args:
	        serial_no: серійний номер для пошуку

	Returns:
	        dict: {
	                "exists": True/False,
	                "asset_name": "ASSET-00001" або None
	        }
	"""
	asset_name = frappe.db.get_value("oiAsset", {"serial_no": serial_no}, "name")
	return {"exists": bool(asset_name), "asset_name": asset_name}
