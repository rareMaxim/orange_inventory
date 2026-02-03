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
		# Password field потребує спеціального методу для отримання
		from frappe.utils.password import get_decrypted_password

		key = get_decrypted_password(
			"Orange Inventory Settings", "Orange Inventory Settings", "command_signing_key"
		)
		if key:
			return key
	except Exception:
		pass

	# Fallback: використовуємо ключ на основі site secret
	frappe.log_error(
		"Command signing key not configured. Please set it in Orange Inventory Settings.", "Security Warning"
	)
	return hashlib.sha256(frappe.local.conf.get("secret_key", "default").encode()).hexdigest()


def normalize_datetime_for_signature(dt) -> str:
	"""
	Нормалізує datetime до стандартного формату для підпису.
	Формат: YYYY-MM-DD HH:MM:SS (без мікросекунд)
	"""
	if not dt:
		return ""
	if isinstance(dt, str):
		# Якщо це вже рядок - обрізаємо мікросекунди
		if "." in dt:
			return dt.split(".")[0]
		return dt
	# datetime object
	return dt.strftime("%Y-%m-%d %H:%M:%S")


def sign_command(command_id: str, agent_id: str, command: str, expires_at) -> str:
	"""
	Створює HMAC-SHA256 підпис для команди.

	Args:
	    command_id: ID команди
	    agent_id: ID агента
	    command: текст команди
	    expires_at: час закінчення дії (datetime або str)

	Returns:
	    str: hex-encoded HMAC signature
	"""
	key = get_command_signing_key()
	# Нормалізуємо expires_at для консистентності
	normalized_expires = normalize_datetime_for_signature(expires_at)
	message = f"{command_id}:{agent_id}:{command}:{normalized_expires}"
	signature = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
	return signature


class oiAgentCommand(Document):
	def before_insert(self):
		# Встановлюємо користувача який створив команду
		self.created_by_user = frappe.session.user

		# Встановлюємо термін дії за замовчуванням (1 година)
		if not self.expires_at:
			self.expires_at = now_datetime() + timedelta(hours=1)

	def before_validate(self):
		"""Заповнюємо поля з шаблону ДО перевірки обов'язкових полів."""
		if self.command_template:
			self.fill_from_template()

	def fill_from_template(self):
		"""Заповнює команду та тип з шаблону."""
		template = frappe.get_doc("oiCommandTemplate", self.command_template)

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
			# Перевіряємо що команда заповнена для custom
			if not self.command:
				frappe.throw("Для custom команди потрібно вказати команду")
			return

		template = frappe.get_doc("oiCommandTemplate", self.command_template)

		if not template.enabled:
			frappe.throw(f"Шаблон '{self.command_template}' вимкнено")

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
		"""Генеруємо підпис перед збереженням (тільки для існуючих документів)."""
		# Для нових документів підпис генерується в after_insert
		# бо self.name ще не встановлено
		if not self.is_new() and self.status == "Pending" and not self.signature:
			self.generate_signature()

	def after_insert(self):
		"""Генеруємо підпис після створення документа (коли вже є name)."""
		if self.status == "Pending":
			self.generate_signature()
			self.db_set("signature", self.signature, update_modified=False)

	def generate_signature(self):
		"""Генерує HMAC підпис для команди."""
		# Отримуємо agent_id
		agent_id = frappe.db.get_value("oiAgent", self.agent, "agent_id")
		if not agent_id:
			return

		# Передаємо expires_at напряму - sign_command нормалізує його
		self.signature = sign_command(self.name or "new", agent_id, self.command, self.expires_at)

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
	def regenerate_signature(self):
		"""Перегенерує підпис команди (для виправлення невалідних підписів)."""
		self.generate_signature()
		self.db_set("signature", self.signature, update_modified=False)
		return {"status": "success", "signature": self.signature}

	@frappe.whitelist()
	def debug_signature(self):
		"""Показує дані що використовуються для підпису (для діагностики)."""
		agent_id = frappe.db.get_value("oiAgent", self.agent, "agent_id")
		expires_normalized = normalize_datetime_for_signature(self.expires_at)
		message = f"{self.name}:{agent_id}:{self.command}:{expires_normalized}"
		key = get_command_signing_key()

		return {
			"command_id": self.name,
			"agent_id": agent_id,
			"command_length": len(self.command) if self.command else 0,
			"expires_at_normalized": expires_normalized,
			"message_for_signing": message,
			"current_signature": self.signature,
			"key_configured": bool(key),
			"key_prefix": key[:8] + "..." if key and len(key) >= 8 else "NOT SET",
			"key_length": len(key) if key else 0,
		}

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
