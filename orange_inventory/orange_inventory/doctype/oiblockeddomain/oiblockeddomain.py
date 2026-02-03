# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class oiBlockedDomain(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		block_method: DF.Literal["hosts", "firewall", "both"]
		domain: DF.Data
		enabled: DF.Check
		include_subdomains: DF.Check
		notes: DF.SmallText | None
		reason: DF.Data | None
		redirect_ip: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_domain()
		self.validate_redirect_ip()

	def validate_domain(self):
		"""Перевіряє формат домену."""
		domain = self.domain.strip().lower()

		# Видаляємо протокол якщо є
		domain = re.sub(r"^https?://", "", domain)
		# Видаляємо шлях якщо є
		domain = domain.split("/")[0]
		# Видаляємо www. якщо є
		if domain.startswith("www."):
			domain = domain[4:]

		# Перевіряємо формат
		domain_pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$"
		if not re.match(domain_pattern, domain):
			frappe.throw(f"Невалідний формат домену: {domain}")

		self.domain = domain

	def validate_redirect_ip(self):
		"""Перевіряє формат IP адреси."""
		if not self.redirect_ip:
			self.redirect_ip = "0.0.0.0"
			return

		ip = self.redirect_ip.strip()
		# Перевіряємо формат IPv4
		ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
		if not re.match(ip_pattern, ip):
			frappe.throw(f"Невалідний формат IP адреси: {ip}")

		# Перевіряємо діапазон октетів
		for octet in ip.split("."):
			if int(octet) > 255:
				frappe.throw(f"Невалідний формат IP адреси: {ip}")

		self.redirect_ip = ip
