# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

"""
API для аналізу та моніторингу програмного забезпечення.

Функції для:
- Перегляд заборонених ПЗ на агентах
- Перегляд ПЗ що потребує оновлення
- Перегляд ПЗ що не в каталозі
- Аналіз встановлень по всій організації
"""

import frappe


@frappe.whitelist()
def get_forbidden_software():
	"""
	Повертає список забороненого ПЗ встановленого на агентах.

	Returns:
	        list: [
	                {
	                        "software_name": "...",
	                        "agent": "...",
	                        "hostname": "...",
	                        "version": "...",
	                        "publisher": "..."
	                }
	        ]
	"""
	return frappe.db.sql(
		"""
		SELECT
			sw.software_name,
			sw.agent,
			ag.hostname,
			sw.version,
			sw.publisher
		FROM `taboiAgentSoftware` sw
		LEFT JOIN `taboiAgent` ag ON sw.agent = ag.name
		WHERE sw.compliance_status = 'Заборонено'
		ORDER BY sw.software_name, ag.hostname
	""",
		as_dict=True,
	)


@frappe.whitelist()
def get_outdated_software():
	"""
	Повертає список ПЗ що потребує оновлення.

	Returns:
	        list: [
	                {
	                        "software_name": "...",
	                        "agent": "...",
	                        "hostname": "...",
	                        "version": "...",
	                        "min_version": "...",
	                        "catalog_entry": "..."
	                }
	        ]
	"""
	return frappe.db.sql(
		"""
		SELECT
			sw.software_name,
			sw.agent,
			ag.hostname,
			sw.version,
			cat.min_version,
			sw.catalog_entry
		FROM `taboiAgentSoftware` sw
		LEFT JOIN `taboiAgent` ag ON sw.agent = ag.name
		LEFT JOIN `taboiSoftwareCatalog` cat ON sw.catalog_entry = cat.name
		WHERE sw.needs_update = 1
		ORDER BY sw.software_name, ag.hostname
	""",
		as_dict=True,
	)


@frappe.whitelist()
def get_uncatalogued_software():
	"""
	Повертає список ПЗ що не в каталозі (невідоме ПЗ).

	Returns:
	        list: [
	                {
	                        "software_name": "...",
	                        "publisher": "...",
	                        "agents_count": int,
	                        "versions": "..."
	                }
	        ]
	"""
	return frappe.db.sql(
		"""
		SELECT
			sw.software_name,
			sw.publisher,
			COUNT(DISTINCT sw.agent) as agents_count,
			GROUP_CONCAT(DISTINCT sw.version SEPARATOR ', ') as versions
		FROM `taboiAgentSoftware` sw
		WHERE sw.compliance_status = 'Не в каталозі'
		GROUP BY sw.software_name, sw.publisher
		ORDER BY agents_count DESC, sw.software_name
	""",
		as_dict=True,
	)


