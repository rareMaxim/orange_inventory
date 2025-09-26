# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiAssetLabelBatch(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oiassetlabelitem.oiassetlabelitem import (
			oiAssetLabelItem,
		)

		columns: DF.Int
		font_px: DF.Int
		items: DF.Table[oiAssetLabelItem]
		label_height_mm: DF.Int
		label_width_mm: DF.Int
		page_margin_mm: DF.Int
		qr_size_mm: DF.Int
		show_inventory_no: DF.Check
		show_serial_no: DF.Check
		title: DF.Data | None
		відступ_між_ярликами_мм: DF.Int
	# end: auto-generated types

	pass
