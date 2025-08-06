# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiHardwareModel(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		hardware_type: DF.Link | None
		manufacturer: DF.Link
		model_image: DF.AttachImage | None
		model_name: DF.Data
	# end: auto-generated types

	pass