@frappe.whitelist()
def get_software_summary():
	"""
	Повертає зведену статистику по ПЗ.

	Returns:
	        dict: {
	                "total_software_records": int,
	                "unique_software": int,
	                "allowed_count": int,
	                "forbidden_count": int,
	                "uncatalogued_count": int,
	                "needs_update_count": int,
	                "agents_with_forbidden": int,
	                "agents_with_outdated": int
	        }
	"""
	total = frappe.db.count("oiAgentSoftware")

	unique_software = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT software_name) as cnt FROM `taboiAgentSoftware`
	"""
	)[0][0]

	allowed = frappe.db.count("oiAgentSoftware", {"compliance_status": "Дозволено"})
	forbidden = frappe.db.count("oiAgentSoftware", {"compliance_status": "Заборонено"})
	uncatalogued = frappe.db.count("oiAgentSoftware", {"compliance_status": "Не в каталозі"})
	needs_update = frappe.db.count("oiAgentSoftware", {"needs_update": 1})

	agents_with_forbidden = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT agent) FROM `taboiAgentSoftware`
		WHERE compliance_status = 'Заборонено'
	"""
	)[0][0]

	agents_with_outdated = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT agent) FROM `taboiAgentSoftware`
		WHERE needs_update = 1
	"""
	)[0][0]

	return {
		"total_software_records": total,
		"unique_software": unique_software,
		"allowed_count": allowed,
		"forbidden_count": forbidden,
		"uncatalogued_count": uncatalogued,
		"needs_update_count": needs_update,
		"agents_with_forbidden": agents_with_forbidden,
		"agents_with_outdated": agents_with_outdated,
	}


@frappe.whitelist()
def get_software_installations(software_name: str):
	"""
	Повертає список агентів де встановлено вказане ПЗ.

	Args:
	        software_name: назва програми

	Returns:
	        list: [
	                {
	                        "agent": "...",
	                        "hostname": "...",
	                        "version": "...",
	                        "install_date": "...",
	                        "compliance_status": "...",
	                        "needs_update": 0/1
	                }
	        ]
	"""
	return frappe.db.sql(
		"""
		SELECT
			sw.agent,
			ag.hostname,
			sw.version,
			sw.install_date,
			sw.compliance_status,
			sw.needs_update
		FROM `taboiAgentSoftware` sw
		LEFT JOIN `taboiAgent` ag ON sw.agent = ag.name
		WHERE sw.software_name = %(software_name)s
		ORDER BY ag.hostname
	""",
		{"software_name": software_name},
		as_dict=True,
	)


@frappe.whitelist()
def get_agent_software_report(agent: str):
	"""
	Повертає звіт по ПЗ для конкретного агента.

	Args:
	        agent: ID агента

	Returns:
	        dict: {
	                "agent": "...",
	                "hostname": "...",
	                "total_software": int,
	                "allowed": int,
	                "forbidden": int,
	                "uncatalogued": int,
	                "needs_update": int,
	                "software": [...]
	        }
	"""
	agent_doc = frappe.get_doc("oiAgent", agent)

	software = frappe.get_all(
		"oiAgentSoftware",
		filters={"agent": agent},
		fields=[
			"software_name",
			"version",
			"publisher",
			"compliance_status",
			"needs_update",
			"catalog_entry",
		],
		order_by="software_name",
	)

	allowed = sum(1 for s in software if s.compliance_status == "Дозволено")
	forbidden = sum(1 for s in software if s.compliance_status == "Заборонено")
	uncatalogued = sum(1 for s in software if s.compliance_status == "Не в каталозі")
	needs_update = sum(1 for s in software if s.needs_update)

	return {
		"agent": agent,
		"hostname": agent_doc.hostname,
		"total_software": len(software),
		"allowed": allowed,
		"forbidden": forbidden,
		"uncatalogued": uncatalogued,
		"needs_update": needs_update,
		"software": software,
	}


@frappe.whitelist()
def add_to_catalog(software_name: str, publisher: str = None, is_allowed: int = 1):
	"""
	Додає ПЗ до каталогу та оновлює статуси на агентах.

	Args:
	        software_name: назва програми
	        publisher: видавець (опціонально)
	        is_allowed: 1 - дозволено, 0 - заборонено

	Returns:
	        dict: {"status": "success", "catalog_entry": "..."}
	"""
	# Перевіряємо чи вже є в каталозі
	existing = frappe.db.get_value("oiSoftwareCatalog", {"software_name": software_name})
	if existing:
		frappe.throw(f"'{software_name}' вже є в каталозі")

	# Створюємо запис
	catalog = frappe.get_doc(
		{
			"doctype": "oiSoftwareCatalog",
			"software_name": software_name,
			"publisher": publisher,
			"is_allowed": is_allowed,
		}
	)
	catalog.insert(ignore_permissions=True)

	# Оновлюємо всі записи на агентах
	agent_software = frappe.get_all("oiAgentSoftware", filters={"software_name": software_name}, pluck="name")

	for sw_name in agent_software:
		doc = frappe.get_doc("oiAgentSoftware", sw_name)
		doc.check_compliance()
		doc.db_update()

	frappe.db.commit()

	return {"status": "success", "catalog_entry": catalog.name, "updated_agents": len(agent_software)}


@frappe.whitelist()
def recheck_all_compliance():
	"""
	Перевіряє відповідність для всього ПЗ на всіх агентах.
	Корисно після змін в каталозі.

	Returns:
	        dict: {"status": "success", "checked": int}
	"""
	software_list = frappe.get_all("oiAgentSoftware", pluck="name")

	for sw_name in software_list:
		doc = frappe.get_doc("oiAgentSoftware", sw_name)
		doc.check_compliance()
		doc.db_update()

	frappe.db.commit()

	return {"status": "success", "checked": len(software_list)}


@frappe.whitelist()
def get_missing_required_software():
	"""
	Повертає список агентів яким бракує обов'язкового ПЗ.

	Returns:
	        list: [
	                {
	                        "agent": "...",
	                        "hostname": "...",
	                        "missing_software": ["...", "..."]
	                }
	        ]
	"""
	# Отримуємо обов'язкове ПЗ
	required_software = frappe.get_all(
		"oiSoftwareCatalog", filters={"is_required": 1, "is_allowed": 1}, pluck="software_name"
	)

	if not required_software:
		return []

	# Отримуємо всіх активних агентів
	agents = frappe.get_all("oiAgent", filters={"status": "Активний"}, fields=["name", "hostname"])

	result = []
	for agent in agents:
		# Отримуємо встановлене ПЗ для агента
		installed = frappe.get_all("oiAgentSoftware", filters={"agent": agent.name}, pluck="software_name")
		installed_lower = {s.lower() for s in installed}

		# Шукаємо відсутнє обов'язкове ПЗ
		missing = [sw for sw in required_software if sw.lower() not in installed_lower]

		if missing:
			result.append({"agent": agent.name, "hostname": agent.hostname, "missing_software": missing})

	return result
