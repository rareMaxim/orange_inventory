# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
API для оновлення агентів.

Endpoints:
- check_update: перевіряє чи є нова версія
- get_download_url: отримує URL для завантаження
"""

import frappe


def _log(message: str):
	"""Логує повідомлення в agent_update.log."""
	frappe.logger("agent_update").info(message)


@frappe.whitelist()
def check_update(current_version: str):
	"""
	Перевіряє чи є оновлення для агента.

	Args:
	        current_version: поточна версія агента (наприклад "1.1")

	Returns:
	        dict: {
	                "update_available": True/False,
	                "latest_version": "1.2",
	                "is_mandatory": True/False,
	                "download_url": "/api/method/...",
	                "file_size": 12345678,
	                "checksum": "sha256...",
	                "release_notes": "..."
	        }
	"""
	# Логуємо запит
	user = frappe.session.user
	ip = frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "unknown"
	_log(f"check_update: user={user}, ip={ip}, current_version={current_version}")

	# Отримуємо актуальну версію
	latest = frappe.db.get_value(
		"oiAgentRelease",
		{"is_latest": 1},
		[
			"name",
			"version",
			"is_mandatory",
			"agent_file",
			"file_checksum",
			"file_size",
			"release_notes",
			"min_version_to_update",
		],
		as_dict=True,
	)

	if not latest:
		_log("check_update: no releases available")
		return {"update_available": False, "message": "Немає доступних версій"}

	# Порівнюємо версії
	if not _is_newer_version(latest.version, current_version):
		_log(f"check_update: version {current_version} is up to date")
		return {
			"update_available": False,
			"latest_version": latest.version,
			"message": "Ви використовуєте актуальну версію",
		}

	# Перевіряємо мінімальну версію для оновлення
	if latest.min_version_to_update:
		if _is_newer_version(latest.min_version_to_update, current_version):
			_log(f"check_update: version {current_version} too old for auto-update")
			return {
				"update_available": False,
				"latest_version": latest.version,
				"message": f"Ваша версія {current_version} занадто стара для автооновлення. "
				f"Мінімальна версія: {latest.min_version_to_update}. Оновіть вручну.",
			}

	# Формуємо URL для завантаження
	download_url = f"/api/method/orange_inventory.update_api.download_agent?version={latest.version}"

	_log(f"check_update: update available {current_version} -> {latest.version}")

	return {
		"update_available": True,
		"latest_version": latest.version,
		"is_mandatory": bool(latest.is_mandatory),
		"download_url": download_url,
		"file_size": latest.file_size or 0,
		"checksum": latest.file_checksum or "",
		"release_notes": latest.release_notes or "",
	}


@frappe.whitelist()
def download_agent(version: str = None):
	"""
	Завантажує файл агента.

	Args:
	        version: версія для завантаження (якщо None - остання)

	Returns:
	        Файл агента для завантаження
	"""
	user = frappe.session.user
	ip = frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "unknown"
	_log(f"download_agent: user={user}, ip={ip}, version={version}")

	try:
		if version:
			release = frappe.get_doc("oiAgentRelease", version)
		else:
			# Отримуємо останню версію
			latest_name = frappe.db.get_value("oiAgentRelease", {"is_latest": 1}, "name")
			if not latest_name:
				_log("download_agent: no releases available")
				frappe.throw("Немає доступних версій агента")
			release = frappe.get_doc("oiAgentRelease", latest_name)

		if not release.agent_file:
			_log(f"download_agent: no file for version {release.version}")
			frappe.throw("Файл агента не знайдено")

		# Отримуємо файл
		file_doc = frappe.get_doc("File", {"file_url": release.agent_file})
		file_path = file_doc.get_full_path()

		_log(f"download_agent: sending file {file_path} for version {release.version}")

		# Відправляємо файл
		with open(file_path, "rb") as f:
			content = f.read()

		_log(f"download_agent: success, size={len(content)} bytes")

		frappe.local.response.filename = f"orange_agent_{release.version}.exe"
		frappe.local.response.filecontent = content
		frappe.local.response.type = "download"

	except Exception as e:
		_log(f"download_agent: ERROR - {e!s}")
		raise


def _is_newer_version(v1: str, v2: str) -> bool:
	"""
	Перевіряє чи v1 > v2.

	Args:
	        v1: версія для порівняння
	        v2: поточна версія

	Returns:
	        True якщо v1 > v2
	"""

	def parse_version(v):
		try:
			parts = v.replace("-", ".").split(".")
			return [int(p) for p in parts if p.isdigit()]
		except Exception:
			return [0]

	parts1 = parse_version(v1)
	parts2 = parse_version(v2)

	# Вирівнюємо довжину
	max_len = max(len(parts1), len(parts2))
	parts1.extend([0] * (max_len - len(parts1)))
	parts2.extend([0] * (max_len - len(parts2)))

	for p1, p2 in zip(parts1, parts2, strict=False):
		if p1 > p2:
			return True
		if p1 < p2:
			return False

	return False  # Версії рівні


@frappe.whitelist()
def get_latest_version():
	"""
	Повертає інформацію про останню версію.

	Returns:
	        dict: {"version": "1.2", "release_date": "2026-01-29", ...}
	"""
	latest = frappe.db.get_value(
		"oiAgentRelease",
		{"is_latest": 1},
		["version", "release_date", "is_mandatory", "release_notes", "file_size"],
		as_dict=True,
	)

	if not latest:
		return {"version": None, "message": "Немає доступних версій"}

	return latest
