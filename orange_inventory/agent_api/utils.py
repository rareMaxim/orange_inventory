# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import gzip
import hashlib
import json

import frappe
from frappe.utils import now_datetime


def _decompress_gzip(data: bytes) -> bytes:
	"""Розпаковує gzip дані."""
	try:
		return gzip.decompress(data)
	except Exception:
		return data


def _log(message: str):
	"""Логує повідомлення Agent API у файл."""
	with open(frappe.get_site_path("logs", "agent_api.log"), "a") as f:
		f.write(f"{now_datetime()} {message}\n")


def _get_request_data() -> dict:
	"""
	Отримує дані запиту з підтримкою gzip.
	Повертає словник з static_data та dynamic_data.
	"""
	request = getattr(frappe, "request", None)

	# Перевіряємо чи є Content-Encoding: gzip
	content_encoding = request.headers.get("Content-Encoding", "").lower() if request else ""

	if content_encoding == "gzip" and request:
		# Розпаковуємо gzip
		raw_data = request.get_data()
		decompressed = _decompress_gzip(raw_data)
		try:
			data = json.loads(decompressed)
			return {"static_data": data.get("static_data"), "dynamic_data": data.get("dynamic_data")}
		except json.JSONDecodeError:
			frappe.throw("Невалідний JSON після gzip декомпресії", frappe.ValidationError)

	# Звичайний запит - використовуємо form_dict
	return {
		"static_data": frappe.form_dict.get("static_data"),
		"dynamic_data": frappe.form_dict.get("dynamic_data"),
	}


def _generate_agent_id(static: dict) -> str:
	"""
	Генерує унікальний agent_id на основі hostname та board_serial.
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
