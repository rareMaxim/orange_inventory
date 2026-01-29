# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "software_name",
			"label": "Програма",
			"fieldtype": "Data",
			"width": 300,
		},
		{
			"fieldname": "publisher",
			"label": "Видавець",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "installations",
			"label": "Встановлень",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "versions",
			"label": "Версії",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "compliance_status",
			"label": "Статус",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"fieldname": "agents",
			"label": "Комп'ютери",
			"fieldtype": "Data",
			"width": 300,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters:
		if filters.get("compliance_status"):
			conditions.append("sw.compliance_status = %(compliance_status)s")
			values["compliance_status"] = filters.get("compliance_status")

		if filters.get("software_name"):
			conditions.append("sw.software_name LIKE %(software_name)s")
			values["software_name"] = f"%{filters.get('software_name')}%"

		if filters.get("publisher"):
			conditions.append("sw.publisher LIKE %(publisher)s")
			values["publisher"] = f"%{filters.get('publisher')}%"

	where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

	data = frappe.db.sql(
		f"""
		SELECT
			sw.software_name,
			sw.publisher,
			COUNT(DISTINCT sw.agent) as installations,
			GROUP_CONCAT(DISTINCT sw.version ORDER BY sw.version SEPARATOR ', ') as versions,
			sw.compliance_status,
			GROUP_CONCAT(DISTINCT ag.hostname ORDER BY ag.hostname SEPARATOR ', ') as agents
		FROM `taboiAgentSoftware` sw
		LEFT JOIN `taboiAgent` ag ON sw.agent = ag.name
		{where_clause}
		GROUP BY sw.software_name, sw.publisher, sw.compliance_status
		ORDER BY installations DESC, sw.software_name
	""",
		values,
		as_dict=True,
	)

	return data
