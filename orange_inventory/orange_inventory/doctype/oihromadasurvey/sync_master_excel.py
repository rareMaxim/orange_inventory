# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Синхронізація показників oiHromadaSurvey з Excel файлу паспорта індикаторів.

Цей модуль забезпечує імпорт та синхронізацію структури індикаторів
з офіційного Excel файлу "Індекс територіальних громад".
"""

import os

import frappe
from frappe.utils.data import cint


def _normalize_id(raw_id: str | None) -> str | None:
	"""
	Нормалізує ID показника: прибирає пробіли, переноси рядків,
	заміняє українські літери на латинські для консистентності.

	Args:
	        raw_id: Сирий ID з Excel

	Returns:
	        Нормалізований ID або None
	"""
	if not raw_id:
		return None
	# Очищаємо від пробілів та переносів
	cleaned = str(raw_id).strip().replace("\n", "").replace(" ", "")
	# Нормалізуємо літери (українські -> латинські для консистентності)
	# А (укр, U+0410) -> A (лат, U+0041)
	# В (укр, U+0412) -> B (лат, U+0042)
	# С (укр, U+0421) -> C (лат, U+0043)
	cleaned = cleaned.replace("А", "A").replace("В", "B").replace("С", "C")
	return cleaned if cleaned else None


def _parse_frequency(freq_str: str | None) -> str:
	"""
	Парсить періодичність з Excel у формат Frappe.

	Args:
	        freq_str: Рядок періодичності з Excel

	Returns:
	        "Раз на рік" або "Раз на квартал"
	"""
	if not freq_str:
		return "Раз на квартал"
	freq_lower = str(freq_str).lower().strip()
	if "рік" in freq_lower or "год" in freq_lower:
		return "Раз на рік"
	return "Раз на квартал"


def _parse_data_type(type_str: str | None) -> str:
	"""
	Парсить тип даних з Excel.

	Args:
	        type_str: Рядок типу даних з Excel

	Returns:
	        "Якісні дані" або "Кількісні дані"
	"""
	if not type_str:
		return "Кількісні дані"
	type_lower = str(type_str).lower().strip()
	if "якісн" in type_lower:
		return "Якісні дані"
	return "Кількісні дані"


def _determine_group_id(title: str) -> str | None:
	"""
	Визначає ID групи верхнього рівня за назвою.

	Args:
	        title: Назва групи

	Returns:
	        ID групи (A, B, C, D) або None
	"""
	if not title:
		return None
	title_lower = title.lower()
	if "економіка" in title_lower:
		return "A"
	elif "навичк" in title_lower:
		return "B"
	elif "інфраструктур" in title_lower:
		return "C"
	elif "публічн" in title_lower or "послуг" in title_lower:
		return "D"
	return None


def _parse_master_excel(file_path: str) -> list[dict]:
	"""
	Парсить Excel файл паспорта індикаторів.

	Структура Excel (лист "Структура індикаторів громад"):
	- Колонка 1: Група верхнього рівня
	- Колонка 3: Підгрупа
	- Колонка 4: # Індикатора (A.1.1, B.1.2 тощо)
	- Колонка 5: Назва індикатора
	- Колонка 6: Структура індексу (Базовий/Розширений)
	- Колонка 7: Вид індикатора
	- Колонка 8: Характер даних (Кількісні/Якісні)
	- Колонка 9: Номер Показника (A.1.1.1, A.1.1.2 тощо)
	- Колонка 10: Назва показника
	- Колонка 11: Визначення
	- Колонка 12: Періодичність
	- Колонка 14: Джерело даних

	Args:
	        file_path: Шлях до Excel файлу

	Returns:
	        Список записів для синхронізації
	"""
	from openpyxl import load_workbook

	wb = load_workbook(file_path, data_only=True)

	# Шукаємо потрібний лист
	sheet_name = None
	for name in wb.sheetnames:
		if "структура" in name.lower() and "індикатор" in name.lower():
			sheet_name = name
			break

	if not sheet_name:
		wb.close()
		raise ValueError("Не знайдено лист 'Структура індикаторів громад' у файлі")

	ws = wb[sheet_name]
	records = []

	# Контекст для відстеження ієрархії (для заповнення пропущених значень)
	current_group = None
	current_group_title = None
	current_subgroup = None
	current_indicator_id = None
	current_indicator_title = None
	current_data_type = None

	# Починаємо з 2-го рядка (пропускаємо заголовки)
	for row in ws.iter_rows(min_row=2, values_only=True):
		# Пропускаємо пусті рядки
		if not any(cell for cell in row if cell):
			continue

		# Отримуємо значення з колонок
		col_group = str(row[0]).strip() if row[0] else None
		col_subgroup = str(row[2]).strip() if len(row) > 2 and row[2] else None
		col_indicator_id = row[3] if len(row) > 3 else None
		col_indicator_title = str(row[4]).strip() if len(row) > 4 and row[4] else None
		col_index_type = str(row[5]).strip() if len(row) > 5 and row[5] else None
		col_indicator_type = str(row[6]).strip() if len(row) > 6 and row[6] else None
		col_data_type = str(row[7]).strip() if len(row) > 7 and row[7] else None
		col_pokaznyk_id = row[8] if len(row) > 8 else None
		col_pokaznyk_title = str(row[9]).strip() if len(row) > 9 and row[9] else None
		col_definition = str(row[10]).strip() if len(row) > 10 and row[10] else None
		col_frequency = str(row[11]).strip() if len(row) > 11 and row[11] else None
		col_source = str(row[13]).strip() if len(row) > 13 and row[13] else None

		# Оновлюємо контекст якщо є нові значення
		if col_group and col_group.strip():
			current_group_title = col_group.strip()
			current_group = _determine_group_id(current_group_title)

		if col_subgroup and col_subgroup.strip():
			current_subgroup = col_subgroup.strip()

		if col_indicator_id:
			normalized = _normalize_id(str(col_indicator_id))
			if normalized:
				current_indicator_id = normalized
				current_indicator_title = col_indicator_title
				current_data_type = col_data_type

		# Обробляємо показник якщо є ID
		if col_pokaznyk_id:
			pokaznyk_id = _normalize_id(str(col_pokaznyk_id))
			if not pokaznyk_id:
				continue

			# Формуємо запис показника
			record = {
				"id": pokaznyk_id,
				"title": col_pokaznyk_title or "",
				"type": _parse_data_type(col_data_type or current_data_type),
				"frequency": _parse_frequency(col_frequency),
				"description": col_definition or "",
				"is_group": 0,
				"enabled": 1,
				# Ієрархія
				"group_id": current_group,
				"group_title": current_group_title,
				"subgroup_title": current_subgroup,
				"indicator_id": current_indicator_id,
				"indicator_title": current_indicator_title,
				# Додаткова інформація
				"index_type": col_index_type,
				"indicator_type": col_indicator_type,
				"source": col_source,
			}
			records.append(record)

	wb.close()
	return records


def _build_hierarchy(records: list[dict]) -> dict:
	"""
	Будує ієрархію з плоского списку записів.

	Args:
	        records: Список записів з _parse_master_excel

	Returns:
	        Словник з групами, підгрупами, індикаторами та показниками
	"""
	hierarchy = {
		"groups": {},
		"subgroups": {},
		"indicators": {},
		"pokaznyky": {},
	}

	# Визначаємо групи верхнього рівня
	group_mapping = {
		"A": "Цифрова економіка",
		"B": "Цифрові навички",
		"C": "Цифрова інфраструктура",
		"D": "Цифровізація публічних послуг",
	}

	for record in records:
		group_id = record.get("group_id")
		if not group_id:
			continue

		# Додаємо групу верхнього рівня
		if group_id not in hierarchy["groups"]:
			hierarchy["groups"][group_id] = {
				"id": group_id,
				"title": record.get("group_title") or group_mapping.get(group_id, f"Група {group_id}"),
				"type": "Група",
				"is_group": 1,
				"enabled": 1,
			}

		# Додаємо підгрупу
		subgroup_title = record.get("subgroup_title")
		if subgroup_title:
			indicator_id = record.get("indicator_id", "")
			if indicator_id and "." in indicator_id:
				parts = indicator_id.split(".")
				subgroup_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else indicator_id
			else:
				subgroup_id = f"{group_id}.{len(hierarchy['subgroups']) + 1}"

			subgroup_key = f"{group_id}:{subgroup_title}"
			if subgroup_key not in hierarchy["subgroups"]:
				hierarchy["subgroups"][subgroup_key] = {
					"id": subgroup_id,
					"title": subgroup_title,
					"type": "Група",
					"is_group": 1,
					"enabled": 1,
					"parent_id": group_id,
				}

		# Додаємо індикатор
		indicator_id = record.get("indicator_id")
		indicator_title = record.get("indicator_title")
		if indicator_id and indicator_title:
			if indicator_id not in hierarchy["indicators"]:
				parent_subgroup_id = None
				if indicator_id and "." in indicator_id:
					parts = indicator_id.split(".")
					parent_subgroup_id = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else None

				hierarchy["indicators"][indicator_id] = {
					"id": indicator_id,
					"title": indicator_title,
					"type": "Група",
					"is_group": 1,
					"enabled": 1,
					"parent_id": parent_subgroup_id,
					"index_type": record.get("index_type"),
					"indicator_type": record.get("indicator_type"),
				}

		# Додаємо показник
		pokaznyk_id = record.get("id")
		if pokaznyk_id:
			hierarchy["pokaznyky"][pokaznyk_id] = {
				"id": pokaznyk_id,
				"title": record.get("title", ""),
				"type": record.get("type", "Кількісні дані"),
				"frequency": record.get("frequency", "Раз на квартал"),
				"description": record.get("description", ""),
				"is_group": 0,
				"enabled": 1,
				"parent_id": record.get("indicator_id"),
				"source": record.get("source"),
			}

	return hierarchy


def _sync_record(
	data: dict,
	parent_name: str | None,
	existing: dict,
	dry_run: bool,
	stats: dict,
	details: list,
	errors: list,
) -> str | None:
	"""
	Створює або оновлює запис в БД.

	Args:
	        data: Дані для запису
	        parent_name: Name батьківського запису
	        existing: Словник існуючих записів {id: doc}
	        dry_run: Чи це тестовий запуск
	        stats: Статистика (created, updated, unchanged)
	        details: Список деталей змін
	        errors: Список помилок

	Returns:
	        Name створеного/оновленого запису або None
	"""
	record_id = data.get("id")
	if not record_id:
		return None

	try:
		if record_id in existing:
			# Оновлюємо існуючий запис
			doc = frappe.get_doc("oiHromadaSurvey", existing[record_id]["name"])

			needs_update = False
			changes = []

			if data.get("title") and doc.title != data["title"]:
				changes.append(f"title: '{doc.title[:30]}...' -> '{data['title'][:30]}...'")
				if not dry_run:
					doc.title = data["title"]
				needs_update = True

			if data.get("type") and doc.type != data["type"]:
				changes.append(f"type: '{doc.type}' -> '{data['type']}'")
				if not dry_run:
					doc.type = data["type"]
				needs_update = True

			if data.get("frequency") and doc.frequency != data["frequency"]:
				changes.append(f"frequency: '{doc.frequency}' -> '{data['frequency']}'")
				if not dry_run:
					doc.frequency = data["frequency"]
				needs_update = True

			if data.get("description") and doc.description != data["description"]:
				changes.append("description: [змінено]")
				if not dry_run:
					doc.description = data["description"]
				needs_update = True

			if needs_update:
				if not dry_run:
					doc.flags.ignore_permissions = True
					doc.save()
				stats["updated"] += 1
				details.append(
					{
						"action": "updated",
						"id": record_id,
						"title": data.get("title", "")[:50],
						"changes": changes,
					}
				)
			else:
				stats["unchanged"] += 1

			return doc.name if not dry_run else existing[record_id]["name"]
		else:
			# Створюємо новий запис
			new_doc = frappe.new_doc("oiHromadaSurvey")
			new_doc.id = record_id
			new_doc.title = data.get("title", "")
			new_doc.type = data.get("type", "Група" if data.get("is_group") else "Кількісні дані")
			new_doc.frequency = data.get("frequency", "Раз на квартал")
			new_doc.description = data.get("description", "")
			new_doc.is_group = cint(data.get("is_group", 0))
			new_doc.enabled = 1

			if parent_name:
				new_doc.parent_oihromadasurvey = parent_name

			if not dry_run:
				new_doc.flags.ignore_permissions = True
				new_doc.insert()

			stats["created"] += 1
			details.append(
				{
					"action": "created",
					"id": record_id,
					"title": data.get("title", "")[:50],
					"parent": parent_name,
				}
			)

			return new_doc.name if not dry_run else f"NEW:{record_id}"

	except Exception as e:
		errors.append(f"Помилка обробки {record_id}: {str(e)}")
		return None


@frappe.whitelist()
def sync_from_master_excel(file_url: str, dry_run: int = 0):
	"""
	Синхронізує структуру показників з Excel файлу паспорта індикаторів.

	Функціонал:
	- Парсить офіційний Excel файл "Індекс територіальних громад"
	- Створює нові записи якщо їх немає в системі
	- Оновлює існуючі записи якщо дані змінились
	- НЕ видаляє записи яких немає в файлі

	Args:
	        file_url: URL завантаженого Excel файлу (паспорт індикаторів)
	        dry_run: Якщо 1, тільки аналізує зміни без збереження

	Returns:
	        dict: {
	                "status": "success" | "error",
	                "dry_run": bool,
	                "total_in_file": int,
	                "created": int,
	                "updated": int,
	                "unchanged": int,
	                "errors": list,
	                "details": list (обмежено до 100 записів)
	        }
	"""
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "write"):
		frappe.throw("Недостатньо прав для синхронізації даних", frappe.PermissionError)

	dry_run = bool(cint(dry_run))

	# Отримуємо файл
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	file_path = file_doc.get_full_path()

	if not os.path.exists(file_path):
		frappe.throw(f"Файл не знайдено: {file_path}")

	# Парсимо Excel
	try:
		records = _parse_master_excel(file_path)
	except Exception as e:
		frappe.throw(f"Помилка парсингу Excel: {str(e)}")

	if not records:
		return {
			"status": "error",
			"message": "Не знайдено жодного запису у файлі",
			"created": 0,
			"updated": 0,
			"unchanged": 0,
			"errors": [],
			"details": [],
		}

	# Будуємо ієрархію
	hierarchy = _build_hierarchy(records)

	# Отримуємо існуючі записи
	existing = {}
	for doc in frappe.get_all(
		"oiHromadaSurvey",
		fields=[
			"name",
			"id",
			"title",
			"type",
			"frequency",
			"description",
			"is_group",
			"parent_oihromadasurvey",
		],
	):
		if doc.id:
			existing[doc.id] = doc

	# Статистика та деталі
	stats = {"created": 0, "updated": 0, "unchanged": 0}
	details = []
	errors = []

	try:
		# Синхронізуємо групи верхнього рівня
		group_names = {}
		for group_id, group_data in sorted(hierarchy["groups"].items()):
			name = _sync_record(group_data, None, existing, dry_run, stats, details, errors)
			if name:
				group_names[group_id] = name

		# Синхронізуємо підгрупи
		subgroup_names = {}
		for subgroup_data in hierarchy["subgroups"].values():
			parent_id = subgroup_data.get("parent_id")
			parent_name = group_names.get(parent_id)
			name = _sync_record(subgroup_data, parent_name, existing, dry_run, stats, details, errors)
			if name:
				subgroup_names[subgroup_data["id"]] = name

		# Синхронізуємо індикатори
		indicator_names = {}
		for indicator_id, indicator_data in sorted(hierarchy["indicators"].items()):
			parent_id = indicator_data.get("parent_id")
			parent_name = subgroup_names.get(parent_id)
			name = _sync_record(indicator_data, parent_name, existing, dry_run, stats, details, errors)
			if name:
				indicator_names[indicator_id] = name

		# Синхронізуємо показники
		for pokaznyk_data in sorted(hierarchy["pokaznyky"].values(), key=lambda x: x.get("id", "")):
			parent_id = pokaznyk_data.get("parent_id")
			parent_name = indicator_names.get(parent_id)
			_sync_record(pokaznyk_data, parent_name, existing, dry_run, stats, details, errors)

		if not dry_run:
			frappe.db.commit()

	except Exception as e:
		# Rollback при критичній помилці
		if not dry_run:
			frappe.db.rollback()
		return {
			"status": "error",
			"message": f"Критична помилка синхронізації: {e!s}. Всі зміни скасовано.",
			"dry_run": dry_run,
			"total_in_file": len(records),
			"created": 0,
			"updated": 0,
			"unchanged": 0,
			"errors": errors + [f"Критична помилка: {e!s}"],
			"details": [],
		}

	return {
		"status": "success" if not errors else "partial",
		"dry_run": dry_run,
		"total_in_file": len(records),
		"created": stats["created"],
		"updated": stats["updated"],
		"unchanged": stats["unchanged"],
		"errors": errors,
		"details": details[:100],  # Обмежуємо для великих файлів
	}


@frappe.whitelist()
def get_sync_preview(file_url: str):
	"""
	Попередній перегляд синхронізації без внесення змін.

	Args:
	        file_url: URL завантаженого Excel файлу

	Returns:
	        Результат sync_from_master_excel з dry_run=1
	"""
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "read"):
		frappe.throw("Недостатньо прав для перегляду синхронізації", frappe.PermissionError)

	return sync_from_master_excel(file_url, dry_run=1)


@frappe.whitelist()
def get_excel_structure_info(file_url: str):
	"""
	Отримує інформацію про структуру Excel файлу для попереднього перегляду.

	Args:
	        file_url: URL завантаженого Excel файлу

	Returns:
	        dict з інформацією про листи та структуру даних
	"""
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "read"):
		frappe.throw("Недостатньо прав для перегляду структури файлу", frappe.PermissionError)

	from openpyxl import load_workbook

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	file_path = file_doc.get_full_path()

	if not os.path.exists(file_path):
		frappe.throw(f"Файл не знайдено: {file_path}")

	wb = load_workbook(file_path, data_only=True)

	info = {
		"sheets": wb.sheetnames,
		"target_sheet": None,
		"rows_count": 0,
		"sample_data": [],
	}

	# Шукаємо цільовий лист
	for name in wb.sheetnames:
		if "структура" in name.lower() and "індикатор" in name.lower():
			info["target_sheet"] = name
			ws = wb[name]
			info["rows_count"] = ws.max_row

			# Отримуємо зразок даних (перші 5 рядків)
			for row_idx, row in enumerate(ws.iter_rows(max_row=6, values_only=True), start=1):
				row_data = [str(cell)[:50] if cell else "" for cell in row[:15]]
				info["sample_data"].append({"row": row_idx, "data": row_data})
			break

	wb.close()
	return info
