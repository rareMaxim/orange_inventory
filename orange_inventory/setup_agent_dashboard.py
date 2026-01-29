# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Налаштування Dashboard для агентів моніторингу.

Запуск:
    bench --site {site} execute orange_inventory.setup_agent_dashboard.setup
"""

import frappe


def setup():
	"""Створює всі компоненти dashboard для агентів."""
	create_number_cards()
	create_dashboard_chart()
	create_dashboard()
	frappe.db.commit()
	print("✓ Agent Dashboard створено успішно!")


def create_number_cards():
	"""Створює Number Cards для статистики агентів."""

	cards = [
		{
			"name": "Всього агентів",
			"label": "Всього агентів",
			"document_type": "oiAgent",
			"function": "Count",
			"color": "#4299E1",
			"show_percentage_stats": 0,
			"filters_json": "[]",
		},
		{
			"name": "Активні агенти",
			"label": "Активні агенти",
			"document_type": "oiAgent",
			"function": "Count",
			"color": "#48BB78",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily",
			"filters_json": '[["oiAgent","status","=","Активний"]]',
		},
		{
			"name": "Офлайн агенти",
			"label": "Офлайн агенти",
			"document_type": "oiAgent",
			"function": "Count",
			"color": "#F56565",
			"show_percentage_stats": 1,
			"stats_time_interval": "Daily",
			"filters_json": '[["oiAgent","status","=","Офлайн"]]',
		},
		{
			"name": "Непривʼязані агенти",
			"label": "Непривʼязані агенти",
			"document_type": "oiAgent",
			"function": "Count",
			"color": "#ED8936",
			"show_percentage_stats": 0,
			"filters_json": '[["oiAgent","asset","is","not set"]]',
		},
		{
			"name": "Активні сповіщення",
			"label": "Активні сповіщення",
			"document_type": "oiAgentAlert",
			"function": "Count",
			"color": "#E53E3E",
			"show_percentage_stats": 0,
			"filters_json": '[["oiAgentAlert","status","=","Активне"]]',
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


def create_dashboard_chart():
	"""Створює графік розподілу статусів агентів."""

	chart_data = {
		"name": "Статуси агентів",
		"chart_name": "Статуси агентів",
		"chart_type": "Group By",
		"document_type": "oiAgent",
		"group_by_type": "Count",
		"group_by_based_on": "status",
		"type": "Donut",
		"color": "#4299E1",
		"filters_json": "[]",
		"timeseries": 0,
		"number_of_groups": 0,
	}

	if frappe.db.exists("Dashboard Chart", chart_data["name"]):
		print(f"  - Dashboard Chart '{chart_data['name']}' вже існує, оновлюю...")
		doc = frappe.get_doc("Dashboard Chart", chart_data["name"])
		doc.update(chart_data)
		doc.save()
	else:
		print(f"  + Створюю Dashboard Chart '{chart_data['name']}'...")
		doc = frappe.get_doc({"doctype": "Dashboard Chart", **chart_data})
		doc.insert(ignore_permissions=True)

	# Графік активності за останні 7 днів
	activity_chart = {
		"name": "Активність агентів",
		"chart_name": "Активність агентів",
		"chart_type": "Count",
		"document_type": "oiAgentSnapshot",
		"based_on": "timestamp",
		"type": "Line",
		"color": "#48BB78",
		"filters_json": "[]",
		"timeseries": 1,
		"timespan": "Last Week",
		"time_interval": "Daily",
	}

	if frappe.db.exists("Dashboard Chart", activity_chart["name"]):
		print(f"  - Dashboard Chart '{activity_chart['name']}' вже існує, оновлюю...")
		doc = frappe.get_doc("Dashboard Chart", activity_chart["name"])
		doc.update(activity_chart)
		doc.save()
	else:
		print(f"  + Створюю Dashboard Chart '{activity_chart['name']}'...")
		doc = frappe.get_doc({"doctype": "Dashboard Chart", **activity_chart})
		doc.insert(ignore_permissions=True)


def create_dashboard():
	"""Створює Dashboard для агентів."""

	dashboard_name = "Agent Monitoring"

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
					"chart": "Статуси агентів",
					"width": "Half",
				},
				{
					"chart": "Активність агентів",
					"width": "Half",
				},
			],
			"cards": [
				{"card": "Всього агентів"},
				{"card": "Активні агенти"},
				{"card": "Офлайн агенти"},
				{"card": "Непривʼязані агенти"},
				{"card": "Активні сповіщення"},
			],
		}
	)
	dashboard.insert(ignore_permissions=True)


def cleanup():
	"""Видаляє всі компоненти dashboard (для тестування)."""
	cards = ["Всього агентів", "Активні агенти", "Офлайн агенти", "Непривʼязані агенти"]
	charts = ["Статуси агентів", "Активність агентів"]

	for card in cards:
		if frappe.db.exists("Number Card", card):
			frappe.delete_doc("Number Card", card, force=True)
			print(f"  - Видалено Number Card '{card}'")

	for chart in charts:
		if frappe.db.exists("Dashboard Chart", chart):
			frappe.delete_doc("Dashboard Chart", chart, force=True)
			print(f"  - Видалено Dashboard Chart '{chart}'")

	if frappe.db.exists("Dashboard", "Agent Monitoring"):
		frappe.delete_doc("Dashboard", "Agent Monitoring", force=True)
		print("  - Видалено Dashboard 'Agent Monitoring'")

	frappe.db.commit()
	print("✓ Cleanup завершено!")
