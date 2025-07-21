# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiHardware(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from orange_inventory.orange_inventory.doctype.oiasset_item.oiasset_item import oiAssetItem

		acquired_from: DF.Link | None
		acquisition_date: DF.Date | None
		acquisition_type: DF.Literal["\u041f\u043e\u043a\u0443\u043f\u043a\u0430", "\u041f\u043e\u0436\u0435\u0440\u0442\u0432\u0430", "\u041f\u0435\u0440\u0435\u0434\u0430\u0447\u0430"]
		asset_category: DF.Link
		asset_items: DF.Table[oiAssetItem]
		asset_tag: DF.Data | None
		company: DF.Link | None
		fin_resp_company: DF.Link | None
		fin_resp_deparnament: DF.Link | None
		fin_resp_user_name: DF.Link | None
		financially_responsible_person: DF.Link | None
		inventory_date: DF.Date | None
		is_batched_asset: DF.Check
		manufacturer: DF.Link | None
		model: DF.Link | None
		picture: DF.AttachImage | None
		purchase_cost: DF.Currency
		purchase_date: DF.Date | None
		quantity: DF.Float
		serial_number: DF.Data | None
		source_document: DF.Attach | None
		status: DF.Link | None
		title: DF.Data | None
		type: DF.Link | None
		unit_cost: DF.Currency
		user: DF.Link | None
		user_name: DF.Link | None
	# end: auto-generated types

	pass
