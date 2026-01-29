# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class oiAgentAlert(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent: DF.Link
		alert_type: DF.Literal[
			"Офлайн", "Високе CPU", "Висока RAM", "Мало місця на диску", "Повернувся онлайн"
		]
		message: DF.SmallText | None
		resolved_at: DF.Datetime | None
		severity: DF.Literal["Info", "Warning", "Critical"]
		status: DF.Literal["Активне", "Вирішено", "Проігноровано"]
		threshold: DF.Float | None
		value: DF.Float | None
	# end: auto-generated types

	def before_save(self):
		if self.has_value_changed("status") and self.status in ["Вирішено", "Проігноровано"]:
			self.resolved_at = now_datetime()


def create_alert(
	agent_name: str,
	alert_type: str,
	severity: str = "Warning",
	message: str = None,
	value: float = None,
	threshold: float = None,
):
	"""
	Створює нове сповіщення для агента.

	Перевіряє чи немає активного сповіщення того ж типу.
	"""
	# Перевіряємо чи немає вже активного сповіщення
	existing = frappe.db.exists(
		"oiAgentAlert", {"agent": agent_name, "alert_type": alert_type, "status": "Активне"}
	)

	if existing:
		return None

	alert = frappe.get_doc(
		{
			"doctype": "oiAgentAlert",
			"agent": agent_name,
			"alert_type": alert_type,
			"severity": severity,
			"message": message,
			"value": value,
			"threshold": threshold,
			"status": "Активне",
		}
	)
	alert.insert(ignore_permissions=True)

	# Надсилаємо realtime сповіщення
	frappe.publish_realtime(
		"agent_alert",
		{"agent": agent_name, "alert_type": alert_type, "severity": severity, "message": message},
		after_commit=True,
	)

	return alert.name


def resolve_alerts(agent_name: str, alert_type: str = None):
	"""
	Закриває активні сповіщення для агента.

	Якщо alert_type не вказано - закриває всі.
	"""
	filters = {"agent": agent_name, "status": "Активне"}

	if alert_type:
		filters["alert_type"] = alert_type

	alerts = frappe.get_all("oiAgentAlert", filters=filters, pluck="name")

	for alert_name in alerts:
		frappe.db.set_value("oiAgentAlert", alert_name, {"status": "Вирішено", "resolved_at": now_datetime()})
