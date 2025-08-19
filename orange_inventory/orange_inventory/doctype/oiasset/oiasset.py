# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import now


class oiAsset(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oiassetmovementhistory.oiassetmovementhistory import (
			oiAssetMovementHistory,
		)

		acquisition_date: DF.Date | None
		asset_name: DF.SmallText
		asset_type: DF.Link | None
		asset_user: DF.Link | None
		cost: DF.Currency
		current_owner: DF.Link | None
		hardware_model: DF.Link | None
		image: DF.AttachImage | None
		inventory_no: DF.Data | None
		is_network_device: DF.Check
		location: DF.Data | None
		manufacturer: DF.Link | None
		movement_history: DF.Table[oiAssetMovementHistory]
		original_donor: DF.Link | None
		quantity: DF.Float
		responsible_employee: DF.Link | None
		serial_no: DF.Data | None
		source_project: DF.Link | None
		status: DF.Literal[
			"\u041e\u0447\u0456\u043a\u0443\u0454 \u043f\u0440\u0438\u0439\u043d\u044f\u0442\u0442\u044f",
			"\u041d\u0430 \u0441\u043a\u043b\u0430\u0434\u0456",
			"\u0412 \u0435\u043a\u0441\u043f\u043b\u0443\u0430\u0442\u0430\u0446\u0456\u0457",
			"\u041f\u0435\u0440\u0435\u0434\u0430\u043d\u043e",
			"\u0421\u043f\u0438\u0441\u0430\u043d\u043e",
		]
		total: DF.Currency
	# end: auto-generated types

	def before_save(self):
		self.total = self.cost * self.quantity

	def on_update(self):
		self.create_network_ports_from_model()

	def create_network_ports_from_model(self):
		if not self.hardware_model:
			return

		hardware_model = frappe.get_doc("oiHardwareModel", self.hardware_model)
		if not hardware_model.is_network_device:
			return

		# Перевіряємо, чи порти вже створені, щоб уникнути дублікатів
		if frappe.db.exists("oiNetworkPort", {"asset": self.name}):
			return

		# Перевіряємо, чи існує шаблон портів у моделі
		if not hardware_model.port_templates:
			return

		for port_template in hardware_model.port_templates:
			# Створюємо унікальний ідентифікатор для перевірки
			port_doc_name = f"{self.name}-{port_template.port_name.replace(' ', '_')}"

			# 1. (ВИПРАВЛЕНО) Перевіряємо, чи порт вже існує
			if frappe.db.exists("oiNetworkPort", port_doc_name):
				continue  # Якщо існує, пропускаємо ітерацію

			try:
				new_port = frappe.new_doc("oiNetworkPort")

				# 2. (РЕКОМЕНДАЦІЯ) Дозволяємо Frappe самому встановити name,
				#    але заповнюємо ключові поля для іменування, якщо воно налаштоване.
				new_port.asset = self.name
				new_port.port_name = port_template.port_name
				new_port.port_type = port_template.port_type

				# Якщо правило іменування - "Set by user", то цей рядок спрацює
				# Якщо інше - Frappe його проігнорує і згенерує своє, що теж є прийнятним.
				# Головне, щоб у доктайпі oiNetworkPort було правило, яке гарантує унікальність.
				# Найкраще встановити Naming Rule -> "Expression" і використати:
				# {asset}-{port_name}

				new_port.insert(ignore_permissions=True)

			except frappe.exceptions.DuplicateEntryError:
				# Якщо раптом виникне дублікат (наприклад, при паралельних запитах),
				# ми його просто проігноруємо.
				pass


@frappe.whitelist()
def split_asset(source_asset_name, serial_numbers):
	"""
	Розділяє "груповий" актив:
	1. Оновлює вихідний актив першим серійним номером.
	2. Створює N-1 нових активів для решти серійних номерів.
	"""
	# --- ВИПРАВЛЕННЯ №1: Перевірка та декодування JSON ---
	# Якщо serial_numbers прийшли як рядок, перетворюємо їх на список Python
	if isinstance(serial_numbers, str):
		try:
			serial_numbers = json.loads(serial_numbers)
		except json.JSONDecodeError:
			frappe.throw("Не вдалося обробити список серійних номерів.")

	if not isinstance(serial_numbers, list) or len(serial_numbers) < 2:
		frappe.throw("Необхідно передати список з щонайменше двох серійних номерів.")

	source_asset = frappe.get_doc("oiAsset", source_asset_name)

	if source_asset.quantity != len(serial_numbers):
		frappe.throw("Кількість серійних номерів не співпадає з кількістю активу.")

	# --- ВИПРАВЛЕННЯ №2: Копіюємо документ ДО внесення змін ---
	original_source_asset_copy = source_asset.as_dict()

	# --- КРОК 1: Оновлення вихідного ("батьківського") активу ---
	first_serial = serial_numbers.pop(0)

	source_asset.quantity = 1
	source_asset.serial_no = first_serial
	source_asset.append(
		"movement_history",
		{"date": now(), "movement_type": f"Деталізація (розділено на {len(serial_numbers) + 1} од.)"},
	)
	source_asset.save()

	# --- КРОК 2: Створення нових (N-1) активів для решти серійників ---
	for sn in serial_numbers:
		# Створюємо новий документ з копії ОРИГІНАЛЬНОГО документа
		new_asset = frappe.new_doc("oiAsset")
		new_asset.update(original_source_asset_copy)

		# Встановлюємо нові, унікальні значення
		new_asset.name = None  # Скидаємо ім'я, щоб Frappe згенерував нове
		new_asset.serial_no = sn
		new_asset.quantity = 1

		new_asset.insert(ignore_permissions=True, ignore_mandatory=True)

	return "Success"


def has_permission(doc, user):
	organization = frappe.db.get_value("oiEmployee", {"user": user}, "organization")
	if doc.current_owner == organization:
		return True

	return False


def get_permission_query_conditions(user):
	if frappe.get_system_settings("allow_users_to_see_all_assets"):
		# frappe.msgprint("Усі активи доступні для перегляду.")
		return ""
	# 1. Перевірка для системного адміністратора
	# Якщо поточний користувач - System Manager, він бачить все.
	if "System Manager" in frappe.get_roles(user):
		# frappe.msgprint("Системний адміністратор має доступ до всіх активів.")
		return ""
	# Отримання організації, до якої належить користувач
	organization = frappe.db.get_value("oiEmployee", {"user": user}, "organization")
	# frappe.msgprint(f"User's organization: {organization}")
	if organization:
		# Повернути умову для фільтрації
		return f"(`taboiAsset`.`current_owner` = '{organization}')"
		# pass
	else:
		# Якщо у користувача немає організації, не показувати нічого
		return "(`taboiAsset`.`current_owner` = 'N/A')"
		# pass
