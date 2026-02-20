# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
Scheduled tasks для Orange Inventory.
"""

import json

import frappe
from frappe.utils import add_to_date, now_datetime

# Пороги для сповіщень
THRESHOLDS = {
	"cpu_usage": 90,  # %
	"ram_usage": 90,  # %
	"disk_usage": 90,  # %
	"offline_minutes": 30,
}


def mark_offline_agents():
	"""
	Позначає агентів як 'Офлайн' якщо вони не відповідали більше 30 хвилин.
	Створює сповіщення для нових офлайн агентів.

	Запускається щогодини через scheduler.
	"""
	from orange_inventory.orange_inventory.doctype.oiagentalert.oiagentalert import (
		create_alert,
		resolve_alerts,
	)

	threshold = add_to_date(now_datetime(), minutes=-THRESHOLDS["offline_minutes"])

	# Знаходимо агентів які стали офлайн
	agents_going_offline = frappe.db.sql(
		"""
		SELECT name, hostname
		FROM `taboiAgent`
		WHERE last_seen < %s
		AND status IN ('Активний', 'Неактивний')
		""",
		threshold,
		as_dict=True,
	)

	# Створюємо сповіщення для кожного
	for agent in agents_going_offline:
		create_alert(
			agent_name=agent.name,
			alert_type="Офлайн",
			severity="Critical",
			message=f"Агент {agent.hostname} не відповідає більше {THRESHOLDS['offline_minutes']} хвилин",
		)

	# Оновлюємо статус
	if agents_going_offline:
		frappe.db.sql(
			"""
			UPDATE `taboiAgent`
			SET status = 'Офлайн'
			WHERE last_seen < %s
			AND status IN ('Активний', 'Неактивний')
			""",
			threshold,
		)

	# Перевіряємо агентів які повернулись онлайн
	agents_back_online = frappe.db.sql(
		"""
		SELECT a.name, a.hostname
		FROM `taboiAgent` a
		WHERE a.status = 'Активний'
		AND EXISTS (
			SELECT 1 FROM `taboiAgentAlert` al
			WHERE al.agent = a.name
			AND al.alert_type = 'Офлайн'
			AND al.status = 'Активне'
		)
		""",
		as_dict=True,
	)

	for agent in agents_back_online:
		resolve_alerts(agent.name, "Офлайн")
		create_alert(
			agent_name=agent.name,
			alert_type="Повернувся онлайн",
			severity="Info",
			message=f"Агент {agent.hostname} знову онлайн",
		)

	frappe.db.commit()


def check_resource_alerts():
	"""
	Перевіряє останні snapshots на перевищення порогів CPU/RAM/Disk.

	Запускається щогодини.
	"""
	from orange_inventory.orange_inventory.doctype.oiagentalert.oiagentalert import (
		create_alert,
		resolve_alerts,
	)

	# Отримуємо останній snapshot для кожного агента
	latest_snapshots = frappe.db.sql(
		"""
		SELECT s.agent, s.cpu_usage, s.ram_usage, s.disk_usage, a.hostname
		FROM `taboiAgentSnapshot` s
		INNER JOIN `taboiAgent` a ON a.name = s.agent
		WHERE s.timestamp = (
			SELECT MAX(s2.timestamp)
			FROM `taboiAgentSnapshot` s2
			WHERE s2.agent = s.agent
		)
		AND a.status = 'Активний'
		""",
		as_dict=True,
	)

	for snapshot in latest_snapshots:
		# Перевірка CPU
		if snapshot.cpu_usage and snapshot.cpu_usage >= THRESHOLDS["cpu_usage"]:
			create_alert(
				agent_name=snapshot.agent,
				alert_type="Високе CPU",
				severity="Warning",
				message=f"CPU використання {snapshot.cpu_usage:.1f}% на {snapshot.hostname}",
				value=snapshot.cpu_usage,
				threshold=THRESHOLDS["cpu_usage"],
			)
		else:
			resolve_alerts(snapshot.agent, "Високе CPU")

		# Перевірка RAM
		if snapshot.ram_usage and snapshot.ram_usage >= THRESHOLDS["ram_usage"]:
			create_alert(
				agent_name=snapshot.agent,
				alert_type="Висока RAM",
				severity="Warning",
				message=f"RAM використання {snapshot.ram_usage:.1f}% на {snapshot.hostname}",
				value=snapshot.ram_usage,
				threshold=THRESHOLDS["ram_usage"],
			)
		else:
			resolve_alerts(snapshot.agent, "Висока RAM")

		# Перевірка дисків
		if snapshot.disk_usage:
			try:
				disks = (
					json.loads(snapshot.disk_usage)
					if isinstance(snapshot.disk_usage, str)
					else snapshot.disk_usage
				)
				for disk in disks:
					usage = disk.get("usage_percent", 0)
					if usage >= THRESHOLDS["disk_usage"]:
						create_alert(
							agent_name=snapshot.agent,
							alert_type="Мало місця на диску",
							severity="Critical" if usage >= 95 else "Warning",
							message=f"Диск {disk.get('drive', '?')} заповнено на {usage:.1f}% на {snapshot.hostname}",
							value=usage,
							threshold=THRESHOLDS["disk_usage"],
						)
						break  # Одне сповіщення на агента
				else:
					resolve_alerts(snapshot.agent, "Мало місця на диску")
			except (json.JSONDecodeError, TypeError):
				pass

	frappe.db.commit()


def cleanup_old_snapshots():
	"""
	Видаляє старі snapshots (старші 30 днів) для економії місця.

	Запускається щодня.
	"""
	threshold = add_to_date(now_datetime(), days=-30)

	frappe.db.sql(
		"""
		DELETE FROM `taboiAgentSnapshot`
		WHERE timestamp < %s
		""",
		threshold,
	)

	frappe.db.commit()


def cleanup_old_alerts():
	"""
	Видаляє старі вирішені сповіщення (старші 7 днів).

	Запускається щодня.
	"""
	threshold = add_to_date(now_datetime(), days=-7)

	frappe.db.sql(
		"""
		DELETE FROM `taboiAgentAlert`
		WHERE status IN ('Вирішено', 'Проігноровано')
		AND resolved_at < %s
		""",
		threshold,
	)

	frappe.db.commit()


def check_outdated_agents():
	"""
	Перевіряє агентів на застарілу версію.
	Створює сповіщення якщо версія агента відрізняється від актуальної.

	Запускається щогодини.
	"""
	from orange_inventory.orange_inventory.doctype.oiagentalert.oiagentalert import (
		create_alert,
		resolve_alerts,
	)

	# Отримуємо актуальну версію агента
	latest_version = frappe.db.get_value("oiAgentRelease", {"is_latest": 1}, "version")

	if not latest_version:
		return  # Немає релізів

	# Знаходимо агентів з застарілою версією
	outdated_agents = frappe.db.sql(
		"""
		SELECT name, hostname, agent_version
		FROM `taboiAgent`
		WHERE status = 'Активний'
		AND agent_version IS NOT NULL
		AND agent_version != ''
		AND agent_version != %s
		""",
		latest_version,
		as_dict=True,
	)

	for agent in outdated_agents:
		create_alert(
			agent_name=agent.name,
			alert_type="Застаріла версія",
			severity="Warning",
			message=f"Агент {agent.hostname} має версію {agent.agent_version}, "
			f"актуальна версія: {latest_version}",
		)

	# Вирішуємо алерти для агентів з актуальною версією
	up_to_date_agents = frappe.db.sql(
		"""
		SELECT name
		FROM `taboiAgent`
		WHERE agent_version = %s
		""",
		latest_version,
		as_dict=True,
	)

	for agent in up_to_date_agents:
		resolve_alerts(agent.name, "Застаріла версія")

	frappe.db.commit()


def check_certificate_expiry():
	"""
	Перевіряє терміни дії сертифікатів на машинах агентів.
	Створює сповіщення якщо сертифікат закінчується протягом 30 днів або вже протермінований.

	Запускається щодня.
	"""
	from orange_inventory.orange_inventory.doctype.oiagentalert.oiagentalert import (
		create_alert,
		resolve_alerts,
	)

	# Оновлюємо статус та days_until_expiry для всіх сертифікатів
	all_certs = frappe.get_all(
		"oiAgentCertificate",
		fields=["name"],
	)
	for cert_ref in all_certs:
		doc = frappe.get_doc("oiAgentCertificate", cert_ref.name)
		doc.update_status()
		doc.db_update()

	# Знаходимо сертифікати що закінчуються або протерміновані
	# Не фільтруємо по статусу агента — сертифікати актуальні незалежно від того чи агент онлайн
	expiring_certs = frappe.db.sql(
		"""
		SELECT c.agent, c.subject_cn, c.not_after, c.days_until_expiry, c.status,
		       c.file_name, a.hostname
		FROM `taboiAgentCertificate` c
		INNER JOIN `taboiAgent` a ON a.name = c.agent
		WHERE c.status IN ('Скоро закінчується', 'Протермінований')
		""",
		as_dict=True,
	)

	# Групуємо по агентах
	agents_with_issues = {}
	for cert in expiring_certs:
		if cert.agent not in agents_with_issues:
			agents_with_issues[cert.agent] = {
				"hostname": cert.hostname,
				"certs": [],
			}
		agents_with_issues[cert.agent]["certs"].append(cert)

	new_alerts = {}
	for agent_name, data in agents_with_issues.items():
		certs = data["certs"]
		expired = [c for c in certs if c.status == "Протермінований"]
		expiring = [c for c in certs if c.status == "Скоро закінчується"]

		parts = []
		if expired:
			names = ", ".join(c.subject_cn or c.file_name for c in expired)
			parts.append(f"протерміновані: {names}")
		if expiring:
			names = ", ".join(f"{c.subject_cn or c.file_name} ({c.days_until_expiry} дн.)" for c in expiring)
			parts.append(f"закінчуються: {names}")

		severity = "Critical" if expired else "Warning"
		message = f"Сертифікати на {data['hostname']}: {'; '.join(parts)}"

		alert_name = create_alert(
			agent_name=agent_name,
			alert_type="Сертифікат закінчується",
			severity=severity,
			message=message,
		)

		# Якщо алерт новий — додаємо до списку для email
		if alert_name:
			new_alerts[agent_name] = data

	# Вирішуємо алерти для агентів де всі сертифікати дійсні
	agents_with_alerts = frappe.get_all(
		"oiAgentAlert",
		filters={"alert_type": "Сертифікат закінчується", "status": "Активне"},
		fields=["agent"],
		group_by="agent",
	)

	for row in agents_with_alerts:
		if row.agent not in agents_with_issues:
			resolve_alerts(row.agent, "Сертифікат закінчується")

	# Надсилаємо email тільки для НОВИХ алертів (уникаємо повторних листів)
	send_certificate_email_notifications(new_alerts)

	frappe.db.commit()


def send_certificate_email_notifications(agents_with_issues: dict):
	"""
	Надсилає email-сповіщення відповідальним співробітникам
	про протерміновані або скоро протерміновані сертифікати.

	Ланцюг: oiAgent → oiAsset (asset) → hromsEmployee (responsible_employee) → email/work_email
	"""
	if not agents_with_issues:
		return

	for agent_name, data in agents_with_issues.items():
		email = _get_employee_email_for_agent(agent_name)
		if not email:
			continue

		_send_certificate_notification_email(email, data)


def _get_employee_email_for_agent(agent_name: str) -> str | None:
	"""
	Отримує email користувача за ланцюгом:
	oiAgent → oiAsset → hromsEmployee (asset_user) → work_email або email
	"""
	# Отримуємо asset прив'язаний до агента
	asset_name = frappe.db.get_value("oiAgent", agent_name, "asset")
	if not asset_name:
		return None

	# Отримуємо користувача активу
	employee_name = frappe.db.get_value("oiAsset", asset_name, "asset_user")
	if not employee_name:
		return None

	# Отримуємо email (пріоритет: робочий > особистий)
	work_email, personal_email = frappe.db.get_value(
		"hromsEmployee", employee_name, ["work_email", "email"]
	) or (None, None)

	return work_email or personal_email


def _send_certificate_notification_email(email: str, data: dict):
	"""Надсилає email про проблеми з сертифікатами через Email Template."""
	certs = data["certs"]
	hostname = data["hostname"]
	expired = [c for c in certs if c.status == "Протермінований"]
	expiring = [c for c in certs if c.status == "Скоро закінчується"]

	template_name = "OI Certificate Expiry"
	template = frappe.get_doc("Email Template", template_name)
	rendered = template.get_formatted_email(
		{
			"hostname": hostname,
			"expired": expired,
			"expiring": expiring,
		}
	)

	try:
		frappe.sendmail(
			recipients=[email],
			sender="Orange Inventory <itsystems@mlt.gov.ua>",
			subject=rendered["subject"],
			message=rendered["message"],
			now=True,
		)
	except Exception:
		frappe.log_error(
			f"Не вдалося надіслати email на {email} про сертифікати {hostname}",
			"Certificate Email Notification",
		)


@frappe.whitelist()
def test_certificate_email_notification(employee_name: str):
	"""
	Тестова відправка email-сповіщення про сертифікати для конкретного співробітника.
	Знаходить всі агенти/активи прив'язані до цього співробітника і надсилає сповіщення.

	Використання: bench execute orange_inventory.tasks.test_certificate_email_notification --args '["EMP-26017"]'
	"""
	# Отримуємо email
	work_email, personal_email = frappe.db.get_value(
		"hromsEmployee", employee_name, ["work_email", "email"]
	) or (None, None)

	email = work_email or personal_email
	if not email:
		frappe.throw(f"Співробітник {employee_name} не має email-адреси")

	# Знаходимо активи цього співробітника
	assets = frappe.get_all(
		"oiAsset",
		filters={"responsible_employee": employee_name},
		fields=["name"],
	)

	if not assets:
		frappe.throw(f"У співробітника {employee_name} немає прив'язаних активів")

	# Знаходимо агентів для цих активів
	asset_names = [a.name for a in assets]
	agents = frappe.get_all(
		"oiAgent",
		filters={"asset": ["in", asset_names], "status": "Активний"},
		fields=["name", "hostname"],
	)

	if not agents:
		frappe.throw(f"Немає активних агентів для активів співробітника {employee_name}")

	sent = 0
	for agent in agents:
		# Знаходимо проблемні сертифікати
		certs = frappe.db.sql(
			"""
			SELECT agent, subject_cn, not_after, days_until_expiry, status, file_name
			FROM `taboiAgentCertificate`
			WHERE agent = %s
			AND status IN ('Скоро закінчується', 'Протермінований')
			ORDER BY not_after ASC
			LIMIT 20
			""",
			agent.name,
			as_dict=True,
		)

		if not certs:
			continue

		data = {
			"hostname": agent.hostname,
			"certs": certs,
		}

		_send_certificate_notification_email(email, data)
		sent += 1
		print(f"Email надіслано на {email} для {agent.hostname} ({len(certs)} сертифікатів)")

	if sent == 0:
		print(f"Немає проблемних сертифікатів для агентів співробітника {employee_name}")
	else:
		print(f"Всього надіслано {sent} email(ів)")


def test_cert_email_for_agent(agent_name: str, override_email: str):
	"""
	Тест: надсилає email про сертифікати конкретного агента на вказану адресу.

	Використання: bench execute orange_inventory.tasks.test_cert_email_for_agent
	              --args '["MMRZO086-f66f36f1", "maks4a@gmail.com"]'
	"""
	agent = frappe.db.get_value("oiAgent", agent_name, ["hostname", "status"], as_dict=True)
	if not agent:
		print(f"Агент {agent_name} не знайдено")
		return

	certs = frappe.db.sql(
		"""
		SELECT subject_cn, file_name, not_after, days_until_expiry, status
		FROM `taboiAgentCertificate`
		WHERE agent = %s
		AND status IN ('Скоро закінчується', 'Протермінований')
		ORDER BY not_after ASC
		""",
		agent_name,
		as_dict=True,
	)

	if not certs:
		print(f"Немає проблемних сертифікатів для агента {agent_name}")
		return

	data = {"hostname": agent.hostname, "certs": certs}
	_send_certificate_notification_email(override_email, data)
	print(f"Email надіслано на {override_email} для {agent.hostname} ({len(certs)} сертифікатів)")
