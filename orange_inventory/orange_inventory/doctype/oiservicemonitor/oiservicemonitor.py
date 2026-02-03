# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiServiceMonitor(Document):
	def validate(self):
		# Встановлюємо display_name якщо порожній
		if not self.display_name:
			self.display_name = self.service_name
