# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def get_pending_commands(agent_id: str):
	"""Повертає список команд для виконання агентом."""
	agent_name = frappe.db.get_value("oiAgent", {"agent_id": agent_id}, "name")
	if not agent_name:
		return {"commands": [], "error": "Агент не знайдено"}

	commands = frappe.get_all(
		"oiAgentCommand",
		filters={"agent": agent_name, "status": "Pending"},
		fields=[
			"name",
			"command_type",
			"command",
			"arguments",
			"timeout_seconds",
			"signature",
			"expires_at",
			"command_template",
			"approved_by_user",
		],
		order_by="creation asc",
	)

	result = []
	now = now_datetime()
	for cmd in commands:
		if cmd.expires_at and cmd.expires_at < now:
			frappe.db.set_value(
				"oiAgentCommand", cmd.name, {"status": "Cancelled", "error_output": "Команда протермінована"}
			)
			continue

		if cmd.command_template:
			requires_approval = frappe.db.get_value(
				"oiCommandTemplate", cmd.command_template, "requires_approval"
			)
			if requires_approval and not cmd.approved_by_user:
				continue

		frappe.db.set_value("oiAgentCommand", cmd.name, "status", "Sent")
		arguments = None
		if cmd.arguments:
			try:
				arguments = json.loads(cmd.arguments)
			except json.JSONDecodeError:
				arguments = None

		expires_at_str = None
		if cmd.expires_at:
			if isinstance(cmd.expires_at, str):
				expires_at_str = cmd.expires_at.split(".")[0] if "." in cmd.expires_at else cmd.expires_at
			else:
				expires_at_str = cmd.expires_at.strftime("%Y-%m-%d %H:%M:%S")

		result.append(
			{
				"id": cmd.name,
				"type": cmd.command_type,
				"command": cmd.command,
				"arguments": arguments,
				"timeout": cmd.timeout_seconds or 60,
				"signature": cmd.signature,
				"expires_at": expires_at_str,
			}
		)

	frappe.db.commit()
	return {"commands": result}


@frappe.whitelist()
def report_command_result(
	command_id: str, status: str, exit_code: int = None, output: str = None, error_output: str = None
):
	"""Повідомляє результат виконання команди."""
	if not frappe.db.exists("oiAgentCommand", command_id):
		return {"status": "error", "message": "Команду не знайдено"}

	valid_statuses = ["Running", "Completed", "Failed", "Timeout"]
	if status not in valid_statuses:
		return {"status": "error", "message": f"Невалідний статус: {status}"}

	frappe.db.set_value(
		"oiAgentCommand",
		command_id,
		{
			"status": status,
			"exit_code": exit_code,
			"output": (output or "")[:65000],
			"error_output": (error_output or "")[:65000],
			"executed_at": now_datetime() if status in ["Completed", "Failed", "Timeout"] else None,
		},
	)
	frappe.db.commit()
	return {"status": "success"}
