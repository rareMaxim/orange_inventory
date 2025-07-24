# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiBasisDocument(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_date: DF.Date
		document_number: DF.Data
		document_type: DF.Literal["\u0420\u0456\u0448\u0435\u043d\u043d\u044f", "\u041d\u0430\u043a\u0430\u0437", "\u0414\u043e\u0433\u043e\u0432\u0456\u0440"]
		scan: DF.Attach | None
		title: DF.SmallText | None
	# end: auto-generated types

	pass
