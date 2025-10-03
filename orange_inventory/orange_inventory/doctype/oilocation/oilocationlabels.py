import frappe
from frappe.utils import now


@frappe.whitelist()
def create_label_batch_from_location(location: str):
	"""Створює oiAssetLabelBatch з усіма активами локації.
	К-сть копій = oiAsset.quantity (мінімум 1).
	"""
	loc = frappe.get_doc("oiLocation", location)

	assets = frappe.get_all(
		"oiAsset",
		filters={"location": location},
		fields=["name", "asset_name", "inventory_no", "serial_no", "quantity"],
		order_by="asset_name asc",
	)
	if not assets:
		frappe.throw("У цій локації немає активів.")

	batch = frappe.get_doc(
		{
			"doctype": "oiAssetLabelBatch",
			"title": f"{loc.building}-{loc.room} ({now().split(' ')[0]})",
			# Параметри шаблону беруться з DocType oiAssetLabelBatch
			# (колонки, розміри, поля тощо – користувач відредагує за потреби)
			"items": [],
		}
	)

	for a in assets:
		copies = int(a.get("quantity") or 1)
		batch.append(
			"items",
			{
				"asset": a["name"],
				# override* залишаємо порожніми — у друці використаємо значення з oiAsset
				"copies": copies,
			},
		)

	batch.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": batch.name}
