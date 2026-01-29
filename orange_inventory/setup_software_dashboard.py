# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Налаштування Dashboard для моніторингу ПЗ.

Запуск:
    bench --site {site} execute orange_inventory.setup_software_dashboard.setup
"""

import frappe


def setup():
	"""Створює всі компоненти dashboard для моніторингу ПЗ."""
	create_number_cards()
	create_dashboard_charts()
	create_dashboard()
	frappe.db.commit()
	print("✓ Software Dashboard створено успішно!")


def create_number_cards():
	"""Створює Number Cards для статистики ПЗ."""

	cards = [
		{
			"name": "Унікальні програми",
			"label": "Унікальні програми",
			"document_type": "oiAgentSoftware",
			"function": "Count",
			"color": "#4299E1",
			"show_percentage_stats": 0,
			"filters_json": "[]",
			"aggregate_function_based_on": "software_name",
		},
		{
			"name": "Дозволене ПЗ",
			"label": "Дозволене ПЗ",
			"document_type": "oiAgentSoftware",
			"function": "Count",
			"color": "#48BB78",
			"show_percentage_stats": 0,
			"filters_json": '[["oiAgentSoftware","compliance_status","=","Дозволено"]]',
		},
		{
			"name": "Заборонене ПЗ",
			"label": "Заборонене ПЗ",
			"document_type": "oiAgentSoftware",
			"function": "Count",
			"color": "#E53E3E",
			"show_percentage_stats": 0,
			"filters_json": '[["oiAgentSoftware","compliance_status","=","Заборонено"]]',
		},
		{
			"name": "Не в каталозі",
			"label": "Не в каталозі",
			"document_type": "oiAgentSoftware",
			"function": "Count",
			"color": "#ED8936",
			"show_percentage_stats": 0,
			"filters_json": '[["oiAgentSoftware","compliance_status","=","Не в каталозі"]]',
		},
		{
			"name": "Потребує оновлення",
			"label": "Потребує оновлення",
			"document_type": "oiAgentSoftware",
			"function": "Count",
			"color": "#F6AD55",
			"show_percentage_stats": 0,
			"filters_json": '[["oiAgentSoftware","needs_update","=","1"]]',
		},
		{
			"name": "Записів у каталозі",
			"label": "Записів у каталозі",
			"document_type": "oiSoftwareCatalog",
			"function": "Count",
			"color": "#667EEA",
			"show_percentage_stats": 0,
			"filters_json": "[]",
		},
	]

	for card_data in cards:
		if frappe.db.exists("Number Card", card_data["name"]):
			print(f"  - Number Card '{card_data['name']}' вже існує, оновлюю...")
			doc = frappe.get_doc("Number Card", card_data["name"])
			doc.update(card_data)
			doc.save()
		else:
			print(f"  + Створюю Number Card '{card_data['name']}'...")
			doc = frappe.get_doc({"doctype": "Number Card", **card_data})
			doc.insert(ignore_permissions=True)


def create_dashboard_charts():
	"""Створює графіки для моніторингу ПЗ."""

	# Графік статусів відповідності
	compliance_chart = {
		"name": "Статуси відповідності ПЗ",
		"chart_name": "Статуси відповідності ПЗ",
		"chart_type": "Group By",
		"document_type": "oiAgentSoftware",
		"group_by_type": "Count",
		"group_by_based_on": "compliance_status",
		"type": "Donut",
		"color": "#4299E1",
		"filters_json": "[]",
		"timeseries": 0,
		"number_of_groups": 0,
	}

	if frappe.db.exists("Dashboard Chart", compliance_chart["name"]):
		print(f"  - Dashboard Chart '{compliance_chart['name']}' вже існує, оновлюю...")
		doc = frappe.get_doc("Dashboard Chart", compliance_chart["name"])
		doc.update(compliance_chart)
		doc.save()
	else:
		print(f"  + Створюю Dashboard Chart '{compliance_chart['name']}'...")
		doc = frappe.get_doc({"doctype": "Dashboard Chart", **compliance_chart})
		doc.insert(ignore_permissions=True)

	# Графік категорій ПЗ в каталозі
	category_chart = {
		"name": "Категорії ПЗ у каталозі",
		"chart_name": "Категорії ПЗ у каталозі",
		"chart_type": "Group By",
		"document_type": "oiSoftwareCatalog",
		"group_by_type": "Count",
		"group_by_based_on": "category",
		"type": "Bar",
		"color": "#667EEA",
		"filters_json": "[]",
		"timeseries": 0,
		"number_of_groups": 0,
	}

	if frappe.db.exists("Dashboard Chart", category_chart["name"]):
		print(f"  - Dashboard Chart '{category_chart['name']}' вже існує, оновлюю...")
		doc = frappe.get_doc("Dashboard Chart", category_chart["name"])
		doc.update(category_chart)
		doc.save()
	else:
		print(f"  + Створюю Dashboard Chart '{category_chart['name']}'...")
		doc = frappe.get_doc({"doctype": "Dashboard Chart", **category_chart})
		doc.insert(ignore_permissions=True)


def create_dashboard():
	"""Створює Dashboard для моніторингу ПЗ."""

	dashboard_name = "Software Monitoring"

	if frappe.db.exists("Dashboard", dashboard_name):
		print(f"  - Dashboard '{dashboard_name}' вже існує, оновлюю...")
		frappe.delete_doc("Dashboard", dashboard_name, force=True)

	print(f"  + Створюю Dashboard '{dashboard_name}'...")

	dashboard = frappe.get_doc(
		{
			"doctype": "Dashboard",
			"name": dashboard_name,
			"dashboard_name": dashboard_name,
			"module": "Orange Inventory",
			"is_default": 0,
			"charts": [
				{
					"chart": "Статуси відповідності ПЗ",
					"width": "Half",
				},
				{
					"chart": "Категорії ПЗ у каталозі",
					"width": "Half",
				},
			],
			"cards": [
				{"card": "Записів у каталозі"},
				{"card": "Дозволене ПЗ"},
				{"card": "Заборонене ПЗ"},
				{"card": "Не в каталозі"},
				{"card": "Потребує оновлення"},
			],
		}
	)
	dashboard.insert(ignore_permissions=True)


def cleanup():
	"""Видаляє всі компоненти dashboard (для тестування)."""
	cards = [
		"Унікальні програми",
		"Дозволене ПЗ",
		"Заборонене ПЗ",
		"Не в каталозі",
		"Потребує оновлення",
		"Записів у каталозі",
	]
	charts = ["Статуси відповідності ПЗ", "Категорії ПЗ у каталозі"]

	for card in cards:
		if frappe.db.exists("Number Card", card):
			frappe.delete_doc("Number Card", card, force=True)
			print(f"  - Видалено Number Card '{card}'")

	for chart in charts:
		if frappe.db.exists("Dashboard Chart", chart):
			frappe.delete_doc("Dashboard Chart", chart, force=True)
			print(f"  - Видалено Dashboard Chart '{chart}'")

	if frappe.db.exists("Dashboard", "Software Monitoring"):
		frappe.delete_doc("Dashboard", "Software Monitoring", force=True)
		print("  - Видалено Dashboard 'Software Monitoring'")

	frappe.db.commit()
	print("✓ Cleanup завершено!")
