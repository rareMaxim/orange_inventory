# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import today


class oiDecommissioningAct(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oidecommissioningitem.oidecommissioningitem import (
			oiDecommissioningItem,
		)

		correspondence: DF.Link | None
		decision: DF.Link | None
		decommission_date: DF.Date
		items: DF.Table[oiDecommissioningItem]
	# end: auto-generated types

	def on_submit(self):
		"""
		При затвердженні 'Акту списання' оновлює статус активів.
		"""
		for item in self.items:
			# Завантажуємо документ 'oiAsset' за посиланням з рядка
			asset_doc = frappe.get_doc("oiAsset", item.asset)

			# Оновлюємо статус та обнуляємо кількість
			asset_doc.status = "Списано"
			asset_doc.quantity = 0

			# Додаємо запис в історію руху
			asset_doc.append(
				"movement_history",
				{
					"date": self.decommission_date,
					"movement_type": "Списання",
					# При списанні актив "іде в нікуди", тому поля from/to пусті
					"reference_appendix": self.decision,
				},
			)

			# Зберігаємо зміни в документі активу
			asset_doc.save()


# =========================
# Public API (called from JS)
# =========================
@frappe.whitelist()
def create_correspondence_for_act(act_name: str) -> str:
	"""Створює вихідний oiCorrespondence із даних oiDecommissioningAct,
	зберігає посилання в полі `correspondence` акта і повертає name кореспонденції.
	Жодних PDF не генеруємо і не прикріплюємо.
	"""
	if not act_name:
		frappe.throw(_("Не передано назву Акта списання"))

	act = frappe.get_doc("oiDecommissioningAct", act_name)

	if getattr(act, "correspondence", None):
		return act.correspondence

	reason = _basis_reason_from_act(act)
	lines = []
	for i, row in enumerate(getattr(act, "items", []) or [], start=1):
		asset_name = (
			getattr(row, "asset_name", None)
			or frappe.db.get_value("oiAsset", row.asset, "asset_name")
			or row.asset
			or ""
		)
		inv = (
			getattr(row, "inventory_no", None)
			or frappe.db.get_value("oiAsset", row.asset, "inventory_no")
			or ""
		)
		if asset_name or inv:
			lines.append(f"{i}. {asset_name} (інв. № {inv})")

	summary = "Щодо списання матеріальних цінностей.\n"
	if reason:
		summary += f"Підстава/причина: {reason}\n"
	if lines:
		summary += "Перелік:\n" + "\n".join(lines)

	title = _make_title_for_correspondence(act, fallback="Службовий лист щодо списання")

	corr = frappe.get_doc(
		{
			"doctype": "oiCorrespondence",
			"correspondence_type": "Вихідний",
			"registration_date": today(),
			"title": title[:140],
			"summary": summary,
		}
	).insert()

	if _has_field("oiDecommissioningAct", "correspondence"):
		act.db_set("correspondence", corr.name)

	frappe.db.commit()
	return corr.name


# ==== helpers ====
def _make_title_for_correspondence(act, fallback: str) -> str:
	d = getattr(act, "decommission_date", None) or today()
	return (
		f"Щодо списання (Акт {act.name} від {frappe.format_value(d, {'fieldtype':'Date'})})"
		if getattr(act, "name", None)
		else fallback
	)


def _basis_reason_from_act(act) -> str:
	basis_name = getattr(act, "decision", None)
	if basis_name and frappe.db.exists("oiBasisDoc", basis_name):
		basis = (
			frappe.db.get_value("oiBasisDoc", basis_name, ["reason", "subject", "description"], as_dict=True)
			or {}
		)
		return basis.get("reason") or basis.get("subject") or basis.get("description") or ""
	return ""


def _has_field(doctype: str, fieldname: str) -> bool:
	return bool(frappe.get_meta(doctype).get_field(fieldname))
