# Copyright (c) 2025, IT MLT and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "contract_number",
			"label": _("Номер договору"),
			"fieldtype": "Link",
			"options": "oiContract",
			"width": 150,
		},
		{"fieldname": "contract_date", "label": _("Дата"), "fieldtype": "Date", "width": 100},
		{"fieldname": "contract_type", "label": _("Тип"), "fieldtype": "Data", "width": 150},
		{"fieldname": "counterparty_name", "label": _("Контрагент"), "fieldtype": "Data", "width": 200},
		{"fieldname": "status", "label": _("Статус"), "fieldtype": "Data", "width": 120},
		{"fieldname": "total_amount", "label": _("Сума"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "currency", "label": _("Валюта"), "fieldtype": "Data", "width": 80},
		{"fieldname": "start_date", "label": _("Початок дії"), "fieldtype": "Date", "width": 100},
		{"fieldname": "end_date", "label": _("Кінець дії"), "fieldtype": "Date", "width": 100},
	]


def get_data(filters):
	"""Fetch contract data"""
	conditions = []
	values = {}

	# Build filter conditions
	if filters.get("contract_type"):
		conditions.append("contract_type = %(contract_type)s")
		values["contract_type"] = filters.get("contract_type")

	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters.get("status")

	if filters.get("from_date"):
		conditions.append("contract_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("contract_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	where_clause = " AND ".join(conditions) if conditions else "1=1"

	query = f"""
		SELECT
			c.name as contract_number,
			c.contract_date,
			c.contract_type,
			cp.counterparty_name,
			c.status,
			c.total_amount,
			c.currency,
			c.start_date,
			c.end_date
		FROM
			`taboiContract` c
		LEFT JOIN
			`taboiCounterparty` cp ON c.counterparty = cp.name
		WHERE
			{where_clause}
		ORDER BY
			c.contract_date DESC
	"""

	data = frappe.db.sql(query, values, as_dict=1)
	return data
