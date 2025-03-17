# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiWorkDaily(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		assigned_to: DF.Link | None
		company: DF.Link | None
		date: DF.Date | None
		description: DF.Text | None
		employee: DF.Link | None
		status: DF.Literal["\u0421\u0442\u0432\u043e\u0440\u0435\u043d\u043e", "\u0412 \u0440\u043e\u0431\u043e\u0442\u0456", "\u0412\u0438\u043a\u043e\u043d\u0430\u043d\u043e"]
		task: DF.Data | None
	# end: auto-generated types

	pass
