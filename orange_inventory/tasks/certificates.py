# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe


def check_certificate_expiry():
	"""Перевіряє терміни дії сертифікатів на машинах агентів."""
	from orange_inventory.orange_inventory.doctype.oiagentalert.oiagentalert import (
		create_alert,
		resolve_alerts,
	)

	all_certs = frappe.get_all("oiAgentCertificate", fields=["name"])
	for cert_ref in all_certs:
		doc = frappe.get_doc("oiAgentCertificate", cert_ref.name)
		doc.update_status()
		doc.db_update()

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

	agents_with_issues = {}
	for cert in expiring_certs:
		if cert.agent not in agents_with_issues:
			agents_with_issues[cert.agent] = {"hostname": cert.hostname, "certs": []}
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
			agent_name=agent_name, alert_type="Сертифікат закінчується", severity=severity, message=message
		)
		if alert_name:
			new_alerts[agent_name] = data

	agents_with_alerts = frappe.get_all(
		"oiAgentAlert",
		filters={"alert_type": "Сертифікат закінчується", "status": "Активне"},
		fields=["agent"],
		group_by="agent",
	)
	for row in agents_with_alerts:
		if row.agent not in agents_with_issues:
			resolve_alerts(row.agent, "Сертифікат закінчується")

	send_certificate_email_notifications(new_alerts)
	frappe.db.commit()


def send_certificate_email_notifications(agents_with_issues: dict):
	"""Надсилає email-сповіщення про сертифікати."""
	if not agents_with_issues:
		return
	for agent_name, data in agents_with_issues.items():
		email = _get_employee_email_for_agent(agent_name)
		if email:
			_send_certificate_notification_email(email, data)


def _get_employee_email_for_agent(agent_name: str) -> str | None:
	"""Отримує email користувача за ланцюгом: oiAgent → oiAsset → hromsEmployee."""
	asset_name = frappe.db.get_value("oiAgent", agent_name, "asset")
	if not asset_name:
		return None
	employee_name = frappe.db.get_value("oiAsset", asset_name, "asset_user")
	if not employee_name:
		return None
	work_email, personal_email = frappe.db.get_value(
		"hromsEmployee", employee_name, ["work_email", "email"]
	) or (None, None)
	return work_email or personal_email


def _send_certificate_notification_email(email: str, data: dict):
	"""Надсилає email про проблеми з сертифікатами."""
	template_name = "OI Certificate Expiry"
	template = frappe.get_doc("Email Template", template_name)
	rendered = template.get_formatted_email(
		{
			"hostname": data["hostname"],
			"expired": [c for c in data["certs"] if c.status == "Протермінований"],
			"expiring": [c for c in data["certs"] if c.status == "Скоро закінчується"],
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
			f"Не вдалося надіслати email на {email} про сертифікати {data['hostname']}",
			"Certificate Email Notification",
		)


@frappe.whitelist()
def test_certificate_email_notification(employee_name: str):
	"""Тестова відправка email-сповіщення для співробітника."""
	work_email, personal_email = frappe.db.get_value(
		"hromsEmployee", employee_name, ["work_email", "email"]
	) or (None, None)
	email = work_email or personal_email
	if not email:
		frappe.throw(f"Співробітник {employee_name} не має email-адреси")
	assets = frappe.get_all("oiAsset", filters={"responsible_employee": employee_name}, fields=["name"])
	if not assets:
		frappe.throw(f"У співробітника {employee_name} немає прив'язаних активів")
	asset_names = [a.name for a in assets]
	agents = frappe.get_all(
		"oiAgent", filters={"asset": ["in", asset_names], "status": "Активний"}, fields=["name", "hostname"]
	)
	if not agents:
		frappe.throw(f"Немає активних агентів для активів співробітника {employee_name}")
	for agent in agents:
		certs = frappe.db.sql(
			"SELECT agent, subject_cn, not_after, days_until_expiry, status, file_name FROM `taboiAgentCertificate` WHERE agent = %s AND status IN ('Скоро закінчується', 'Протермінований') ORDER BY not_after ASC LIMIT 20",
			agent.name,
			as_dict=True,
		)
		if certs:
			_send_certificate_notification_email(email, {"hostname": agent.hostname, "certs": certs})


def test_cert_email_for_agent(agent_name: str, override_email: str):
	"""Тест: надсилає email про сертифікати конкретного агента."""
	agent = frappe.db.get_value("oiAgent", agent_name, ["hostname", "status"], as_dict=True)
	if not agent:
		return
	certs = frappe.db.sql(
		"SELECT subject_cn, file_name, not_after, days_until_expiry, status FROM `taboiAgentCertificate` WHERE agent = %s AND status IN ('Скоро закінчується', 'Протермінований') ORDER BY not_after ASC",
		agent_name,
		as_dict=True,
	)
	if certs:
		_send_certificate_notification_email(override_email, {"hostname": agent.hostname, "certs": certs})
