# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe


def _save_certificates(agent_name: str, certificates: list):
	"""Зберігає/оновлює список сертифікатів для агента."""
	if not certificates:
		return

	try:
		existing_certs = {
			row.thumbprint: row.name
			for row in frappe.get_all(
				"oiAgentCertificate",
				filters={"agent": agent_name},
				fields=["name", "thumbprint"],
			)
		}

		current_thumbprints = set()
		for cert in certificates:
			thumbprint = cert.get("thumbprint", "").strip()
			if not thumbprint:
				continue
			current_thumbprints.add(thumbprint)
			values = {
				"subject_cn": cert.get("subject_cn", ""),
				"issuer_cn": cert.get("issuer_cn", ""),
				"serial_number": cert.get("serial_number", ""),
				"not_before": cert.get("not_before"),
				"not_after": cert.get("not_after"),
				"file_name": cert.get("file_name", ""),
			}

			if thumbprint in existing_certs:
				frappe.db.set_value(
					"oiAgentCertificate", existing_certs[thumbprint], values, update_modified=False
				)
				doc = frappe.get_doc("oiAgentCertificate", existing_certs[thumbprint])
				doc.update_status()
				doc.db_update()
			else:
				doc = frappe.get_doc(
					{
						"doctype": "oiAgentCertificate",
						"agent": agent_name,
						"thumbprint": thumbprint,
						**values,
					}
				)
				doc.insert(ignore_permissions=True)

		for tp, doc_name in existing_certs.items():
			if tp not in current_thumbprints:
				frappe.delete_doc("oiAgentCertificate", doc_name, ignore_permissions=True)

	except Exception:
		frappe.log_error("Не вдалося зберегти oiAgentCertificate", "Agent API")
