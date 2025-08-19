# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiNetworkPort(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset: DF.Link | None
		connected_asset: DF.Link | None
		connection: DF.Link | None
		is_wan_connection: DF.Check
		notes: DF.Text | None
		port_name: DF.Data | None
		port_type: DF.Data | None
	# end: auto-generated types

	def on_update(self):
		"""
		Синхронізує з'єднання між портами після збереження.
		"""
		print(f"Updating network port: {self.name}")
		# Перевіряємо, чи змінилося поле 'connection'
		if self.has_value_changed("connection"):
			old_connection = self.get_doc_before_save()

			# Сценарій 1: Старе з'єднання було розірвано
			if old_connection and old_connection.connection:
				print(f"Old connection: {old_connection.connection}")
				# Завантажуємо старий підключений порт і розриваємо з'єднання з ним
				old_target_port = frappe.get_doc("oiNetworkPort", old_connection.connection)
				if old_target_port.connection == self.name:
					old_target_port.connection = None
					old_target_port.connected_asset = None
					old_target_port.save(ignore_permissions=True)

			# Сценарій 2: Встановлено нове з'єднання
			if self.connection:
				print(f"New connection: {self.connection}")
				# Завантажуємо новий цільовий порт
				target_port = frappe.get_doc("oiNetworkPort", self.connection)
				# Якщо він ще не підключений до нас, встановлюємо двосторонній зв'язок
				if target_port.connection != self.name:
					target_port.connection = self.name
					target_port.connected_asset = self.asset
					target_port.save(ignore_permissions=True)
