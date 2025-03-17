# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiCartridgeService(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from orange_inventory.orange_inventory.doctype.oicartridgeservice_table.oicartridgeservice_table import oiCartridgeServiceTable

		cartridge: DF.Link | None
		cost: DF.Currency
		date: DF.Date | None
		serial_number: DF.Data | None
		table_szsq: DF.Table[oiCartridgeServiceTable]
	# end: auto-generated types

	pass
