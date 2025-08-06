# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiBasisDoc(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		basis_doc_type: DF.Literal["\u0420\u0456\u0448\u0435\u043d\u043d\u044f"]
		decision_date: DF.Date
		decision_number: DF.Data
		scan: DF.Attach | None
		title: DF.SmallText
	# end: auto-generated types

	pass
