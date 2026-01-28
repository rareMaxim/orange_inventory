# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHromadaImportLog(Document):
	def before_save(self):
		# Автоматично заповнюємо поля
		if not self.imported_by:
			self.imported_by = frappe.session.user

		# Формуємо відображення періоду
		if self.year and self.quarter:
			self.period_display = f"{self.year}-{self.quarter}"

		# Підраховуємо кількість змін
		self.total_changes = len([c for c in (self.changes or []) if c.old_value != c.new_value])

	def before_insert(self):
		if not self.import_date:
			self.import_date = frappe.utils.now_datetime()
