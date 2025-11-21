# Copyright (c) 2025, IT MLT and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	return columns, data, None, chart


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "monitoring_name",
			"label": _("Моніторинг"),
			"fieldtype": "Link",
			"options": "oiPriceMonitoring",
			"width": 150,
		},
		{"fieldname": "monitoring_date", "label": _("Дата"), "fieldtype": "Date", "width": 100},
		{"fieldname": "counterparty_name", "label": _("Контрагент"), "fieldtype": "Data", "width": 150},
		{"fieldname": "item_name", "label": _("Позиція"), "fieldtype": "Data", "width": 200},
		{"fieldname": "quantity", "label": _("Кількість"), "fieldtype": "Int", "width": 80},
		{"fieldname": "min_price", "label": _("Мін. ціна"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "avg_price", "label": _("Сер. ціна"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "max_price", "label": _("Макс. ціна"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "status", "label": _("Статус"), "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	"""Fetch price monitoring data"""
	conditions = []
	values = {}

	# Build filter conditions
	if filters.get("status"):
		conditions.append("pm.status = %(status)s")
		values["status"] = filters.get("status")

	if filters.get("from_date"):
		conditions.append("pm.monitoring_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("pm.monitoring_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	if filters.get("counterparty"):
		conditions.append("pm.expected_counterparty = %(counterparty)s")
		values["counterparty"] = filters.get("counterparty")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	query = f"""
		SELECT
			pm.name as monitoring_name,
			pm.monitoring_date,
			cp.counterparty_name,
			pmi.item_name,
			pmi.quantity,
			pmi.min_price,
			pmi.avg_price,
			pmi.max_price,
			pm.status
		FROM
			`taboiPriceMonitoring` pm
		LEFT JOIN
			`taboiPriceMonitoringItem` pmi ON pmi.parent = pm.name
		LEFT JOIN
			`taboiCounterparty` cp ON pm.expected_counterparty = cp.name
		WHERE
			{where_clause}
		ORDER BY
			pm.monitoring_date DESC, pm.name, pmi.idx
	"""

	data = frappe.db.sql(query, values, as_dict=1)
	return data


def get_chart_data(data):
	"""Generate chart for price comparison"""
	if not data:
		return None

	labels = []
	min_prices = []
	avg_prices = []
	max_prices = []

	for row in data:
		if row.get("item_name"):
			labels.append(row.get("item_name")[:30])  # Limit label length
			min_prices.append(row.get("min_price") or 0)
			avg_prices.append(row.get("avg_price") or 0)
			max_prices.append(row.get("max_price") or 0)

	return {
		"data": {
			"labels": labels[:20],  # Limit to first 20 items
			"datasets": [
				{"name": "Мін. ціна", "values": min_prices[:20]},
				{"name": "Сер. ціна", "values": avg_prices[:20]},
				{"name": "Макс. ціна", "values": max_prices[:20]},
			],
		},
		"type": "bar",
		"colors": ["#28a745", "#78d6ff", "#fc4f51"],
	}
