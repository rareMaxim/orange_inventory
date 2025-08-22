# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHardwareModel(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oinetworkporttemplate.oinetworkporttemplate import (
			oiNetworkPortTemplate,
		)

		hardware_type: DF.Link | None
		is_network_device: DF.Check
		manufacturer: DF.Link
		model_image: DF.AttachImage | None
		model_name: DF.Data
		port_templates: DF.Table[oiNetworkPortTemplate]
	# end: auto-generated types

	pass


@frappe.whitelist()
def sync_ports_to_assets(model_name):
	"""
	Знаходить усі активи, що використовують цю модель, та створює для них
	відсутні мережеві порти на основі поточних шаблонів у моделі.
	"""
	model_doc = frappe.get_doc("oiHardwareModel", model_name)
	if not model_doc.is_network_device or not model_doc.port_templates:
		frappe.msgprint("Ця модель не є мережевим пристроєм або не має шаблонів портів для синхронізації.")
		return

	# Знаходимо всі активи, пов'язані з цією моделлю
	linked_assets = frappe.get_all("oiAsset", filters={"hardware_model": model_name}, pluck="name")

	if not linked_assets:
		frappe.msgprint("Не знайдено активів, що використовують цю модель.")
		return

	created_count = 0
	checked_assets = 0
	# Проходимо по кожному активу
	for asset_name in linked_assets:
		checked_assets += 1

		# Отримуємо існуючі порти для цього активу, щоб уникнути дублікатів
		existing_ports = frappe.get_all("oiNetworkPort", filters={"asset": asset_name}, pluck="port_name")

		# Проходимо по шаблонах у моделі
		for port_template in model_doc.port_templates:
			# Якщо порт з такою назвою ще не існує для цього активу, створюємо його
			if port_template.port_name not in existing_ports:
				try:
					new_port = frappe.new_doc("oiNetworkPort")
					new_port.asset = asset_name
					new_port.port_name = port_template.port_name
					new_port.port_type = port_template.port_type
					new_port.insert(ignore_permissions=True)
					created_count += 1
				except frappe.exceptions.DuplicateEntryError:
					# На випадок рідкісних паралельних запитів, просто ігноруємо помилку
					pass

	frappe.msgprint(
		f"Синхронізацію завершено. Перевірено {checked_assets} актив(ів). Створено {created_count} нових портів."
	)
