# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import json
import re
from datetime import datetime

import frappe
from dateutil.relativedelta import relativedelta
from frappe.model.document import Document
from frappe.utils import getdate, now, today


class oiAsset(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oiassetcomponent.oiassetcomponent import (
			oiAssetComponent,
		)
		from orange_inventory.orange_inventory.doctype.oiassetmovementhistory.oiassetmovementhistory import (
			oiAssetMovementHistory,
		)

		acquisition_date: DF.Date | None
		asset_name: DF.SmallText
		asset_type: DF.Link | None
		asset_user: DF.Link | None
		components: DF.Table[oiAssetComponent]
		cost: DF.Currency
		current_owner: DF.Link | None
		enabled: DF.Check
		hardware_model: DF.Link | None
		image: DF.AttachImage | None
		inventory_date: DF.Date | None
		inventory_no: DF.Data | None
		inventory_status: DF.Data | None
		is_network_device: DF.Check
		location: DF.Link | None
		manufacturer: DF.Link | None
		movement_history: DF.Table[oiAssetMovementHistory]
		naming_series: DF.Literal["ASSET-.#####"]
		original_donor: DF.Link | None
		parent_asset: DF.Link | None
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
		type: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.update_inventory_status()
		self.validate_components()
		self.update_component_parent_assets()

	def before_save(self):
		self.total = self.cost * self.quantity

	def on_update(self):
		self.create_network_ports_from_model()

	def update_inventory_status(self):
		"""Оновлює статус інвентаризації на основі дати останньої інвентаризації"""
		if not self.inventory_date:
			self.inventory_status = "Інвентаризація не проводилась"
			return

		inventory_date = getdate(self.inventory_date)
		current_date = getdate(today())
		delta = relativedelta(current_date, inventory_date)
		months_diff = delta.years * 12 + delta.months

		if months_diff >= 12:
			self.inventory_status = "⚠️ Інвентаризація не проводилась більше 12 міс."
		elif months_diff >= 9:
			self.inventory_status = "⚠️ Інвентаризація не проводилась більше 9 міс."
		elif months_diff >= 6:
			self.inventory_status = "⚠️ Інвентаризація не проводилась більше 6 міс."
		elif months_diff >= 3:
			self.inventory_status = "⚠️ Інвентаризація не проводилась більше 3 міс."
		else:
			self.inventory_status = "✓ Інвентаризація актуальна"

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

	def validate_components(self):
		"""Валідує компоненти активу"""
		if not self.components:
			return

		# Перевіряємо на дублікати компонентів
		component_assets = [comp.component_asset for comp in self.components]
		if len(component_assets) != len(set(component_assets)):
			frappe.throw("Не можна додати один і той же компонент двічі")

		# Перевіряємо, чи компонент не є батьківським активом (запобігаємо циклічним залежностям)
		for comp in self.components:
			if comp.component_asset == self.name:
				frappe.throw("Актив не може бути компонентом самого себе")

			# Перевіряємо, чи компонент вже встановлено в інший актив
			existing_parent = frappe.db.get_value("oiAsset", comp.component_asset, "parent_asset")
			if existing_parent and existing_parent != self.name:
				frappe.throw(
					f"Актив {comp.component_asset} вже встановлено в {existing_parent}. "
					"Спочатку видаліть його звідти."
				)

	def update_component_parent_assets(self):
		"""Оновлює поле parent_asset для всіх компонентів"""
		if not self.components:
			# Якщо компонентів немає, очищаємо parent_asset для всіх активів, які раніше були компонентами
			frappe.db.sql(
				"""
				UPDATE `taboiAsset`
				SET parent_asset = NULL
				WHERE parent_asset = %s
			""",
				(self.name,),
			)
			return

		# Отримуємо список поточних компонентів
		current_components = [comp.component_asset for comp in self.components]

		# Оновлюємо parent_asset для поточних компонентів
		for comp_name in current_components:
			frappe.db.set_value("oiAsset", comp_name, "parent_asset", self.name, update_modified=False)

		# Очищаємо parent_asset для компонентів, які були видалені
		frappe.db.sql(
			"""
			UPDATE `taboiAsset`
			SET parent_asset = NULL
			WHERE parent_asset = %s
			AND name NOT IN ({})
		""".format(",".join(["%s"] * len(current_components))),
			tuple([self.name] + current_components),
		)


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
	"""
	Визначає умови для фільтрації активів на основі ролей користувача.

	Returns:
	        str: SQL умова для WHERE clause або порожній рядок для повного доступу
	"""
	# 1. Перевірка системного налаштування для глобального доступу
	if frappe.get_system_settings("allow_users_to_see_all_assets"):
		return ""

	# 2. Перевірка для привілейованих ролей (виправлено критичний bug)
	user_roles = frappe.get_roles(user)
	privileged_roles = {"System Manager", "Maintenance Manager"}

	if any(role in user_roles for role in privileged_roles):
		return ""

	# 3. Фільтрація по організації користувача
	organization = frappe.db.get_value("oiEmployee", {"user": user}, "organization")

	if organization:
		# Використовуємо безпечний спосіб для SQL умови
		return f"(`taboiAsset`.`current_owner` = {frappe.db.escape(organization)})"
	else:
		# Якщо у користувача немає організації, не показувати нічого
		return "(`taboiAsset`.`current_owner` = 'N/A')"


@frappe.whitelist()
def get_network_ports_with_details(asset_name):
	"""
	Отримує мережеві порти для вказаного активу, включаючи деталі
	про підключений актив та порт, з природним сортуванням.
	"""
	if not frappe.db.exists("oiAsset", asset_name):
		return []

	# 1. Отримуємо всі порти для поточного активу (без сортування в базі)
	ports = frappe.get_all(
		"oiNetworkPort",
		fields=[
			"name",
			"port_name",
			"port_type",
			"connection",
			"is_wan_connection",
			"connected_asset",
		],
		filters={"asset": asset_name},
	)

	# 2. Збираємо ID підключених активів та портів
	connected_asset_ids = {p.get("connected_asset") for p in ports if p.get("connected_asset")}
	connected_port_ids = {p.get("connection") for p in ports if p.get("connection")}

	# 3. Отримуємо назви активів одним запитом
	asset_names = {}
	if connected_asset_ids:
		asset_docs = frappe.get_all(
			"oiAsset", fields=["name", "asset_name"], filters={"name": ("in", list(connected_asset_ids))}
		)
		asset_names = {doc.name: doc.asset_name for doc in asset_docs}

	# 4. Отримуємо назви портів одним запитом
	port_names = {}
	if connected_port_ids:
		port_docs = frappe.get_all(
			"oiNetworkPort", fields=["name", "port_name"], filters={"name": ("in", list(connected_port_ids))}
		)
		port_names = {doc.name: doc.port_name for doc in port_docs}

	# 5. Додаємо отримані назви до списку портів
	for port in ports:
		if port.get("connected_asset"):
			port["connected_asset_name"] = asset_names.get(port.get("connected_asset"))
		if port.get("connection"):
			port["connected_port_name"] = port_names.get(port.get("connection"))

	# 6. ✨ СОРТУЄМО РЕЗУЛЬТАТ ПРИРОДНИМ ЧИНОМ ✨
	def natural_sort_key(s):
		# Ця функція розділяє назву порту на текст і числа (напр., "Eth 10" -> ['Eth ', 10])
		return [
			int(text) if text.isdigit() else text.lower()
			for text in re.split("([0-9]+)", s.get("port_name", ""))
		]

	ports.sort(key=natural_sort_key)

	return ports


@frappe.whitelist()
def set_inventory_date(asset_name, inventory_date=None, location=None):
	"""
	Встановлює дату інвентаризації для активу та опціонально оновлює місцезнаходження
	"""
	if not frappe.db.exists("oiAsset", asset_name):
		frappe.throw("Актив не знайдено")

	asset = frappe.get_doc("oiAsset", asset_name)

	# Встановлюємо дату інвентаризації
	asset.inventory_date = inventory_date if inventory_date else today()

	# Оновлюємо місцезнаходження, якщо воно вказано
	if location:
		asset.location = location

	asset.save()

	return {"success": True, "inventory_date": asset.inventory_date, "location": asset.location}


@frappe.whitelist()
def get_inventory_status(asset_name):
	"""
	Повертає статус інвентаризації для активу з кольором для відображення
	"""
	if not frappe.db.exists("oiAsset", asset_name):
		return None

	asset = frappe.get_doc("oiAsset", asset_name)

	if not asset.inventory_date:
		return {"status": "Інвентаризація не проводилась", "months_since_inventory": None, "color": "gray"}

	inventory_date = getdate(asset.inventory_date)
	current_date = getdate(today())
	delta = relativedelta(current_date, inventory_date)
	months_diff = delta.years * 12 + delta.months

	# Визначаємо статус та колір
	if months_diff >= 12:
		status = "⚠️ Інвентаризація > 12 міс."
		color = "#d9534f"  # червоний
	elif months_diff >= 9:
		status = "⚠️ Інвентаризація > 9 міс."
		color = "#f0ad4e"  # помаранчевий
	elif months_diff >= 6:
		status = "⚠️ Інвентаризація > 6 міс."
		color = "#ff9800"  # жовто-помаранчевий
	elif months_diff >= 3:
		status = "⚠️ Інвентаризація > 3 міс."
		color = "#5bc0de"  # блакитний
	else:
		status = "✓ Інвентаризація актуальна"
		color = "#5cb85c"  # зелений

	return {"status": status, "months_since_inventory": months_diff, "color": color}
