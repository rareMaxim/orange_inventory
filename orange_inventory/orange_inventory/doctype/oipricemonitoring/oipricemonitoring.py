# Copyright (c) 2025, IT MLT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiPriceMonitoring(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oipricemonitoringitem.oipricemonitoringitem import (
			oiPriceMonitoringItem,
		)

		approved_by: DF.Link | None
		completion_date: DF.Date | None
		expected_contract_type: DF.Link | None
		expected_counterparty: DF.Link | None
		monitoring_date: DF.Date
		monitoring_items: DF.Table[oiPriceMonitoringItem]
		monitoring_purpose: DF.TextEditor | None
		recommendations: DF.TextEditor | None
		responsible_person: DF.Link | None
		status: DF.Literal[
			"\u0412 \u043f\u0440\u043e\u0446\u0435\u0441\u0456",
			"\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e",
			"\u0417\u0430\u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u043e",
		]
		summary: DF.TextEditor | None
	# end: auto-generated types

	def validate(self):
		"""Validate monitoring data and calculate price analysis"""
		self.calculate_price_analysis()

	def calculate_price_analysis(self):
		"""Calculate min, max, avg prices for each item"""
		for item in self.monitoring_items:
			prices = []

			# Collect all prices
			if item.price_1:
				prices.append(item.price_1)
			if item.price_2:
				prices.append(item.price_2)
			if item.price_3:
				prices.append(item.price_3)

			# Calculate statistics if we have prices
			if prices:
				item.min_price = min(prices)
				item.max_price = max(prices)
				item.avg_price = sum(prices) / len(prices)

	def on_submit(self):
		"""Actions to perform when monitoring is completed"""
		self.status = "Завершено"
		self.completion_date = frappe.utils.today()

	@frappe.whitelist()
	def create_contract_from_monitoring(self):
		"""Create a contract based on this price monitoring"""
		# Check if contract already exists
		existing = frappe.db.exists("oiContract", {"price_monitoring": self.name})
		if existing:
			frappe.throw(f"Договір {existing} вже створено на основі цього моніторингу")

		# Generate temporary contract number based on monitoring number
		temp_contract_number = f"ПРОЕКТ-{self.name}"

		# Create new contract
		contract = frappe.get_doc(
			{
				"doctype": "oiContract",
				"price_monitoring": self.name,
				"contract_number": temp_contract_number,
				"counterparty": self.expected_counterparty,
				"contract_type": self.expected_contract_type,
				"contract_date": frappe.utils.today(),
				"status": "Чернетка",
			}
		)

		# Add items from monitoring to contract
		for item in self.monitoring_items:
			contract.append(
				"contract_items",
				{
					"item_name": item.item_name,
					"hardware_model": item.hardware_model,
					"quantity": item.quantity or 1,
					"unit_price": item.avg_price or item.min_price or 0,
					"description": item.notes,
				},
			)

		contract.insert()

		frappe.msgprint(
			f"Створено договір: <a href='/app/oicontract/{contract.name}'>{contract.name}</a>",
			title="Договір створено",
			indicator="green",
		)

		return contract.name
