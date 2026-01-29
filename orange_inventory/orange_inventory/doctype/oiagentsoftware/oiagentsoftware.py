# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class oiAgentSoftware(Document):
	def validate(self):
		self.check_compliance()

	def check_compliance(self):
		"""Перевіряє відповідність ПЗ каталогу."""
		self.last_checked = now_datetime()

		# Шукаємо в каталозі по точній назві або частковому збігу
		catalog_entry = self._find_catalog_entry()

		if catalog_entry:
			self.catalog_entry = catalog_entry.name

			if catalog_entry.is_allowed:
				self.compliance_status = "Дозволено"
				# Перевіряємо версію
				self._check_version(catalog_entry)
			else:
				self.compliance_status = "Заборонено"
				self.needs_update = 0
				self.is_outdated = 0
		else:
			self.catalog_entry = None
			self.compliance_status = "Не в каталозі"
			self.needs_update = 0
			self.is_outdated = 0

	def _find_catalog_entry(self):
		"""Шукає відповідний запис у каталозі."""
		if not self.software_name:
			return None

		# Спочатку точний збіг
		entry = frappe.db.get_value(
			"oiSoftwareCatalog",
			{"software_name": self.software_name},
			["name", "is_allowed", "min_version", "max_version"],
			as_dict=True,
		)

		if entry:
			return entry

		# Частковий збіг (ПЗ може мати суфікси типу "x64", "x86", "(64-bit)")
		software_name_clean = re.sub(
			r"\s*\(?(x64|x86|64-bit|32-bit)\)?", "", self.software_name, flags=re.IGNORECASE
		).strip()

		entries = frappe.get_all(
			"oiSoftwareCatalog",
			filters={},
			fields=["name", "software_name", "is_allowed", "min_version", "max_version"],
		)

		for e in entries:
			catalog_clean = re.sub(
				r"\s*\(?(x64|x86|64-bit|32-bit)\)?", "", e.software_name, flags=re.IGNORECASE
			).strip()
			if catalog_clean.lower() == software_name_clean.lower():
				return e
			# Також перевіряємо чи назва з агента містить назву з каталогу
			if e.software_name.lower() in self.software_name.lower():
				return e

		return None

	def _check_version(self, catalog_entry):
		"""Перевіряє чи версія ПЗ відповідає вимогам."""
		if not self.version:
			self.needs_update = 0
			self.is_outdated = 0
			return

		min_version = catalog_entry.get("min_version")
		max_version = catalog_entry.get("max_version")

		if min_version and self._compare_versions(self.version, min_version) < 0:
			self.needs_update = 1
			self.is_outdated = 1
		else:
			self.needs_update = 0
			self.is_outdated = 0

		# Перевірка максимальної версії (якщо вказана)
		if max_version and self._compare_versions(self.version, max_version) > 0:
			self.compliance_status = "Заборонено"

	def _compare_versions(self, v1: str, v2: str) -> int:
		"""
		Порівнює дві версії.

		Returns:
		        -1 якщо v1 < v2
		        0 якщо v1 == v2
		        1 якщо v1 > v2
		"""

		def normalize(v):
			# Видаляємо все крім цифр і крапок
			v = re.sub(r"[^\d.]", ".", v)
			# Розбиваємо на частини
			parts = [int(x) for x in v.split(".") if x.isdigit()]
			return parts if parts else [0]

		parts1 = normalize(v1)
		parts2 = normalize(v2)

		# Вирівнюємо довжину
		max_len = max(len(parts1), len(parts2))
		parts1.extend([0] * (max_len - len(parts1)))
		parts2.extend([0] * (max_len - len(parts2)))

		for p1, p2 in zip(parts1, parts2, strict=False):
			if p1 < p2:
				return -1
			elif p1 > p2:
				return 1

		return 0
