# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAgent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_id: DF.Data
		asset: DF.Link | None
		bios_serial: DF.Data | None
		board_serial: DF.Data | None
		cpu_cores: DF.Int | None
		cpu_model: DF.Data | None
		first_seen: DF.Datetime | None
		hostname: DF.Data | None
		last_seen: DF.Datetime | None
		os: DF.Data | None
		ram_total_gb: DF.Float | None
		raw_data: DF.Code | None
		status: DF.Literal["Активний", "Неактивний", "Офлайн"]
		system_manufacturer: DF.Data | None
		system_model: DF.Data | None
		system_type: DF.Data | None
	# end: auto-generated types

	def on_update(self):
		"""Синхронізує зв'язок з активом у обидва боки."""
		self._sync_asset_link()

	def _sync_asset_link(self):
		"""Оновлює зв'язок agent у прив'язаному активі."""
		# Отримуємо попереднє значення asset
		old_doc = self.get_doc_before_save()
		old_asset = old_doc.asset if old_doc else None

		# Якщо asset змінився
		if self.asset != old_asset:
			# Якщо був старий asset - очищаємо його agent поле
			if old_asset:
				frappe.db.set_value("oiAsset", old_asset, "agent", None)

			# Якщо є новий asset - встановлюємо agent
			if self.asset:
				frappe.db.set_value("oiAsset", self.asset, "agent", self.name)
