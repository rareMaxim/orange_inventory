# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import now_datetime

from orange_inventory.agent_api.certificates import _save_certificates
from orange_inventory.agent_api.networking import _process_neighbors, _sync_network_ports

# We need to import these to use them in report_machine_data
from orange_inventory.agent_api.snmp import _process_snmp_reports
from orange_inventory.agent_api.software import _save_software
from orange_inventory.agent_api.utils import _generate_agent_id, _get_request_data, _get_valid_serial


@frappe.whitelist()
def report_machine_data(static_data: str | None = None, dynamic_data: str | None = None):
	"""
	Приймає дані від агента моніторингу.
	"""
	# Отримуємо дані з підтримкою gzip
	request_data = _get_request_data()
	static_data = request_data.get("static_data") or static_data
	dynamic_data = request_data.get("dynamic_data") or dynamic_data

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
	agent.last_ip = frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "unknown"
	agent.agent_version = static.get("agent_version")

	os_platform = static.get("os_platform", "")
	os_version = static.get("os_version", "")
	agent.os = f"{os_platform} {os_version}".strip()
	agent.os_edition = static.get("os_edition", "")
	agent.cpu_model = static.get("cpu_model")
	agent.cpu_cores = static.get("cpu_cores")

	total_ram_bytes = static.get("total_ram_bytes", 0)
	if total_ram_bytes:
		agent.ram_total_gb = round(total_ram_bytes / (1024**3), 2)

	system_info = static.get("system", {})
	agent.system_manufacturer = system_info.get("manufacturer")
	agent.system_model = system_info.get("model")
	agent.system_type = static.get("system_type")

	bios_info = static.get("bios", {})
	agent.bios_serial = bios_info.get("serial_number")
	agent.board_serial = static.get("board_serial")
	agent.raw_data = json.dumps(static, ensure_ascii=False, indent=2)

	# --- АВТОМАТИЧНЕ ПРИВ'ЯЗУВАННЯ ДО АКТИВУ ---
	asset_name = None
	if not agent.asset and serial_no:
		asset_name = frappe.db.get_value("oiAsset", {"serial_no": serial_no}, "name")
		if asset_name:
			agent.asset = asset_name
			frappe.db.set_value("oiAsset", asset_name, "agent", agent.name if agent.name else agent_id)
	else:
		asset_name = agent.asset

	agent.save(ignore_permissions=True)

	if created and asset_name:
		frappe.db.set_value("oiAsset", asset_name, "agent", agent.name)

	if dynamic:
		_save_snapshot(agent.name, dynamic)
		snmp_reports = dynamic.get("snmp_reports", [])
		if snmp_reports:
			_process_snmp_reports(agent.name, snmp_reports)

	software_list = static.get("installed_software", [])
	if software_list:
		_save_software(agent.name, software_list)

	adapters = static.get("network_adapters", [])
	if asset_name and adapters:
		macs = []
		for adapter in adapters:
			mac = adapter.get("mac_address")
			if mac and mac != "00:00:00:00:00:00":
				macs.append(mac.lower())

		if macs:
			current_macs = frappe.db.get_value("oiAsset", asset_name, "mac_addresses") or ""
			new_macs_str = ", ".join(sorted(list(set(macs))))
			if current_macs != new_macs_str:
				frappe.db.set_value("oiAsset", asset_name, "mac_addresses", new_macs_str)

		_sync_network_ports(asset_name, adapters)

	certificates = static.get("certificates", [])
	if certificates:
		_save_certificates(agent.name, certificates)

	if dynamic and dynamic.get("neighbors"):
		_process_neighbors(agent.name, asset_name, dynamic.get("neighbors"))

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
	"""Зберігає snapshot динамічних даних."""
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
				"services_status": json.dumps(dynamic.get("services", []), ensure_ascii=False),
			}
		)
		snapshot.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error("Не вдалося зберегти oiAgentSnapshot", "Agent API")


@frappe.whitelist()
def get_agent_by_id(agent_id: str):
	"""Перевіряє чи існує агент з вказаним agent_id."""
	result = frappe.db.get_value("oiAgent", {"agent_id": agent_id}, ["name", "asset"], as_dict=True)
	if result:
		return {"exists": True, "agent_name": result.name, "asset_name": result.asset}
	return {"exists": False, "agent_name": None, "asset_name": None}


@frappe.whitelist()
def get_asset_by_serial(serial_no: str):
	"""Перевіряє чи існує актив з вказаним серійним номером."""
	asset_name = frappe.db.get_value("oiAsset", {"serial_no": serial_no}, "name")
	return {"exists": bool(asset_name), "asset_name": asset_name}
