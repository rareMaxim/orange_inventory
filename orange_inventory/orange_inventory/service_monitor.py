# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Service Monitor для Orange Inventory.
Перевіряє стан служб Windows та створює алерти.
"""

import json

import frappe
from frappe.utils import add_to_date, now_datetime


def check_services():
	"""
	Перевіряє стан служб для всіх агентів.
	Викликається scheduled job.
	"""
	# Отримуємо активні правила моніторингу служб
	monitors = frappe.get_all(
		"oiServiceMonitor",
		filters={"enabled": 1},
		fields=[
			"name",
			"service_name",
			"display_name",
			"expected_state",
			"alert_on_stop",
			"check_interval_minutes",
		],
	)

	if not monitors:
		return

	# Отримуємо всіх активних агентів
	agents = frappe.get_all(
		"oiAgent",
		filters={"status": ["!=", ""]},
		fields=["name", "hostname"],
	)

	for monitor in monitors:
		for agent in agents:
			try:
				check_service_for_agent(monitor, agent)
			except Exception as e:
				frappe.log_error(
					message=f"Помилка перевірки служби {monitor.service_name} для агента {agent.name}: {str(e)}",
					title="Service Monitor Error",
				)


def check_service_for_agent(monitor, agent):
	"""Перевіряє стан конкретної служби для агента."""
	# Перевіряємо cooldown
	if is_in_cooldown(monitor, agent.name):
		return

	# Отримуємо останній snapshot з даними про служби
	snapshot = frappe.get_all(
		"oiAgentSnapshot",
		filters={"agent": agent.name},
		fields=["services_status"],
		order_by="timestamp desc",
		limit=1,
	)

	if not snapshot or not snapshot[0].services_status:
		return

	# Парсимо дані про служби
	try:
		services = json.loads(snapshot[0].services_status)
	except (json.JSONDecodeError, TypeError):
		return

	if not isinstance(services, list):
		return

	# Шукаємо потрібну службу
	service_found = False
	service_state = None

	for svc in services:
		if svc.get("name", "").lower() == monitor.service_name.lower():
			service_found = True
			service_state = svc.get("state", "Unknown")
			break

	# Перевіряємо стан
	if not service_found:
		# Служба не знайдена на цьому агенті - можливо вона там не встановлена
		return

	expected_state = monitor.expected_state or "Running"

	# Якщо стан не відповідає очікуваному і потрібно створити алерт
	if monitor.alert_on_stop and service_state != expected_state:
		create_service_alert(monitor, agent, service_state, expected_state)


def is_in_cooldown(monitor, agent_name):
	"""Перевіряє чи агент у періоді cooldown для цієї служби."""
	cooldown_minutes = monitor.check_interval_minutes or 15

	# Шукаємо останній алерт для цієї служби і агента
	last_alert = frappe.get_all(
		"oiAgentAlert",
		filters={
			"agent": agent_name,
			"alert_type": "Служба зупинена",
			"message": ["like", f"%{monitor.service_name}%"],
			"creation": [">=", add_to_date(now_datetime(), minutes=-cooldown_minutes)],
		},
		limit=1,
	)

	return bool(last_alert)


def create_service_alert(monitor, agent, current_state, expected_state):
	"""Створює алерт про проблему зі службою."""
	display_name = monitor.display_name or monitor.service_name
	hostname = agent.hostname or agent.name

	message = f"Служба '{display_name}' на {hostname}: стан '{current_state}' (очікувався '{expected_state}')"

	alert = frappe.get_doc(
		{
			"doctype": "oiAgentAlert",
			"agent": agent.name,
			"alert_type": "Служба зупинена",
			"severity": "Warning",
			"status": "Активне",
			"message": message,
		}
	)
	alert.insert(ignore_permissions=True)

	# Надсилаємо системне сповіщення
	send_service_notification(alert, monitor, agent)

	frappe.db.commit()


def send_service_notification(alert, monitor, agent):
	"""Надсилає системне сповіщення про службу."""
	users = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["System Manager", "Maintenance Manager"]]},
		fields=["parent"],
		distinct=True,
	)

	for user in users:
		try:
			frappe.publish_realtime(event="msgprint", message=f"⚠️ {alert.message}", user=user.parent)

			notification = frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": f"🔧 Служба: {monitor.display_name or monitor.service_name}",
					"for_user": user.parent,
					"type": "Alert",
					"document_type": "oiAgentAlert",
					"document_name": alert.name,
					"email_content": alert.message,
				}
			)
			notification.insert(ignore_permissions=True)
		except Exception:
			pass


def auto_resolve_service_alerts():
	"""
	Автоматично вирішує алерти про служби, коли служба знову працює.
	"""
	# Отримуємо активні алерти про служби
	active_alerts = frappe.get_all(
		"oiAgentAlert",
		filters={"status": "Активне", "alert_type": "Служба зупинена"},
		fields=["name", "agent", "message"],
	)

	for alert in active_alerts:
		try:
			# Витягуємо назву служби з повідомлення
			# Формат: "Служба 'ServiceName' на hostname: ..."
			import re

			match = re.search(r"Служба '([^']+)'", alert.message)
			if not match:
				continue

			service_name = match.group(1)

			# Шукаємо monitor для цієї служби
			monitor = frappe.get_all(
				"oiServiceMonitor",
				filters={"display_name": service_name},
				fields=["service_name", "expected_state"],
				limit=1,
			)

			if not monitor:
				# Спробуємо по service_name
				monitor = frappe.get_all(
					"oiServiceMonitor",
					filters={"service_name": service_name},
					fields=["service_name", "expected_state"],
					limit=1,
				)

			if not monitor:
				continue

			monitor = monitor[0]

			# Отримуємо останній snapshot
			snapshot = frappe.get_all(
				"oiAgentSnapshot",
				filters={"agent": alert.agent},
				fields=["services_status"],
				order_by="timestamp desc",
				limit=1,
			)

			if not snapshot or not snapshot[0].services_status:
				continue

			services = json.loads(snapshot[0].services_status)

			# Шукаємо службу
			for svc in services:
				if svc.get("name", "").lower() == monitor.service_name.lower():
					if svc.get("state") == (monitor.expected_state or "Running"):
						# Служба знову працює - закриваємо алерт
						frappe.db.set_value(
							"oiAgentAlert",
							alert.name,
							{"status": "Вирішено", "resolved_at": now_datetime()},
						)
					break

		except Exception as e:
			frappe.log_error(
				message=f"Помилка авто-вирішення алерту служби {alert.name}: {str(e)}",
				title="Service Alert Auto Resolve Error",
			)

	frappe.db.commit()
