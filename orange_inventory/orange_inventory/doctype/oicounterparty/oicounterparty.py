# Copyright (c) 2025, IT MLT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiCounterparty(Document):
	def validate(self):
		"""Validate counterparty data"""
		self.validate_identifiers()
		self.set_short_name()

	def validate_identifiers(self):
		"""Ensure either EDRPOU or IPN is provided"""
		if self.counterparty_type in ["Юридична особа", "Державна установа", "Міжнародна організація"]:
			if not self.edrpou:
				frappe.msgprint("Рекомендується вказати ЄДРПОУ для юридичної особи")
		elif self.counterparty_type in ["Фізична особа-підприємець", "Фізична особа"]:
			if not self.ipn and not self.edrpou:
				frappe.msgprint("Рекомендується вказати ІПН або ЄДРПОУ")

	def set_short_name(self):
		"""Set short name if not provided"""
		if not self.counterparty_short_name:
			# Extract short name from full name (e.g., ТОВ "Компанія" -> Компанія)
			self.counterparty_short_name = self.counterparty_name
