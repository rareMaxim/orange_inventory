# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiAssetAcceptanceItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset_category: DF.Link | None
		is_batched: DF.Check
		item_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		quantity: DF.Int
		serial_numbers: DF.SmallText | None
		unit_cost: DF.Currency
	# end: auto-generated types

	pass
