# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiSoftwareCatalog(Document):
	def validate(self):
		# Нормалізуємо назву ПЗ для кращого пошуку
		if self.software_name:
			self.software_name = self.software_name.strip()

	def get_installations_count(self) -> int:
		"""Повертає кількість встановлень цього ПЗ на агентах."""
		return frappe.db.count("oiAgentSoftware", filters={"catalog_entry": self.name})
