# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiContractType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from_balance: DF.Check
		on_balance: DF.Check
		remove_from_balance: DF.Check
	# end: auto-generated types

	pass
