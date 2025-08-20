# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiReceiptOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oireceiptorderitem.oireceiptorderitem import (
			oiReceiptOrderItem,
		)

		amended_from: DF.Link | None
		decision: DF.Link
		items: DF.Table[oiReceiptOrderItem]
		receipt_date: DF.Date
		source_name: DF.DynamicLink | None
		source_project: DF.Link | None
		source_type: DF.Literal["oiDonor", "oiOrganization"]
		to_organization: DF.Link | None
	# end: auto-generated types

	def before_submit(self):
		"""
		Виконує фінальну валідацію перед підтвердженням документа.
		Блокує підтвердження, якщо є помилки.
		"""
		errors = []
		all_serials_to_check = []

		# Спочатку збираємо всі серійні номери з документа
		for item in self.items:
			if item.serial_numbers:
				serials = [s.strip() for s in item.serial_numbers.replace("\n", ",").split(",") if s.strip()]
				all_serials_to_check.extend(serials)

		# Перевіряємо наявність цих серійних номерів в базі даних ОДНИМ запитом
		if all_serials_to_check:
			existing_serials = frappe.db.get_all(
				"oiAsset",
				filters={"serial_no": ("in", list(set(all_serials_to_check)))},
				fields=["serial_no"],
				pluck="serial_no",
			)
			existing_serials_set = set(existing_serials)
		else:
			existing_serials_set = set()

		# Тепер проходимо по рядках і формуємо помилки
		for i, item in enumerate(self.items):
			if not item.asset_name:
				continue

			serials = []
			if item.serial_numbers:
				serials = [s.strip() for s in item.serial_numbers.replace("\n", ",").split(",") if s.strip()]

			# 1. Перевірка на дублікати всередині одного поля
			if len(serials) != len(set(serials)):
				errors.append(
					f"<b>Рядок {i+1} ({item.asset_name})</b>: Знайдено дублікати в серійних номерах."
				)

			# 2. Перевірка відповідності кількості
			if item.qty > 1 and serials and len(serials) != item.qty:
				errors.append(
					f"<b>Рядок {i+1} ({item.asset_name})</b>: Кількість серійних номерів ({len(serials)}) не співпадає з кількістю активів ({int(item.qty)})."
				)

			# 3. Перевірка на існування серійного номера в базі даних
			for sn in serials:
				if sn in existing_serials_set:
					# Створюємо посилання на існуючий актив для зручності користувача
					asset_link = frappe.get_desk_link(
						"oiAsset", frappe.get_value("oiAsset", {"serial_no": sn}, "name")
					)
					errors.append(
						f"<b>Рядок {i+1} ({item.asset_name})</b>: Серійний номер <b>{sn}</b> вже існує в системі. {asset_link}"
					)

		if errors:
			error_message = (
				"<b>Неможливо підтвердити документ. Виправте наступні помилки:</b><br>" + "<br>".join(errors)
			)
			frappe.throw(error_message, title="Помилка валідації")

	def on_submit(self):
		"""
		При затвердженні 'Прибуткового ордеру' створює записи в 'oiAsset'.
		"""
		for item in self.items:
			serial_numbers = []
			if item.serial_numbers:
				processed_string = item.serial_numbers.replace("\n", ",")
				serial_numbers = [s.strip() for s in processed_string.split(",") if s.strip()]

			if item.qty > 1 and len(serial_numbers) != item.qty:
				self.create_single_asset(item, item.qty, item.serial_numbers)
			else:
				if item.qty == 1:
					serial = serial_numbers[0] if serial_numbers else None
					self.create_single_asset(item, 1, serial)
				else:
					for sn in serial_numbers:
						self.create_single_asset(item, 1, sn)

	def create_single_asset(self, item, qty, serial_no):
		"""
		Допоміжна функція для створення одного запису 'oiAsset'.
		"""
		new_asset = frappe.new_doc("oiAsset")
		new_asset.asset_name = item.asset_name
		new_asset.asset_type = item.asset_type
		new_asset.quantity = qty
		new_asset.cost = item.rate
		new_asset.serial_no = serial_no
		new_asset.status = "На складі"

		new_asset.acquisition_date = self.receipt_date
		new_asset.current_owner = self.to_organization
		new_asset.source_project = self.source_project

		if self.source_type == "oiDonor":
			new_asset.original_donor = self.source_name

		new_asset.insert(ignore_permissions=True)

		movement_data = {
			"date": self.receipt_date,
			"movement_type": "Надходження",
			"to_organization": self.to_organization,
			"reference_appendix": self.decision,
			"from_source_type": self.source_type,
			"from_source_name": self.source_name,
		}
		if self.source_type == "oiOrganization":
			movement_data["from_organization"] = self.source_name

		new_asset.append("movement_history", movement_data)
		new_asset.save()
