# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

import hashlib
import hmac
import json
import re
from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

# Небезпечні патерни команд
DANGEROUS_PATTERNS = [
	# Windows destructive
	r"format\s+[a-z]:",
	r"del\s+/[sfq]",
	r"rd\s+/s",
	r"rmdir\s+/s",
	r"diskpart",
	r"cipher\s+/w",
	# Linux destructive
	r"rm\s+-rf\s+/",
	r"rm\s+-rf\s+/\*",
	r"mkfs\.",
	r"dd\s+if=.+of=/dev/",
	r":\(\)\{\s*:\|:&\s*\};:",  # fork bomb
	# Registry/system
	r"reg\s+delete\s+hk",
	r"bcdedit",
	# Network exfiltration
	r"certutil.*-urlcache",
	r"bitsadmin.*transfer",
	r"invoke-webrequest.*-outfile",
	# Credential theft
	r"mimikatz",
	r"sekurlsa",
	r"lsadump",
	# Disable security
	r"set-mppreference.*-disablerealtimemonitoring",
	r"netsh\s+advfirewall\s+set.*state\s+off",
]


def get_command_signing_key() -> str:
	"""
	Отримує секретний ключ для підпису команд з налаштувань.
	"""
	try:
		key = frappe.db.get_single_value("Orange Inventory Settings", "command_signing_key")
		if key:
			return key
	except Exception:
		pass

	# Fallback: використовуємо ключ на основі site secret
	frappe.log_error(
		"Command signing key not configured. Please set it in Orange Inventory Settings.", "Security Warning"
	)
	return hashlib.sha256(frappe.local.conf.get("secret_key", "default").encode()).hexdigest()


def sign_command(command_id: str, agent_id: str, command: str, expires_at: str) -> str:
	"""
	Створює HMAC-SHA256 підпис для команди.

	Args:
	    command_id: ID команди
	    agent_id: ID агента
	    command: текст команди
	    expires_at: час закінчення дії

	Returns:
	    str: hex-encoded HMAC signature
	"""
	key = get_command_signing_key()
	message = f"{command_id}:{agent_id}:{command}:{expires_at}"
	signature = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
	return signature


