# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import hashlib
import json

import frappe


def _save_software(agent_name: str, software_list: list):
	"""Зберігає/оновлює список встановленого ПЗ для агента."""
	if not software_list:
		return

	try:
		existing_software = {
			row.software_name: row.name
			for row in frappe.get_all(
				"oiAgentSoftware", filters={"agent": agent_name}, fields=["name", "software_name"]
			)
		}

		current_software_names = set()
		for sw in software_list:
			name = sw.get("name", "").strip()
			if not name:
				continue

			current_software_names.add(name)
			version = sw.get("version", "").strip()
			publisher = (sw.get("publisher") or sw.get("vendor") or "").strip()
			install_date = sw.get("install_date")
			install_location = sw.get("install_location", "").strip()

			parsed_date = None
			if install_date and len(install_date) == 8:
				try:
					parsed_date = f"{install_date[:4]}-{install_date[4:6]}-{install_date[6:8]}"
				except Exception:
					pass

			if name in existing_software:
				frappe.db.set_value(
					"oiAgentSoftware",
					existing_software[name],
					{
						"version": version,
						"publisher": publisher,
						"install_date": parsed_date,
						"install_location": install_location,
					},
					update_modified=False,
				)
				doc = frappe.get_doc("oiAgentSoftware", existing_software[name])
				doc.check_compliance()
				doc.db_update()
			else:
				doc = frappe.get_doc(
					{
						"doctype": "oiAgentSoftware",
						"agent": agent_name,
						"software_name": name,
						"version": version,
						"publisher": publisher,
						"install_date": parsed_date,
						"install_location": install_location,
					}
				)
				doc.insert(ignore_permissions=True)

		for sw_name, doc_name in existing_software.items():
			if sw_name not in current_software_names:
				frappe.delete_doc("oiAgentSoftware", doc_name, ignore_permissions=True)

		_update_catalog_counts()
	except Exception:
		frappe.log_error("Не вдалося зберегти oiAgentSoftware", "Agent API")


def _update_catalog_counts():
	"""Оновлює лічильники встановлень для всіх записів каталогу."""
	catalog_entries = frappe.get_all("oiSoftwareCatalog", fields=["name"])
	for entry in catalog_entries:
		doc = frappe.get_doc("oiSoftwareCatalog", entry.name)
		doc.update_installations_count()


@frappe.whitelist()
def get_blocked_software(agent_id=None):
	"""Повертає список заблокованого ПЗ для enforcement на агентах."""
	blocked_list = []
	agent_name = None
	agent_group = None
	if agent_id:
		agent_data = frappe.get_value("oiAgent", {"agent_id": agent_id}, ["name", "asset_group"])
		if agent_data:
			agent_name, agent_group = agent_data

	blocked = frappe.get_all(
		"oiSoftwareCatalog",
		filters={"is_allowed": 0, "enforce_block": 1},
		fields=["name", "software_name", "executable_names", "block_reason"],
	)

	for item in blocked:
		if not item.executable_names:
			continue
		if agent_id and agent_name:
			if not _is_rule_applicable(item.name, "oiSoftwareCatalog", agent_name, agent_group):
				continue

		executables = [exe.strip().lower() for exe in item.executable_names.split(",") if exe.strip()]
		if executables:
			blocked_list.append(
				{
					"name": item.software_name,
					"executables": executables,
					"reason": item.block_reason or "Заборонено політикою",
				}
			)

	version_input = json.dumps(blocked_list, sort_keys=True) + (agent_id or "")
	version_hash = hashlib.md5(version_input.encode()).hexdigest()[:8]
	return {"blocked": blocked_list, "version": version_hash, "count": len(blocked_list)}


def _is_rule_applicable(rule_name, parenttype, agent_name, agent_group):
	"""Перевіряє чи правило блокування застосовується до конкретного агента."""
	has_groups = frappe.db.exists("oiBlockRuleGroup", {"parent": rule_name, "parenttype": parenttype})
	has_agents = frappe.db.exists("oiBlockRuleAgent", {"parent": rule_name, "parenttype": parenttype})

	if not has_groups and not has_agents:
		return True

	if has_agents and frappe.db.exists(
		"oiBlockRuleAgent", {"parent": rule_name, "parenttype": parenttype, "agent": agent_name}
	):
		return True

	if (
		has_groups
		and agent_group
		and frappe.db.exists(
			"oiBlockRuleGroup", {"parent": rule_name, "parenttype": parenttype, "group": agent_group}
		)
	):
		return True

	return False
