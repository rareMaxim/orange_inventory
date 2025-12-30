# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_assets_by_decision(decision):
	"""
	Отримує всі активи, пов'язані з рішенням (oiBasisDoc).
	Шукає активи через:
	1. oiReceiptOrder (прибуткові ордери) - активи, що надійшли за цим рішенням
	2. oiIssueOrder (видаткові ордери) - активи, що передавалися за цим рішенням
	3. oiAssetMovementHistory - історія передачі з посиланням на рішення
	"""
	if not decision:
		return {"assets": [], "decision_info": {}, "summary": {}}

	# Отримуємо інформацію про рішення
	decision_info = frappe.get_doc("oiBasisDoc", decision)

	# Знаходимо всі активи через історію руху
	asset_names = frappe.db.sql(
		"""
		SELECT DISTINCT parent
		FROM `taboiAssetMovementHistory`
		WHERE reference_appendix = %s
		AND parenttype = 'oiAsset'
	""",
		decision,
		as_dict=False,
	)
	asset_names = [a[0] for a in asset_names]

	# Шукаємо активи через видаткові ордери
	issue_orders = frappe.get_all(
		"oiIssueOrder", filters={"decision": decision, "docstatus": 1}, pluck="name"
	)

	for io in issue_orders:
		items = frappe.get_all("oiIssueOrderItem", filters={"parent": io}, pluck="asset")
		asset_names.extend(items)

	# Унікальні активи
	asset_names = list(set(asset_names))

	if not asset_names:
		return {
			"assets": [],
			"decision_info": {
				"decision_number": decision_info.decision_number,
				"decision_date": decision_info.decision_date,
				"title": decision_info.title,
				"full_title": decision_info.full_title,
			},
			"summary": {"total_quantity": 0, "total_value": 0, "status_counts": {}},
		}

	# Отримуємо дані активів
	assets = frappe.get_all(
		"oiAsset",
		filters={"name": ("in", asset_names)},
		fields=[
			"name",
			"asset_name",
			"serial_no",
			"inventory_no",
			"status",
			"current_owner",
			"quantity",
			"cost",
			"total",
		],
		order_by="asset_name",
	)

	# Отримуємо назви організацій
	org_names = {}
	org_list = list(set([a.current_owner for a in assets if a.current_owner]))
	if org_list:
		orgs = frappe.get_all(
			"oiOrganization", filters={"name": ("in", org_list)}, fields=["name", "organization_name"]
		)
		org_names = {o.name: o.organization_name for o in orgs}

	# Отримуємо історію руху для кожного активу
	for asset in assets:
		asset["current_owner_name"] = org_names.get(asset.current_owner, asset.current_owner)
		asset["movement_history"] = get_asset_movement_history(asset.name)

	# Підсумки
	summary = {
		"total_quantity": sum(a.quantity or 0 for a in assets),
		"total_value": sum(a.total or 0 for a in assets),
		"status_counts": {},
	}

	for asset in assets:
		status = asset.status or "Невідомо"
		summary["status_counts"][status] = summary["status_counts"].get(status, 0) + 1

	return {
		"assets": assets,
		"decision_info": {
			"decision_number": decision_info.decision_number,
			"decision_date": decision_info.decision_date,
			"title": decision_info.title,
			"full_title": decision_info.full_title,
		},
		"summary": summary,
	}


def get_asset_movement_history(asset_name):
	"""
	Отримує історію руху активу з розшифровкою посилань.
	"""
	history = frappe.get_all(
		"oiAssetMovementHistory",
		filters={"parent": asset_name, "parenttype": "oiAsset"},
		fields=[
			"date",
			"movement_type",
			"from_source_type",
			"from_source_name",
			"to_organization",
			"reference_appendix",
		],
		order_by="date desc",
	)

	# Збираємо унікальні організації та рішення для отримання назв
	org_names = set()
	decision_names = set()

	for h in history:
		if h.to_organization:
			org_names.add(h.to_organization)
		if h.from_source_type == "oiOrganization" and h.from_source_name:
			org_names.add(h.from_source_name)
		if h.reference_appendix:
			decision_names.add(h.reference_appendix)

	# Отримуємо назви організацій
	org_titles = {}
	if org_names:
		orgs = frappe.get_all(
			"oiOrganization",
			filters={"name": ("in", list(org_names))},
			fields=["name", "organization_name"],
		)
		org_titles = {o.name: o.organization_name for o in orgs}

	# Отримуємо назви донорів
	donor_names = set()
	for h in history:
		if h.from_source_type == "oiDonor" and h.from_source_name:
			donor_names.add(h.from_source_name)

	donor_titles = {}
	if donor_names:
		donors = frappe.get_all(
			"oiDonor", filters={"name": ("in", list(donor_names))}, fields=["name", "donor_name"]
		)
		donor_titles = {d.name: d.donor_name for d in donors}

	# Отримуємо назви рішень
	decision_titles = {}
	if decision_names:
		decisions = frappe.get_all(
			"oiBasisDoc",
			filters={"name": ("in", list(decision_names))},
			fields=["name", "full_title", "title"],
		)
		decision_titles = {d.name: d.full_title or d.title for d in decisions}

	# Додаємо назви до історії
	for h in history:
		h["to_organization_name"] = org_titles.get(h.to_organization, h.to_organization)
		if h.from_source_type == "oiOrganization":
			h["from_source_name"] = org_titles.get(h.from_source_name, h.from_source_name)
		elif h.from_source_type == "oiDonor":
			h["from_source_name"] = donor_titles.get(h.from_source_name, h.from_source_name)
		h["reference_appendix_title"] = decision_titles.get(h.reference_appendix, "")

	return history
