# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Модуль синхронізації з порталом hromada.gov.ua.

Забезпечує:
- Отримання параметрів індексу цифрової трансформації з API
- Автоматичний mapping по коду показника
- Відправка даних на портал
"""

import json

import frappe
import requests
from frappe.utils import now_datetime
from frappe.utils.data import cint, flt


def _get_settings():
	"""Отримати налаштування інтеграції."""
	return frappe.get_single("oiHromadaSettings")


def _get_api_headers():
	"""Отримати заголовки для API запитів."""
	settings = _get_settings()
	token = settings.get_password("api_token")
	if not token:
		frappe.throw("API Token не налаштовано. Перейдіть до oiHromadaSettings.")
	return {
		"accept": "application/json, text/plain, */*",
		"authorization": f"Bearer {token}",
		"content-type": "application/json",
		"origin": "https://hromada.gov.ua",
		"referer": "https://hromada.gov.ua/",
	}


def _normalize_code(code: str | None) -> str | None:
	"""
	Нормалізує код параметра для порівняння.
	Прибирає пробіли, заміняє українські літери на латинські.
	"""
	if not code:
		return None
	# Очищаємо від пробілів
	cleaned = str(code).strip().replace(" ", "")
	# Нормалізуємо літери (українські -> латинські)
	cleaned = cleaned.replace("А", "A").replace("В", "B").replace("С", "C").replace("Е", "E")
	return cleaned if cleaned else None


def _log_sync(message: str, level: str = "info"):
	"""Додати запис в лог синхронізації."""
	settings = _get_settings()
	log_entry = {
		"timestamp": str(now_datetime()),
		"level": level,
		"message": message,
	}

	try:
		current_log = json.loads(settings.sync_log or "[]")
	except (json.JSONDecodeError, TypeError):
		current_log = []

	current_log.insert(0, log_entry)
	# Обмежуємо лог до 100 записів
	current_log = current_log[:100]

	frappe.db.set_value(
		"oiHromadaSettings",
		"oiHromadaSettings",
		"sync_log",
		json.dumps(current_log, ensure_ascii=False, indent=2),
	)


@frappe.whitelist()
def fetch_portal_parameters():
	"""
	Отримати параметри індексу з порталу hromada.gov.ua.

	Також перевіряє зміни статусів enabled (в одному запиті):
	- Якщо показник є локально з mapping, але відсутній на порталі -> пропонує вимкнути
	- Якщо показник локально enabled = false, але є на порталі -> пропонує увімкнути

	Returns:
	        dict: {
	                "status": "success" | "error",
	                "total": int,
	                "mapped": int,
	                "to_disable": list,
	                "to_enable": list,
	                "no_status_changes": bool,
	                "error": str (якщо є помилка)
	        }
	"""
	if not frappe.has_permission("oiHromadaSettings", "write"):
		frappe.throw("Недостатньо прав для синхронізації", frappe.PermissionError)

	settings = _get_settings()
	headers = _get_api_headers()
	base_url = settings.api_base_url or "https://backend.hromada.gov.ua/api"

	try:
		# Отримуємо інформацію про користувача для перевірки токена
		user_response = requests.get(
			f"{base_url}/auth/cabinet/user",
			headers=headers,
			timeout=30,
		)

		if user_response.status_code != 200:
			_log_sync(f"Помилка авторизації: {user_response.status_code}", "error")
			return {"status": "error", "error": f"Помилка авторизації: {user_response.status_code}"}

		user_data = user_response.json()
		community_id = user_data.get("community", {}).get("id")

		if community_id:
			frappe.db.set_value("oiHromadaSettings", "oiHromadaSettings", "community_id", community_id)

		# Отримуємо параметри індексу
		params_response = requests.get(
			f"{base_url}/front/index-group/parameters/location",
			params={"loadCommunity": "true"},
			headers=headers,
			timeout=120,
		)

		if params_response.status_code != 200:
			_log_sync(f"Помилка отримання параметрів: {params_response.status_code}", "error")
			return {
				"status": "error",
				"error": f"Помилка отримання параметрів: {params_response.status_code}",
			}

		data = params_response.json()
		groups = data.get("data", [])

		# Збираємо всі параметри, їх ID та коди
		all_parameters = []
		portal_param_ids = set()
		portal_param_codes = set()

		for group in groups:
			for subgroup in group.get("subgroups", []):
				for indicator in subgroup.get("indicators", []):
					for param in indicator.get("parameters", []):
						param_id = cint(param.get("id"))
						param_code = _normalize_code(param.get("code"))
						if param_id:
							portal_param_ids.add(param_id)
						if param_code:
							portal_param_codes.add(param_code)

						all_parameters.append(
							{
								"id": param_id,
								"code": _normalize_code(param.get("code")),
								"description": param.get("description"),
								"value": param.get("value"),
								"value_type": param.get("value_type"),
								"data_source": param.get("data_source"),
								"formula_type": param.get("formula_type"),
								"group_name": group.get("name"),
								"subgroup_name": subgroup.get("name"),
								"indicator_code": indicator.get("code"),
								"indicator_description": indicator.get("description"),
							}
						)

		total_params = len(all_parameters)

		# Оновлюємо статистику
		frappe.db.set_value(
			"oiHromadaSettings",
			"oiHromadaSettings",
			{
				"total_parameters": total_params,
				"last_sync_date": now_datetime(),
			},
		)

		# Автоматичний mapping
		mapped_count = _perform_auto_mapping(all_parameters)

		# Перевіряємо зміни статусів enabled (використовуємо вже отримані дані)
		to_disable, to_enable = _check_enabled_status_from_portal_data(portal_param_ids, portal_param_codes)

		_log_sync(f"Отримано {total_params} параметрів, замаплено {mapped_count}")

		frappe.db.commit()

		return {
			"status": "success",
			"total": total_params,
			"mapped": mapped_count,
			"to_disable": to_disable,
			"to_enable": to_enable,
			"no_status_changes": len(to_disable) == 0 and len(to_enable) == 0,
		}

	except requests.exceptions.RequestException as e:
		_log_sync(f"Помилка запиту: {e!s}", "error")
		return {"status": "error", "error": f"Помилка запиту: {e!s}"}
	except Exception as e:
		_log_sync(f"Невідома помилка: {e!s}", "error")
		return {"status": "error", "error": f"Невідома помилка: {e!s}"}


def _check_enabled_status_from_portal_data(
	portal_param_ids: set, portal_param_codes: set
) -> tuple[list, list]:
	"""
	Перевірити зміни статусів enabled на основі даних з порталу.

	Перевіряє:
	1. Показники з mapping: порівнює по ID
	2. Показники без mapping: порівнює по коду (нормалізованому)

	Args:
	        portal_param_ids: Множина ID параметрів, присутніх на порталі
	        portal_param_codes: Множина нормалізованих кодів параметрів з порталу

	Returns:
	        tuple: (to_disable, to_enable) - списки показників для зміни статусу
	"""
	# Отримуємо всі локальні показники (не групи)
	local_surveys = frappe.get_all(
		"oiHromadaSurvey",
		filters={
			"type": ["!=", "Група"],
		},
		fields=[
			"name",
			"id",
			"title",
			"enabled",
			"hromada_parameter_id",
			"hromada_parameter_code",
		],
	)

	to_disable = []
	to_enable = []

	for survey in local_surveys:
		param_id = cint(survey.get("hromada_parameter_id"))
		is_enabled = cint(survey.get("enabled"))
		local_code = _normalize_code(survey.get("id"))

		if param_id:
			# Є mapping - перевіряємо по ID
			is_on_portal = param_id in portal_param_ids

			if is_enabled and not is_on_portal:
				to_disable.append(
					{
						"name": survey.get("name"),
						"id": survey.get("id"),
						"title": survey.get("title"),
						"parameter_id": param_id,
						"parameter_code": survey.get("hromada_parameter_code"),
						"reason": "Відсутній на порталі (по ID)",
					}
				)
			elif not is_enabled and is_on_portal:
				to_enable.append(
					{
						"name": survey.get("name"),
						"id": survey.get("id"),
						"title": survey.get("title"),
						"parameter_id": param_id,
						"parameter_code": survey.get("hromada_parameter_code"),
						"reason": "Присутній на порталі",
					}
				)
		else:
			# Немає mapping - перевіряємо по коду
			is_on_portal = local_code in portal_param_codes if local_code else False

			if is_enabled and not is_on_portal and local_code:
				to_disable.append(
					{
						"name": survey.get("name"),
						"id": survey.get("id"),
						"title": survey.get("title"),
						"parameter_id": None,
						"parameter_code": survey.get("id"),
						"reason": "Відсутній на порталі (немає mapping)",
					}
				)
			elif not is_enabled and is_on_portal:
				to_enable.append(
					{
						"name": survey.get("name"),
						"id": survey.get("id"),
						"title": survey.get("title"),
						"parameter_id": None,
						"parameter_code": survey.get("id"),
						"reason": "Присутній на порталі (потребує mapping)",
					}
				)

	return to_disable, to_enable


def _perform_auto_mapping(parameters: list[dict]) -> int:
	"""
	Виконати автоматичний mapping параметрів по коду.

	Args:
	        parameters: Список параметрів з порталу

	Returns:
	        Кількість замаплених параметрів
	"""
	# Отримуємо всі показники з системи
	surveys = frappe.get_all(
		"oiHromadaSurvey",
		filters={"type": ["!=", "Група"]},
		fields=["name", "id", "title"],
	)

	# Створюємо словник по нормалізованому коду
	survey_by_code = {}
	for s in surveys:
		norm_code = _normalize_code(s.get("id"))
		if norm_code:
			survey_by_code[norm_code] = s

	mapped_count = 0
	unmapped_count = 0

	for param in parameters:
		param_code = param.get("code")
		if not param_code:
			continue

		norm_code = _normalize_code(param_code)
		if norm_code and norm_code in survey_by_code:
			survey = survey_by_code[norm_code]
			# Оновлюємо mapping
			frappe.db.set_value(
				"oiHromadaSurvey",
				survey["name"],
				{
					"hromada_parameter_id": param.get("id"),
					"hromada_parameter_code": param.get("code"),
					"hromada_data_source": param.get("data_source"),
				},
				update_modified=False,
			)
			mapped_count += 1
		else:
			unmapped_count += 1

	# Оновлюємо статистику
	frappe.db.set_value(
		"oiHromadaSettings",
		"oiHromadaSettings",
		{
			"mapped_parameters": mapped_count,
			"unmapped_parameters": unmapped_count,
		},
	)

	return mapped_count


@frappe.whitelist()
def auto_map_parameters():
	"""
	Виконати автоматичний mapping по коду (публічний endpoint).

	Returns:
	        dict: Статистика mapping
	"""
	if not frappe.has_permission("oiHromadaSettings", "write"):
		frappe.throw("Недостатньо прав для mapping", frappe.PermissionError)

	# Спочатку отримуємо актуальні параметри
	result = fetch_portal_parameters()
	if result.get("status") != "success":
		return result

	parameters = result.get("parameters", [])
	mapped = _perform_auto_mapping(parameters)

	frappe.db.commit()

	return {
		"status": "success",
		"created": 0,
		"updated": mapped,
		"unchanged": len(parameters) - mapped,
	}


@frappe.whitelist()
def sync_to_portal(dry_run: int = 0):
	"""
	Відправити дані на портал hromada.gov.ua.

	Відправляє тільки параметри з data_source='community'.

	Args:
	        dry_run: Якщо 1, тільки перевіряє без відправки

	Returns:
	        dict: {
	                "status": "success" | "partial" | "error",
	                "updated": int,
	                "skipped": int,
	                "errors": list
	        }
	"""
	if not frappe.has_permission("oiHromadaSettings", "write"):
		frappe.throw("Недостатньо прав для синхронізації", frappe.PermissionError)

	dry_run = bool(cint(dry_run))
	settings = _get_settings()
	headers = _get_api_headers()
	base_url = settings.api_base_url or "https://backend.hromada.gov.ua/api"

	# Отримуємо всі показники з mapping і data_source='community'
	surveys = frappe.get_all(
		"oiHromadaSurvey",
		filters={
			"type": ["!=", "Група"],
			"hromada_parameter_id": ["is", "set"],
			"hromada_data_source": "community",
		},
		fields=[
			"name",
			"id",
			"title",
			"type",
			"int_data",
			"bool_data",
			"hromada_parameter_id",
			"hromada_parameter_code",
		],
	)

	if not surveys:
		_log_sync("Немає показників для синхронізації (data_source=community)")
		return {
			"status": "success",
			"updated": 0,
			"skipped": 0,
			"errors": [],
			"message": "Немає показників для синхронізації",
		}

	# Формуємо дані для відправки
	parameters_to_send = []
	for survey in surveys:
		param_id = survey.get("hromada_parameter_id")
		if not param_id:
			continue

		# Визначаємо значення
		if survey.get("type") == "Кількісні дані":
			value = cint(survey.get("int_data") or 0)
		elif survey.get("type") == "Якісні дані":
			value = 1 if cint(survey.get("bool_data")) else 0
		else:
			continue

		parameters_to_send.append(
			{
				"id": param_id,
				"value": value,
				"survey_name": survey.get("name"),
				"survey_title": survey.get("title"),
			}
		)

	if not parameters_to_send:
		return {
			"status": "success",
			"updated": 0,
			"skipped": len(surveys),
			"errors": [],
		}

	if dry_run:
		_log_sync(f"[DRY RUN] Підготовлено {len(parameters_to_send)} параметрів для відправки")
		return {
			"status": "success",
			"dry_run": True,
			"updated": 0,
			"prepared": len(parameters_to_send),
			"parameters": parameters_to_send,
		}

	# Відправляємо дані
	try:
		payload = {"parameters": [{"id": p["id"], "value": p["value"]} for p in parameters_to_send]}

		response = requests.patch(
			f"{base_url}/front/index-community",
			headers=headers,
			json=payload,
			timeout=60,
		)

		if response.status_code in (200, 201, 204):
			# Оновлюємо дату синхронізації для кожного показника
			for param in parameters_to_send:
				frappe.db.set_value(
					"oiHromadaSurvey",
					param["survey_name"],
					"hromada_last_sync",
					now_datetime(),
					update_modified=False,
				)

			frappe.db.set_value(
				"oiHromadaSettings",
				"oiHromadaSettings",
				"last_sync_date",
				now_datetime(),
			)

			_log_sync(f"Успішно відправлено {len(parameters_to_send)} параметрів на портал")
			frappe.db.commit()

			return {
				"status": "success",
				"updated": len(parameters_to_send),
				"skipped": len(surveys) - len(parameters_to_send),
				"errors": [],
			}
		else:
			error_msg = f"Помилка відправки: {response.status_code} - {response.text}"
			_log_sync(error_msg, "error")
			return {
				"status": "error",
				"error": error_msg,
				"updated": 0,
				"skipped": len(surveys),
				"errors": [error_msg],
			}

	except requests.exceptions.RequestException as e:
		error_msg = f"Помилка запиту: {e!s}"
		_log_sync(error_msg, "error")
		return {
			"status": "error",
			"error": error_msg,
			"updated": 0,
			"skipped": len(surveys),
			"errors": [error_msg],
		}


@frappe.whitelist()
def get_sync_comparison():
	"""
	Отримати порівняння локальних значень з портальними.

	Завантажує поточні значення з порталу та порівнює з локальними.

	Returns:
	        dict: {
	                "status": "success" | "error",
	                "total": int,
	                "changed": int,
	                "unchanged": int,
	                "comparison": list - список параметрів з порівнянням
	        }
	"""
	if not frappe.has_permission("oiHromadaSettings", "read"):
		frappe.throw("Недостатньо прав для перегляду", frappe.PermissionError)

	settings = _get_settings()
	headers = _get_api_headers()
	base_url = settings.api_base_url or "https://backend.hromada.gov.ua/api"

	# Отримуємо показники з mapping і data_source='community'
	surveys = frappe.get_all(
		"oiHromadaSurvey",
		filters={
			"type": ["!=", "Група"],
			"hromada_parameter_id": ["is", "set"],
			"hromada_data_source": "community",
		},
		fields=[
			"name",
			"id",
			"title",
			"type",
			"int_data",
			"bool_data",
			"hromada_parameter_id",
			"hromada_parameter_code",
			"hromada_last_sync",
		],
	)

	if not surveys:
		return {
			"status": "success",
			"total": 0,
			"changed": 0,
			"unchanged": 0,
			"comparison": [],
			"message": "Немає показників для синхронізації",
		}

	# Отримуємо поточні значення з порталу
	try:
		params_response = requests.get(
			f"{base_url}/front/index-group/parameters/location",
			params={"loadCommunity": "true"},
			headers=headers,
			timeout=60,
		)

		if params_response.status_code != 200:
			return {
				"status": "error",
				"error": f"Помилка отримання даних з порталу: {params_response.status_code}",
			}

		data = params_response.json()
		groups = data.get("data", [])

		# Збираємо значення з порталу по ID параметра
		portal_values = {}
		for group in groups:
			for subgroup in group.get("subgroups", []):
				for indicator in subgroup.get("indicators", []):
					for param in indicator.get("parameters", []):
						param_id = param.get("id")
						if param_id:
							portal_values[param_id] = {
								"value": param.get("value"),
								"value_type": param.get("value_type"),
								"code": param.get("code"),
								"description": param.get("description"),
							}

	except requests.exceptions.RequestException as e:
		return {"status": "error", "error": f"Помилка запиту: {e!s}"}

	# Порівнюємо значення
	comparison = []
	changed_count = 0
	unchanged_count = 0

	for survey in surveys:
		param_id = survey.get("hromada_parameter_id")
		if not param_id:
			continue

		# Локальне значення
		if survey.get("type") == "Кількісні дані":
			local_value = cint(survey.get("int_data") or 0)
			local_display = str(local_value)
		elif survey.get("type") == "Якісні дані":
			local_value = 1 if cint(survey.get("bool_data")) else 0
			local_display = "Так" if local_value else "Ні"
		else:
			continue

		# Значення з порталу
		portal_data = portal_values.get(param_id, {})
		portal_raw = portal_data.get("value")

		# Конвертуємо портальне значення для порівняння
		if survey.get("type") == "Кількісні дані":
			try:
				portal_value = int(float(portal_raw)) if portal_raw is not None else 0
			except (ValueError, TypeError):
				portal_value = 0
			portal_display = str(portal_value)
		else:  # Якісні дані
			portal_value = cint(portal_raw) if portal_raw is not None else 0
			portal_display = "Так" if portal_value else "Ні"

		# Визначаємо чи є зміна
		is_changed = local_value != portal_value

		if is_changed:
			changed_count += 1
		else:
			unchanged_count += 1

		comparison.append(
			{
				"survey_name": survey.get("name"),
				"survey_id": survey.get("id"),
				"title": survey.get("title"),
				"type": survey.get("type"),
				"parameter_id": param_id,
				"parameter_code": survey.get("hromada_parameter_code"),
				"local_value": local_value,
				"local_display": local_display,
				"portal_value": portal_value,
				"portal_display": portal_display,
				"is_changed": is_changed,
				"last_sync": str(survey.get("hromada_last_sync"))
				if survey.get("hromada_last_sync")
				else None,
			}
		)

	# Сортуємо: спочатку змінені
	comparison.sort(key=lambda x: (not x["is_changed"], x["parameter_code"] or ""))

	return {
		"status": "success",
		"total": len(comparison),
		"changed": changed_count,
		"unchanged": unchanged_count,
		"comparison": comparison,
	}


@frappe.whitelist()
def sync_selected_to_portal(parameter_ids: str | list | None = None):
	"""
	Відправити обрані параметри на портал hromada.gov.ua.

	Args:
	        parameter_ids: JSON список ID параметрів для синхронізації.
	                                   Якщо не вказано - синхронізує всі параметри з data_source='community'.

	Returns:
	        dict: {
	                "status": "success" | "partial" | "error",
	                "updated": int,
	                "errors": list
	        }
	"""
	if not frappe.has_permission("oiHromadaSettings", "write"):
		frappe.throw("Недостатньо прав для синхронізації", frappe.PermissionError)

	# Парсимо список ID
	if isinstance(parameter_ids, str):
		try:
			parameter_ids = json.loads(parameter_ids)
		except json.JSONDecodeError:
			parameter_ids = None

	settings = _get_settings()
	headers = _get_api_headers()
	base_url = settings.api_base_url or "https://backend.hromada.gov.ua/api"

	# Базові фільтри
	filters = {
		"type": ["!=", "Група"],
		"hromada_parameter_id": ["is", "set"],
		"hromada_data_source": "community",
	}

	# Якщо вказано конкретні ID - фільтруємо по них
	if parameter_ids:
		filters["hromada_parameter_id"] = ["in", parameter_ids]

	surveys = frappe.get_all(
		"oiHromadaSurvey",
		filters=filters,
		fields=[
			"name",
			"id",
			"title",
			"type",
			"int_data",
			"bool_data",
			"hromada_parameter_id",
			"hromada_parameter_code",
		],
	)

	if not surveys:
		return {
			"status": "success",
			"updated": 0,
			"message": "Немає параметрів для синхронізації",
		}

	# Формуємо дані для відправки
	parameters_to_send = []
	for survey in surveys:
		param_id = survey.get("hromada_parameter_id")
		if not param_id:
			continue

		if survey.get("type") == "Кількісні дані":
			value = cint(survey.get("int_data") or 0)
		elif survey.get("type") == "Якісні дані":
			value = 1 if cint(survey.get("bool_data")) else 0
		else:
			continue

		parameters_to_send.append(
			{
				"id": param_id,
				"value": value,
				"survey_name": survey.get("name"),
				"survey_title": survey.get("title"),
			}
		)

	if not parameters_to_send:
		return {"status": "success", "updated": 0}

	# Відправляємо дані
	try:
		payload = {"parameters": [{"id": p["id"], "value": p["value"]} for p in parameters_to_send]}

		response = requests.patch(
			f"{base_url}/front/index-community",
			headers=headers,
			json=payload,
			timeout=60,
		)

		if response.status_code in (200, 201, 204):
			# Оновлюємо дату синхронізації
			for param in parameters_to_send:
				frappe.db.set_value(
					"oiHromadaSurvey",
					param["survey_name"],
					"hromada_last_sync",
					now_datetime(),
					update_modified=False,
				)

			frappe.db.set_value(
				"oiHromadaSettings",
				"oiHromadaSettings",
				"last_sync_date",
				now_datetime(),
			)

			_log_sync(f"Успішно відправлено {len(parameters_to_send)} параметрів на портал")
			frappe.db.commit()

			return {
				"status": "success",
				"updated": len(parameters_to_send),
			}
		else:
			error_msg = f"Помилка відправки: {response.status_code} - {response.text}"
			_log_sync(error_msg, "error")
			return {
				"status": "error",
				"error": error_msg,
				"updated": 0,
			}

	except requests.exceptions.RequestException as e:
		error_msg = f"Помилка запиту: {e!s}"
		_log_sync(error_msg, "error")
		return {"status": "error", "error": error_msg, "updated": 0}


@frappe.whitelist()
def get_sync_preview():
	"""
	Отримати попередній перегляд синхронізації (застарілий метод).
	Використовуйте get_sync_comparison() замість цього.
	"""
	return get_sync_comparison()


@frappe.whitelist()
def check_enabled_status_changes():
	"""
	Перевірити які показники потрібно увімкнути/вимкнути на основі даних порталу.

	ЗАСТАРІЛИЙ МЕТОД - використовується fetch_portal_parameters() який повертає
	дані про статуси в одному запиті.

	Логіка:
	- Якщо показник є локально, але відсутній на порталі -> enabled = false
	- Якщо показник локально enabled = false, але є на порталі -> enabled = true

	Returns:
	        dict: {
	                "status": "success" | "error",
	                "to_disable": list - показники для вимкнення,
	                "to_enable": list - показники для увімкнення,
	                "no_changes": bool - якщо змін немає
	        }
	"""
	if not frappe.has_permission("oiHromadaSettings", "read"):
		frappe.throw("Недостатньо прав для перегляду", frappe.PermissionError)

	settings = _get_settings()
	headers = _get_api_headers()
	base_url = settings.api_base_url or "https://backend.hromada.gov.ua/api"

	# Отримуємо параметри з порталу
	try:
		params_response = requests.get(
			f"{base_url}/front/index-group/parameters/location",
			params={"loadCommunity": "true"},
			headers=headers,
			timeout=120,
		)

		if params_response.status_code != 200:
			return {
				"status": "error",
				"error": f"Помилка отримання даних з порталу: {params_response.status_code}",
			}

		data = params_response.json()
		groups = data.get("data", [])

		# Збираємо ID та коди параметрів з порталу
		portal_param_ids = set()
		portal_param_codes = set()
		for group in groups:
			for subgroup in group.get("subgroups", []):
				for indicator in subgroup.get("indicators", []):
					for param in indicator.get("parameters", []):
						param_id = cint(param.get("id"))
						param_code = _normalize_code(param.get("code"))
						if param_id:
							portal_param_ids.add(param_id)
						if param_code:
							portal_param_codes.add(param_code)

	except requests.exceptions.RequestException as e:
		return {"status": "error", "error": f"Помилка запиту: {e!s}"}

	# Використовуємо спільну функцію перевірки
	to_disable, to_enable = _check_enabled_status_from_portal_data(portal_param_ids, portal_param_codes)

	return {
		"status": "success",
		"to_disable": to_disable,
		"to_enable": to_enable,
		"no_changes": len(to_disable) == 0 and len(to_enable) == 0,
	}


@frappe.whitelist()
def apply_enabled_status_changes(to_disable: str | list | None = None, to_enable: str | list | None = None):
	"""
	Застосувати зміни статусу enabled для показників.

	Args:
	        to_disable: JSON список name показників для вимкнення
	        to_enable: JSON список name показників для увімкнення

	Returns:
	        dict: Результат застосування змін
	"""
	if not frappe.has_permission("oiHromadaSettings", "write"):
		frappe.throw("Недостатньо прав для зміни статусів", frappe.PermissionError)

	# Парсимо списки
	if isinstance(to_disable, str):
		try:
			to_disable = json.loads(to_disable)
		except json.JSONDecodeError:
			to_disable = []
	to_disable = to_disable or []

	if isinstance(to_enable, str):
		try:
			to_enable = json.loads(to_enable)
		except json.JSONDecodeError:
			to_enable = []
	to_enable = to_enable or []

	disabled_count = 0
	enabled_count = 0

	# Вимикаємо показники
	for name in to_disable:
		if frappe.db.exists("oiHromadaSurvey", name):
			frappe.db.set_value("oiHromadaSurvey", name, "enabled", 0, update_modified=False)
			disabled_count += 1

	# Вмикаємо показники
	for name in to_enable:
		if frappe.db.exists("oiHromadaSurvey", name):
			frappe.db.set_value("oiHromadaSurvey", name, "enabled", 1, update_modified=False)
			enabled_count += 1

	if disabled_count > 0 or enabled_count > 0:
		_log_sync(f"Змінено статуси: вимкнено {disabled_count}, увімкнено {enabled_count}")
		frappe.db.commit()

	return {
		"status": "success",
		"disabled": disabled_count,
		"enabled": enabled_count,
	}


@frappe.whitelist()
def get_unmapped_parameters():
	"""
	Отримати список параметрів з порталу без mapping в системі.

	Returns:
	        list: Список незамаплених параметрів
	"""
	if not frappe.has_permission("oiHromadaSettings", "read"):
		frappe.throw("Недостатньо прав для перегляду", frappe.PermissionError)

	# Отримуємо всі коди показників з системи
	surveys = frappe.get_all(
		"oiHromadaSurvey",
		filters={"type": ["!=", "Група"]},
		fields=["id"],
	)

	local_codes = {_normalize_code(s.get("id")) for s in surveys if s.get("id")}

	# Отримуємо параметри з порталу
	result = fetch_portal_parameters()
	if result.get("status") != "success":
		return {"status": "error", "error": result.get("error")}

	parameters = result.get("parameters", [])

	# Фільтруємо незамаплені
	unmapped = []
	for param in parameters:
		norm_code = _normalize_code(param.get("code"))
		if norm_code and norm_code not in local_codes:
			unmapped.append(param)

	return {
		"status": "success",
		"total": len(unmapped),
		"unmapped": unmapped,
	}
