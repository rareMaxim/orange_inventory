# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

from datetime import date, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class oiAgentCertificate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent: DF.Link
		days_until_expiry: DF.Int
		file_name: DF.Data | None
		issuer_cn: DF.Data | None
		not_after: DF.Date | None
		not_before: DF.Date | None
		serial_number: DF.Data | None
		status: DF.Literal[
			"\u0414\u0456\u0439\u0441\u043d\u0438\u0439",
			"\u0421\u043a\u043e\u0440\u043e \u0437\u0430\u043a\u0456\u043d\u0447\u0443\u0454\u0442\u044c\u0441\u044f",
			"\u041f\u0440\u043e\u0442\u0435\u0440\u043c\u0456\u043d\u043e\u0432\u0430\u043d\u0438\u0439",
			"\u0429\u0435 \u043d\u0435 \u0434\u0456\u0439\u0441\u043d\u0438\u0439",
		]
		subject_cn: DF.Data
		thumbprint: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.update_status()

	def update_status(self):
		"""Оновлює статус та кількість днів до закінчення."""
		if not self.not_after:
			self.status = "Дійсний"
			self.days_until_expiry = None
			return

		today = date.today()
		not_after = self.not_after
		if isinstance(not_after, str):
			not_after = date.fromisoformat(not_after)

		delta = (not_after - today).days
		self.days_until_expiry = delta

		if self.not_before:
			not_before = self.not_before
			if isinstance(not_before, str):
				not_before = date.fromisoformat(not_before)
			if today < not_before:
				self.status = "Ще не дійсний"
				return

		if delta < 0:
			self.status = "Протермінований"
		elif delta <= 30:
			self.status = "Скоро закінчується"
		else:
			self.status = "Дійсний"


@frappe.whitelist()
def create_delete_certs_command(certs_by_agent):
	"""
	Створює віддалену команду видалення обраних сертифікатів для агентів.

	Args:
	    certs_by_agent: dict {agent_name: [{name, file_name, subject_cn}, ...]}
	"""
	import json as json_module

	if isinstance(certs_by_agent, str):
		certs_by_agent = json_module.loads(certs_by_agent)

	created = []
	skipped = []

	for agent_name, certs in certs_by_agent.items():
		agent = frappe.db.get_value("oiAgent", agent_name, ["name", "hostname", "status"], as_dict=True)
		if not agent:
			skipped.append({"agent": agent_name, "reason": "Агент не знайдено"})
			continue

		if agent.status != "Активний":
			skipped.append({"agent": agent.hostname, "reason": f"Статус: {agent.status}"})
			continue

		# Збираємо імена файлів
		file_names = [c["file_name"] for c in certs if c.get("file_name")]
		if not file_names:
			skipped.append({"agent": agent.hostname, "reason": "Немає імен файлів"})
			continue

		# Генеруємо PowerShell скрипт для конкретних файлів
		ps_script = _build_delete_certs_script(file_names)

		cmd = frappe.get_doc(
			{
				"doctype": "oiAgentCommand",
				"agent": agent_name,
				"command_type": "PowerShell",
				"command": ps_script,
				"status": "Pending",
				"timeout_seconds": 120,
				"expires_at": now_datetime() + timedelta(hours=2),
			}
		)
		cmd.flags.ignore_permissions = True
		cmd.insert()

		created.append(
			{
				"agent": agent.hostname,
				"command": cmd.name,
				"count": len(file_names),
			}
		)

	frappe.db.commit()
	return {"created": created, "skipped": skipped}


def _build_delete_certs_script(file_names):
	"""Генерує PowerShell скрипт для видалення конкретних .cer файлів."""
	# Екрануємо імена файлів для PowerShell
	escaped = []
	for fn in file_names:
		safe_name = fn.replace("'", "''")
		escaped.append(f"    '{safe_name}'")

	files_array = ",\n".join(escaped)

	return (
		"$certDir = 'C:\\My Certificates and CRLs 13'\n"
		"$filesToDelete = @(\n"
		f"{files_array}\n"
		")\n"
		"$deleted = @()\n"
		"$errors = @()\n"
		"foreach ($fileName in $filesToDelete) {\n"
		"    $filePath = Join-Path $certDir $fileName\n"
		"    if (Test-Path $filePath) {\n"
		"        try {\n"
		"            Remove-Item $filePath -Force\n"
		"            $deleted += $fileName\n"
		"        } catch {\n"
		'            $errors += "${fileName}: $($_.Exception.Message)"\n'
		"        }\n"
		"    } else {\n"
		'        $errors += "${fileName}: file not found"\n'
		"    }\n"
		"}\n"
		"if ($deleted.Count -gt 0) {\n"
		'    Write-Output "Deleted $($deleted.Count) certificate(s):"\n'
		'    $deleted | ForEach-Object { Write-Output "  - $_" }\n'
		"} else {\n"
		"    Write-Output 'No certificates deleted.'\n"
		"}\n"
		"if ($errors.Count -gt 0) {\n"
		'    Write-Output "`nErrors:"\n'
		'    $errors | ForEach-Object { Write-Output "  - $_" }\n'
		"}"
	)
