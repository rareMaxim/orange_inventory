# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet


class oiAssetGroup(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_count: DF.Int
		alert_email_recipients: DF.SmallText | None
		asset_count: DF.Int
		color: DF.Color | None
		default_location: DF.Link | None
		description: DF.SmallText | None
		group_name: DF.Data
		icon: DF.Icon | None
		is_active: DF.Check
		lft: DF.Int
		parent_group: DF.Link | None
		responsible_user: DF.Link | None
		rgt: DF.Int
	# end: auto-generated types

	nsm_parent_field = "parent_group"

	def on_update(self):
		super().on_update()
		self.update_stats()

	def update_stats(self):
		"""Оновлює статистику групи."""
		# Рахуємо агентів
		try:
			agent_count = frappe.db.count("oiAgent", {"asset_group": self.name})
		except Exception:
			agent_count = 0

		# Рахуємо активи (поле може не існувати)
		try:
			asset_count = frappe.db.count("oiAsset", {"asset_group": self.name})
		except Exception:
			asset_count = 0

		# Оновлюємо без тригера on_update
		frappe.db.set_value(
			"oiAssetGroup",
			self.name,
			{"agent_count": agent_count, "asset_count": asset_count},
			update_modified=False,
		)

	@staticmethod
	def update_all_stats():
		"""Оновлює статистику для всіх груп."""
		groups = frappe.get_all("oiAssetGroup", pluck="name")
		for group_name in groups:
			group = frappe.get_doc("oiAssetGroup", group_name)
			group.update_stats()


def update_group_stats(doc, method):
	"""Hook для оновлення статистики групи при зміні агента/активу."""
	if doc.asset_group:
		try:
			group = frappe.get_doc("oiAssetGroup", doc.asset_group)
			group.update_stats()
		except frappe.DoesNotExistError:
			pass

	# Якщо група змінилась - оновлюємо стару групу
	if hasattr(doc, "_doc_before_save") and doc._doc_before_save:
		old_group = doc._doc_before_save.get("asset_group")
		if old_group and old_group != doc.asset_group:
			try:
				old_group_doc = frappe.get_doc("oiAssetGroup", old_group)
				old_group_doc.update_stats()
			except frappe.DoesNotExistError:
				pass
