# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Setup functions for Orange Inventory.
"""

import json
import os

import frappe


def after_install():
	"""Виконується після встановлення додатку."""
	import_default_command_templates()


def import_default_command_templates():
	"""
	Імпортує стандартні шаблони команд з JSON файлу.
	Можна викликати вручну: bench execute orange_inventory.setup.import_default_command_templates
	"""
	# Шлях до файлу з шаблонами
	app_path = frappe.get_app_path("orange_inventory")
	fixtures_path = os.path.join(
		app_path,
		"orange_inventory",
		"doctype",
		"oicommandtemplate",
		"fixtures",
		"default_templates.json",
	)

	if not os.path.exists(fixtures_path):
		frappe.log_error(f"Fixtures file not found: {fixtures_path}", "Setup Error")
		print(f"❌ Файл не знайдено: {fixtures_path}")
		return

	with open(fixtures_path, encoding="utf-8") as f:
		templates = json.load(f)

	imported = 0
	skipped = 0

	for template_data in templates:
		template_name = template_data.get("template_name")

		# Перевіряємо чи вже існує
		if frappe.db.exists("oiCommandTemplate", {"template_name": template_name}):
			skipped += 1
			continue

		try:
			doc = frappe.get_doc(template_data)
			doc.insert(ignore_permissions=True)
			imported += 1
			print(f"✓ Імпортовано: {template_name}")
		except Exception as e:
			frappe.log_error(f"Error importing template {template_name}: {e}", "Setup Error")
			print(f"✗ Помилка: {template_name} - {e}")

	frappe.db.commit()
	print(f"\n📋 Результат: імпортовано {imported}, пропущено {skipped} (вже існують)")
	return {"imported": imported, "skipped": skipped}
