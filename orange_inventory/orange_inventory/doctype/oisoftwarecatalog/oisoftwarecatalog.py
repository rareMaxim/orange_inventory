# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiSoftwareCatalog(Document):
	def validate(self):
		# Нормалізуємо назву ПЗ для кращого пошуку
		if self.software_name:
			self.software_name = self.software_name.strip()

	def update_installations_count(self):
		"""Оновлює кількість встановлень цього ПЗ на агентах."""
		count = frappe.db.count("oiAgentSoftware", filters={"catalog_entry": self.name})
		if self.installations_count != count:
			frappe.db.set_value(
				"oiSoftwareCatalog", self.name, "installations_count", count, update_modified=False
			)
