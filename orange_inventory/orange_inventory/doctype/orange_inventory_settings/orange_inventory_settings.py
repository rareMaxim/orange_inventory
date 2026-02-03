# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import secrets

import frappe
from frappe.model.document import Document


class OrangeInventorySettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_link_agents: DF.Check
		command_signing_key: DF.Data | None
		company_name: DF.Data | None
		default_location: DF.Link | None
	# end: auto-generated types

	@frappe.whitelist()
	def generate_signing_key(self):
		"""Генерує новий ключ підпису команд."""
		new_key = secrets.token_hex(32)  # 64 символи hex
		self.command_signing_key = new_key
		self.save()
		return {"key": new_key}


@frappe.whitelist()
def get_command_signing_key():
	"""Повертає ключ підпису для використання в agent_api."""
	settings = frappe.get_single("Orange Inventory Settings")
	return settings.command_signing_key or ""