class oiAgentCommand(Document):
	def before_insert(self):
		# Встановлюємо користувача який створив команду
		self.created_by_user = frappe.session.user

		# Встановлюємо термін дії за замовчуванням (1 година)
		if not self.expires_at:
			self.expires_at = now_datetime() + timedelta(hours=1)

	def validate(self):
		self.validate_permissions()
		self.validate_template()
		self.validate_command_safety()
		self.validate_timeout()
		self.validate_expiry()
		self.validate_approval()

	def validate_permissions(self):
		"""Перевіряє права доступу."""
		if not frappe.has_permission("oiAgentCommand", "create"):
			frappe.throw("У вас немає прав на створення команд для агентів")

		# Якщо використовується шаблон - перевіряємо ролі
		if self.command_template:
			template = frappe.get_doc("oiCommandTemplate", self.command_template)
			if template.allowed_roles:
				allowed_roles = [r.strip() for r in template.allowed_roles.split(",")]
				user_roles = frappe.get_roles()
				if not any(role in user_roles for role in allowed_roles):
					frappe.throw(f"Ваша роль не дозволяє використовувати шаблон '{self.command_template}'")

	def validate_template(self):
		"""Валідація шаблону команди."""
		if not self.command_template:
			# Custom команда - потребує System Manager
			if "System Manager" not in frappe.get_roles():
				frappe.throw(
					"Тільки System Manager може створювати custom команди. " "Використовуйте шаблон команди."
				)
			return

		template = frappe.get_doc("oiCommandTemplate", self.command_template)

		if not template.enabled:
			frappe.throw(f"Шаблон '{self.command_template}' вимкнено")

		# Встановлюємо тип команди з шаблону
		self.command_type = template.command_type

		# Якщо є аргументи - рендеримо команду з шаблону
		if self.arguments:
			try:
				params = json.loads(self.arguments)
				self.command = template.render_command(params)
			except json.JSONDecodeError:
				frappe.throw("Невалідний JSON в аргументах")
		else:
			self.command = template.command_template

		# Встановлюємо таймаут з шаблону якщо не вказано
		if not self.timeout_seconds or self.timeout_seconds > template.max_timeout_seconds:
			self.timeout_seconds = template.max_timeout_seconds

	def validate_command_safety(self):
		"""Перевіряє команду на небезпечні патерни."""
		if not self.command:
			return

		cmd_lower = self.command.lower()

		for pattern in DANGEROUS_PATTERNS:
			if re.search(pattern, cmd_lower, re.IGNORECASE):
				frappe.throw(
					"Команда містить заборонений патерн. " "Такі команди заблоковані з міркувань безпеки."
				)

	def validate_timeout(self):
		"""Валідація timeout."""
		if self.timeout_seconds:
			if self.timeout_seconds < 1:
				frappe.throw("Таймаут повинен бути більше 0")
			if self.timeout_seconds > 3600:
				frappe.throw("Таймаут не може бути більше 3600 секунд (1 година)")

	def validate_expiry(self):
		"""Перевіряє термін дії."""
		if self.expires_at:
			expires = get_datetime(self.expires_at)
			now = now_datetime()

			# Не можна встановити в минулому
			if expires < now:
				frappe.throw("Термін дії не може бути в минулому")

			# Максимум 24 години
			max_expiry = now + timedelta(hours=24)
			if expires > max_expiry:
				frappe.throw("Термін дії не може бути більше 24 годин")

	def validate_approval(self):
		"""Перевіряє схвалення для команд з високим ризиком."""
		if not self.command_template:
			return

		template = frappe.get_doc("oiCommandTemplate", self.command_template)

		if template.requires_approval and not self.approved_by_user:
			# Дозволяємо створити в статусі Pending, але не виконувати
			if self.status not in ["Pending", "Cancelled"]:
				frappe.throw("Ця команда потребує схвалення іншим адміністратором перед виконанням")

	def before_save(self):
		"""Генеруємо підпис перед збереженням."""
		if self.status == "Pending" and not self.signature:
			self.generate_signature()

	def generate_signature(self):
		"""Генерує HMAC підпис для команди."""
		# Отримуємо agent_id
		agent_id = frappe.db.get_value("oiAgent", self.agent, "agent_id")
		if not agent_id:
			return

		expires_str = str(self.expires_at) if self.expires_at else ""

		self.signature = sign_command(self.name or "new", agent_id, self.command, expires_str)

	def on_update(self):
		"""Логування змін."""
		if self.has_value_changed("status"):
			self.log_status_change()

		# Перегенеруємо підпис якщо змінилась команда
		if self.has_value_changed("command") or self.has_value_changed("expires_at"):
			self.generate_signature()
			self.db_set("signature", self.signature, update_modified=False)

	def log_status_change(self):
		"""Детальне логування змін статусу."""
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "oiAgentCommand",
				"reference_name": self.name,
				"content": f"Статус змінено на <b>{self.status}</b> користувачем {frappe.session.user}",
			}
		).insert(ignore_permissions=True)

	@frappe.whitelist()
	def approve(self):
		"""Схвалення команди іншим адміністратором."""
		if self.approved_by_user:
			frappe.throw("Команда вже схвалена")

		if self.created_by_user == frappe.session.user:
			frappe.throw("Ви не можете схвалити власну команду")

		if "System Manager" not in frappe.get_roles() and "Maintenance Manager" not in frappe.get_roles():
			frappe.throw("Тільки System Manager або Maintenance Manager може схвалювати команди")

		self.approved_by_user = frappe.session.user
		self.save()

		return {"status": "success", "message": "Команду схвалено"}
