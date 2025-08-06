# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiAsset(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from orange_inventory.orange_inventory.doctype.oiassetmovementhistory.oiassetmovementhistory import oiAssetMovementHistory

		acquisition_date: DF.Date | None
		asset_model: DF.Data | None
		asset_name: DF.SmallText
		asset_type: DF.Link | None
		cost: DF.Currency
		current_owner: DF.Link | None
		image: DF.AttachImage | None
		inventory_no: DF.Data | None
		location: DF.Data | None
		movement_history: DF.Table[oiAssetMovementHistory]
		original_donor: DF.Link | None
		quantity: DF.Float
		responsible_employee: DF.Link | None
		serial_no: DF.Data | None
		source_project: DF.Link | None
		status: DF.Literal["\u041e\u0447\u0456\u043a\u0443\u0454 \u043f\u0440\u0438\u0439\u043d\u044f\u0442\u0442\u044f", "\u041d\u0430 \u0441\u043a\u043b\u0430\u0434\u0456", "\u0412 \u0435\u043a\u0441\u043f\u043b\u0443\u0430\u0442\u0430\u0446\u0456\u0457", "\u041f\u0435\u0440\u0435\u0434\u0430\u043d\u043e", "\u0421\u043f\u0438\u0441\u0430\u043d\u043e"]
		total: DF.Currency
	# end: auto-generated types

	def before_save(self):
		self.total = self.cost * self.quantity
