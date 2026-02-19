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
	expiring_certs = frappe.db.sql(
		"""
		SELECT c.agent, c.subject_cn, c.not_after, c.days_until_expiry, c.status,
		       c.file_name, a.hostname
		FROM `taboiAgentCertificate` c
		INNER JOIN `taboiAgent` a ON a.name = c.agent
		WHERE a.status = 'Активний'
		AND c.status IN ('Скоро закінчується', 'Протермінований')
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

		create_alert(
			agent_name=agent_name,
			alert_type="Сертифікат закінчується",
			severity=severity,
			message=message,
		)

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

	frappe.db.commit()
