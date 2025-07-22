# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiAssetItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset_user: DF.Link | None
		asset_user_display: DF.Data | None
		current_owner: DF.Link | None
		current_owner_display: DF.Data | None
		hardware_type: DF.Link
		notes: DF.TextEditor | None
		responsible_person: DF.Link | None
		responsible_person_display: DF.Data | None
		serial_no: DF.Data
		status: DF.Literal["\u041d\u0435\u0432\u0456\u0434\u043e\u043c\u043e", "\u041d\u0430 \u0441\u043a\u043b\u0430\u0434\u0456", "\u0412 \u0435\u043a\u0441\u043f\u043b\u0443\u0430\u0442\u0430\u0446\u0456\u0457", "\u0412 \u0440\u0435\u043c\u043e\u043d\u0442\u0456", "\u0421\u043f\u0438\u0441\u0430\u043d\u043e"]
	# end: auto-generated types

	pass
