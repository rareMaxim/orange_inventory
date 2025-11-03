# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiAssetComponent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset_name: DF.Data | None
		component_asset: DF.Link
		installation_date: DF.Date | None
		notes: DF.SmallText | None
		serial_no: DF.Data | None
	# end: auto-generated types

	pass
