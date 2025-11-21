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
		creation_date: DF.Date | None
		font_px: DF.Int
		items: DF.Table[oiAssetLabelItem]
		label_gap_mm: DF.Int
		label_height_mm: DF.Int
		label_width_mm: DF.Int
		logo_image: DF.AttachImage | None
		organization_name: DF.Data | None
		page_margin_mm: DF.Int
		print_mode: DF.Literal["Color", "Monochrome"]
		qr_size_mm: DF.Int
		show_inventory_no: DF.Check
		show_location: DF.Check
		show_logo: DF.Check
		show_mvo: DF.Check
		show_organization: DF.Check
		show_serial_no: DF.Check
		title: DF.Data
	# end: auto-generated types

	pass
