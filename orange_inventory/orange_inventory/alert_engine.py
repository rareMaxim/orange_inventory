# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Alert Engine для Orange Inventory.
Перевіряє правила алертів та створює сповіщення.
"""

import json
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, now_datetime, time_diff_in_seconds


def check_all_alerts():
	"""
	Головна функція перевірки всіх алертів.
	Викликається scheduled job.
	"""
	# Отримуємо всі активні правила
	rules = frappe.get_all("oiAlertRule", filters={"enabled": 1}, fields=["*"])

	if not rules:
		return

	# Отримуємо всіх активних агентів
	agents = frappe.get_all(
		"oiAgent",
		filters={"status": ["!=", ""]},
		fields=["name", "hostname", "last_seen", "status", "agent_version"],
	)

	for rule in rules:
		try:
			check_rule(rule, agents)
		except Exception as e:
			frappe.log_error(
				message=f"Помилка перевірки правила {rule.rule_name}: {str(e)}", title="Alert Engine Error"
			)


def check_rule(rule, agents):
	"""Перевіряє одне правило для всіх агентів."""
	for agent in agents:
		try:
			# Перевіряємо cooldown - чи не було нещодавно алерту
			if is_in_cooldown(rule, agent.name):
				continue

			# Отримуємо значення метрики
			metric_value = get_metric_value(rule.metric, agent)
			if metric_value is None:
				continue

			# Перевіряємо умову
			if evaluate_condition(metric_value, rule.operator, rule.threshold_value):
				# Умова спрацювала - створюємо алерт
				create_alert(rule, agent, metric_value)

		except Exception as e:
			frappe.log_error(
				message=f"Помилка перевірки агента {agent.name} для правила {rule.rule_name}: {str(e)}",
				title="Alert Check Error",
			)


def get_metric_value(metric, agent):
	"""Отримує значення метрики для агента."""
	if metric == "agent_offline_minutes":
		if not agent.last_seen:
			return None
		# Рахуємо скільки хвилин агент офлайн
		last_seen = agent.last_seen
		if isinstance(last_seen, str):
			last_seen = datetime.fromisoformat(last_seen)
		diff = now_datetime() - last_seen
		return diff.total_seconds() / 60

	elif metric == "agent_version":
		return agent.agent_version

	elif metric in ["cpu_usage_percent", "ram_usage_percent", "disk_usage_percent"]:
		# Отримуємо останній snapshot
		snapshot = frappe.get_all(
			"oiAgentSnapshot",
			filters={"agent": agent.name},
			fields=["cpu_usage", "ram_usage", "disk_usage"],
			order_by="timestamp desc",
			limit=1,
		)

		if not snapshot:
			return None

		snap = snapshot[0]

		if metric == "cpu_usage_percent":
			return snap.cpu_usage
		elif metric == "ram_usage_percent":
			return snap.ram_usage
		elif metric == "disk_usage_percent":
			# Беремо максимальне використання серед дисків
			if snap.disk_usage:
				try:
					disks = (
						json.loads(snap.disk_usage) if isinstance(snap.disk_usage, str) else snap.disk_usage
					)
					if isinstance(disks, list) and disks:
						return max(d.get("used_percent", 0) for d in disks)
				except (json.JSONDecodeError, TypeError):
					pass
			return None

	return None


def evaluate_condition(value, operator, threshold):
	"""Оцінює умову порівняння."""
	if value is None:
		return False

	try:
		value = flt(value)
		threshold = flt(threshold)
	except (ValueError, TypeError):
		# Для рядкових порівнянь (версія)
		pass

	operators = {
		">": lambda v, t: v > t,
		">=": lambda v, t: v >= t,
		"<": lambda v, t: v < t,
		"<=": lambda v, t: v <= t,
		"=": lambda v, t: v == t,
		"!=": lambda v, t: v != t,
	}

	op_func = operators.get(operator)
	if op_func:
		return op_func(value, threshold)
	return False


def is_in_cooldown(rule, agent_name):
	"""Перевіряє чи агент у періоді cooldown для цього правила."""
	cooldown_minutes = cint(rule.cooldown_minutes) or 60

	# Шукаємо останній алерт цього типу для агента
	last_alert = frappe.get_all(
		"oiAgentAlert",
		filters={
			"agent": agent_name,
			"alert_type": rule.alert_type,
			"creation": [">=", add_to_date(now_datetime(), minutes=-cooldown_minutes)],
		},
		limit=1,
	)

	return bool(last_alert)


def create_alert(rule, agent, metric_value):
	"""Створює новий алерт."""
	# Формуємо повідомлення
	message = get_alert_message(rule, agent, metric_value)

	# Створюємо запис алерту
	alert = frappe.get_doc(
		{
			"doctype": "oiAgentAlert",
			"agent": agent.name,
			"alert_type": rule.alert_type,
			"severity": rule.severity,
			"status": "Активне",
			"message": message,
			"value": flt(metric_value) if isinstance(metric_value, int | float) else 0,
			"threshold": rule.threshold_value,
		}
	)
	alert.insert(ignore_permissions=True)

	# Надсилаємо сповіщення
	if rule.send_system_notification:
		send_system_notification(alert, rule, agent)

	if rule.send_email and rule.email_recipients:
		send_email_notification(alert, rule, agent, message)

	frappe.db.commit()

	return alert.name


def get_alert_message(rule, agent, metric_value):
	"""Формує текст повідомлення алерту."""
	hostname = agent.hostname or agent.name

	messages = {
		"Офлайн": f"Агент {hostname} офлайн вже {int(metric_value)} хвилин",
		"Високе CPU": f"Агент {hostname}: CPU використання {metric_value:.1f}% (поріг: {rule.threshold_value}%)",
		"Висока RAM": f"Агент {hostname}: RAM використання {metric_value:.1f}% (поріг: {rule.threshold_value}%)",
		"Мало місця на диску": f"Агент {hostname}: Диск заповнений на {metric_value:.1f}% (поріг: {rule.threshold_value}%)",
		"Застаріла версія": f"Агент {hostname}: версія {metric_value} застаріла",
	}

	return messages.get(rule.alert_type, f"Алерт для {hostname}: {rule.alert_type}")


def send_system_notification(alert, rule, agent):
	"""Надсилає системне сповіщення у Frappe."""
	# Отримуємо користувачів з ролями System Manager та Maintenance Manager
	users = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["System Manager", "Maintenance Manager"]]},
		fields=["parent"],
		distinct=True,
	)

	for user in users:
		try:
			frappe.publish_realtime(
				event="msgprint", message=f"⚠️ {rule.severity}: {alert.message}", user=user.parent
			)

			# Створюємо Notification Log
			notification = frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": f"🚨 {rule.alert_type}: {agent.hostname or agent.name}",
					"for_user": user.parent,
					"type": "Alert",
					"document_type": "oiAgentAlert",
					"document_name": alert.name,
					"email_content": alert.message,
				}
			)
			notification.insert(ignore_permissions=True)
		except Exception:
			pass  # Ігноруємо помилки сповіщень


def send_email_notification(alert, rule, agent, message):
	"""Надсилає email сповіщення."""
	recipients = [e.strip() for e in rule.email_recipients.split(",") if e.strip()]

	if not recipients:
		return

	subject = f"[{rule.severity}] {rule.alert_type}: {agent.hostname or agent.name}"

	email_content = f"""
	<h3>🚨 Orange Inventory Alert</h3>
	<p><strong>Тип:</strong> {rule.alert_type}</p>
	<p><strong>Важливість:</strong> {rule.severity}</p>
	<p><strong>Агент:</strong> {agent.hostname or agent.name}</p>
	<p><strong>Повідомлення:</strong> {message}</p>
	<p><strong>Час:</strong> {now_datetime()}</p>
	<hr>
	<p><a href="{frappe.utils.get_url()}/app/oiagent/{agent.name}">Переглянути агента</a></p>
	<p><a href="{frappe.utils.get_url()}/app/oiagentalert/{alert.name}">Переглянути алерт</a></p>
	"""

	try:
		frappe.sendmail(recipients=recipients, subject=subject, message=email_content, now=True)
	except Exception as e:
		frappe.log_error(message=f"Помилка надсилання email: {str(e)}", title="Alert Email Error")


def auto_resolve_alerts():
	"""
	Автоматично вирішує алерти, коли умова більше не виконується.
	Викликається scheduled job.
	"""
	# Отримуємо всі активні алерти
	active_alerts = frappe.get_all(
		"oiAgentAlert", filters={"status": "Активне"}, fields=["name", "agent", "alert_type", "threshold"]
	)

	for alert in active_alerts:
		try:
			# Отримуємо агента
			agent = frappe.get_doc("oiAgent", alert.agent)

			# Перевіряємо чи умова ще актуальна
			rule = frappe.get_all(
				"oiAlertRule",
				filters={"alert_type": alert.alert_type, "enabled": 1},
				fields=["metric", "operator", "threshold_value"],
				limit=1,
			)

			if not rule:
				continue

			rule = rule[0]
			current_value = get_metric_value(rule.metric, agent)

			# Якщо умова більше не виконується - вирішуємо алерт
			if current_value is not None and not evaluate_condition(
				current_value, rule.operator, rule.threshold_value
			):
				frappe.db.set_value(
					"oiAgentAlert", alert.name, {"status": "Вирішено", "resolved_at": now_datetime()}
				)

				# Якщо агент повернувся онлайн - створюємо інформаційний алерт
				if alert.alert_type == "Офлайн":
					create_back_online_alert(agent)

		except Exception as e:
			frappe.log_error(
				message=f"Помилка авто-вирішення алерту {alert.name}: {str(e)}", title="Auto Resolve Error"
			)

	frappe.db.commit()


def create_back_online_alert(agent):
	"""Створює інформаційний алерт про повернення агента онлайн."""
	# Перевіряємо cooldown
	last_back_online = frappe.get_all(
		"oiAgentAlert",
		filters={
			"agent": agent.name,
			"alert_type": "Повернувся онлайн",
			"creation": [">=", add_to_date(now_datetime(), minutes=-60)],
		},
		limit=1,
	)

	if last_back_online:
		return

	alert = frappe.get_doc(
		{
			"doctype": "oiAgentAlert",
			"agent": agent.name,
			"alert_type": "Повернувся онлайн",
			"severity": "Info",
			"status": "Вирішено",
			"message": f"Агент {agent.hostname or agent.name} знову онлайн",
			"resolved_at": now_datetime(),
		}
	)
	alert.insert(ignore_permissions=True)
