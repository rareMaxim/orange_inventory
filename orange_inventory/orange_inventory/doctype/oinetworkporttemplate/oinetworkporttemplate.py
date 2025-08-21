# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiNetworkPortTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		port_name: DF.Data
		port_type: DF.Literal["RJ45", "WAN", "SFP", "SFP+", "QSFP", "Fiber", "WiFi"]
	# end: auto-generated types

	pass
