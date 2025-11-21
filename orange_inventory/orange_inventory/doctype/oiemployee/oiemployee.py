# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiEmployee(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		birthday: DF.Date | None
		department: DF.Link | None
		enabled: DF.Check
		full_name: DF.Data
		organization: DF.Link | None
		phone: DF.Data | None
		position: DF.Data | None
		status: DF.Literal[
			"\u041f\u0440\u0430\u0446\u044e\u0454 \u043e\u0447\u043d\u043e",
			"\u041f\u0440\u0430\u0446\u044e\u0454 \u0432\u0456\u0434\u0434\u0430\u043b\u0435\u043d\u043e",
			"\u0417\u0432\u0456\u043b\u044c\u043d\u0435\u043d\u043e",
			"\u0421\u043b\u0443\u0436\u0438\u0442\u044c",
			"\u041f\u0440\u043e\u0441\u0442\u043e\u0439",
			"\u0414\u0435\u043a\u0440\u0435\u0442",
			"\u041d\u0435 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0438\u0439/\u043d\u0435 \u043f\u0440\u0430\u0446\u044e\u0454",
		]
		user: DF.Link | None
	# end: auto-generated types

	pass


@frappe.whitelist()
def get_department_query(doctype, txt, searchfield, start, page_len, filters):
	"""
	Filter departments (organizations) to show only those that are descendants
	of the selected organization in the tree structure.
	If no organization is selected, show all organizations.
	"""
	if not filters or not filters.get("organization"):
		# If no organization selected, show all organizations
		return frappe.db.sql(
			"""
			SELECT name, organization_name, tax_code
			FROM `taboiOrganization`
			WHERE (organization_name LIKE %(txt)s OR tax_code LIKE %(txt)s OR name LIKE %(txt)s)
			ORDER BY organization_name
			LIMIT %(start)s, %(page_len)s
			""",
			{"txt": f"%{txt}%", "start": start, "page_len": page_len},
			as_dict=False,
		)

	# Get the parent organization
	parent_org = filters.get("organization")

	# Get the lft and rgt values of the parent organization for tree filtering
	parent_data = frappe.db.get_value("oiOrganization", parent_org, ["lft", "rgt"], as_dict=True)

	if not parent_data:
		return []

	# Return organizations that are descendants (within the lft/rgt range)
	# Including parent organization itself by using >= and <=
	return frappe.db.sql(
		"""
		SELECT name, organization_name, tax_code
		FROM `taboiOrganization`
		WHERE lft > %(lft)s
			AND rgt < %(rgt)s
			AND (organization_name LIKE %(txt)s OR tax_code LIKE %(txt)s OR name LIKE %(txt)s)
		ORDER BY lft
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"lft": parent_data.lft,
			"rgt": parent_data.rgt,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
		as_dict=False,
	)


@frappe.whitelist()
def create_label_batch_for_employee(employee):
	"""
	Create an oiAssetLabelBatch document with all assets
	where responsible_employee equals the given employee.

	Args:
	        employee: Name of the oiEmployee document

	Returns:
	        Name of the created oiAssetLabelBatch document
	"""
	# Get employee details
	emp_doc = frappe.get_doc("oiEmployee", employee)

	# Find all assets for this employee
	assets = frappe.get_all(
		"oiAsset",
		filters={
			"responsible_employee": employee,
			"docstatus": ["<", 2],  # Not cancelled
		},
		fields=["name", "asset_name", "inventory_no", "serial_no"],
		order_by="inventory_no",
	)

	if not assets:
		frappe.msgprint(f"Не знайдено активів для МВО: {emp_doc.full_name}")
		return None

	# Create new AssetLabelBatch
	batch = frappe.new_doc("oiAssetLabelBatch")
	batch.title = f"Етикетки для {emp_doc.full_name}"

	# Set default print settings
	batch.columns = 3
	batch.label_width_mm = 66
	batch.label_height_mm = 42
	batch.label_gap_mm = 0
	batch.page_margin_mm = 5
	batch.font_px = 11
	batch.qr_size_mm = 15

	# Enable common fields
	batch.show_inventory_no = 1
	batch.show_mvo = 1
	batch.show_organization = 1
	batch.show_location = 1

	# Add all assets to the batch
	for asset in assets:
		batch.append("items", {"asset": asset.name, "copies": 1})

	# Save the document
	batch.insert()

	frappe.msgprint(
		f"Створено пакет етикеток з {len(assets)} активами для МВО: {emp_doc.full_name}",
		title="Успішно створено",
	)

	return batch.name
