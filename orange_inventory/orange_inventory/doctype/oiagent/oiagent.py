# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAgent(Document):
	# Поля, які не відстежуються у версіях/коментарях
	_version_ignore_fields = ["last_seen"]

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_id: DF.Data
		agent_version: DF.Data | None
		asset: DF.Link | None
		asset_group: DF.Link | None
		bios_serial: DF.Data | None
		board_serial: DF.Data | None
		cpu_cores: DF.Int
		cpu_model: DF.Data | None
		first_seen: DF.Datetime | None
		hostname: DF.Data | None
		last_seen: DF.Datetime | None
		os: DF.Data | None
		os_edition: DF.Data | None
		ram_total_gb: DF.Float
		raw_data: DF.Code | None
		status: DF.Literal[
			"\u0410\u043a\u0442\u0438\u0432\u043d\u0438\u0439",
			"\u041d\u0435\u0430\u043a\u0442\u0438\u0432\u043d\u0438\u0439",
			"\u041e\u0444\u043b\u0430\u0439\u043d",
		]
		system_manufacturer: DF.Data | None
		system_model: DF.Data | None
		system_type: DF.Data | None
	# end: auto-generated types

	def save_version(self):
		"""Зберігає версію документа, виключаючи певні поля з відстеження."""
		old_doc = self.get_doc_before_save()
		if old_doc and self._version_ignore_fields:
			# Тимчасово встановлюємо старі значення для ігнорованих полів
			saved_values = {}
			for field in self._version_ignore_fields:
				if hasattr(self, field):
					saved_values[field] = getattr(self, field)
					setattr(self, field, getattr(old_doc, field, None))

			# Викликаємо оригінальний метод
			super().save_version()

			# Відновлюємо значення
			for field, value in saved_values.items():
				setattr(self, field, value)
		else:
			super().save_version()

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
