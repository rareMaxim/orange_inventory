# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

from datetime import date

import frappe
from frappe.model.document import Document


class oiAgentCertificate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent: DF.Link
		days_until_expiry: DF.Int
		file_name: DF.Data | None
		issuer_cn: DF.Data | None
		not_after: DF.Date | None
		not_before: DF.Date | None
		serial_number: DF.Data | None
		status: DF.Literal[
			"\u0414\u0456\u0439\u0441\u043d\u0438\u0439",
			"\u0421\u043a\u043e\u0440\u043e \u0437\u0430\u043a\u0456\u043d\u0447\u0443\u0454\u0442\u044c\u0441\u044f",
			"\u041f\u0440\u043e\u0442\u0435\u0440\u043c\u0456\u043d\u043e\u0432\u0430\u043d\u0438\u0439",
			"\u0429\u0435 \u043d\u0435 \u0434\u0456\u0439\u0441\u043d\u0438\u0439",
		]
		subject_cn: DF.Data
		thumbprint: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.update_status()

	def update_status(self):
		"""Оновлює статус та кількість днів до закінчення."""
		if not self.not_after:
			self.status = "Дійсний"
			self.days_until_expiry = None
			return

		today = date.today()
		not_after = self.not_after
		if isinstance(not_after, str):
			not_after = date.fromisoformat(not_after)

		delta = (not_after - today).days
		self.days_until_expiry = delta

		if self.not_before:
			not_before = self.not_before
			if isinstance(not_before, str):
				not_before = date.fromisoformat(not_before)
			if today < not_before:
				self.status = "Ще не дійсний"
				return

		if delta < 0:
			self.status = "Протермінований"
		elif delta <= 30:
			self.status = "Скоро закінчується"
		else:
			self.status = "Дійсний"
