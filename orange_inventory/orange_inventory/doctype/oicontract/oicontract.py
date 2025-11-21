# Copyright (c) 2025, IT MLT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiContract(Document):
	def validate(self):
		"""Validate contract data and calculate totals"""
		self.calculate_total_amount()
		self.validate_dates()

	def calculate_total_amount(self):
		"""Calculate total amount from contract items"""
		total = 0
		for item in self.contract_items:
			if item.quantity and item.unit_price:
				item.total_price = item.quantity * item.unit_price
				total += item.total_price
		self.total_amount = total

	def validate_dates(self):
		"""Validate that end_date is after start_date"""
		if self.start_date and self.end_date:
			if self.end_date < self.start_date:
				frappe.throw("Дата закінчення не може бути раніше дати початку")
