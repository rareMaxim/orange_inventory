# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAlertRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		alert_type: DF.Literal[
			"Офлайн", "Високе CPU", "Висока RAM", "Мало місця на диску", "Застаріла версія"
		]
		cooldown_minutes: DF.Int
		description: DF.SmallText | None
		duration_minutes: DF.Int
		email_recipients: DF.SmallText | None
		enabled: DF.Check
		metric: DF.Literal[
			"cpu_usage_percent",
			"ram_usage_percent",
			"disk_usage_percent",
			"agent_offline_minutes",
			"agent_version",
		]
		operator: DF.Literal[">", ">=", "<", "<=", "=", "!="]
		rule_name: DF.Data
		send_email: DF.Check
		send_system_notification: DF.Check
		severity: DF.Literal["Info", "Warning", "Critical"]
		threshold_value: DF.Float
	# end: auto-generated types

	def validate(self):
		self._validate_threshold()
		self._validate_email_recipients()

	def _validate_threshold(self):
		"""Перевіряємо коректність порогового значення для метрики."""
		if self.metric in ["cpu_usage_percent", "ram_usage_percent", "disk_usage_percent"]:
			if self.threshold_value < 0 or self.threshold_value > 100:
				frappe.throw("Порогове значення для відсотків має бути від 0 до 100")
		elif self.metric == "agent_offline_minutes":
			if self.threshold_value < 1:
				frappe.throw("Час офлайн має бути не менше 1 хвилини")

	def _validate_email_recipients(self):
		"""Перевіряємо email адреси."""
		if self.send_email and not self.email_recipients:
			frappe.throw("Вкажіть email отримувачів або вимкніть надсилання email")
