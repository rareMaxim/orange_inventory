# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiDonor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contacts: DF.TextEditor | None
		country: DF.Link | None
		donor_name: DF.Data | None
		donor_short_name: DF.Data | None
		donor_type: DF.Literal["\u0411\u043b\u0430\u0433\u043e\u0434\u0456\u0439\u043d\u0438\u0439 \u0444\u043e\u043d\u0434", "\u0413\u041e", "\u041f\u0440\u0438\u0432\u0430\u0442\u043d\u0430 \u043e\u0441\u043e\u0431\u0430", "\u041a\u043e\u043c\u0435\u0440\u0446\u0456\u0439\u043d\u0430 \u043e\u0440\u0433\u0430\u043d\u0456\u0437\u0430\u0446\u0456\u044f", "\u0406\u043d\u043e\u0437\u0435\u043c\u043d\u0438\u0439 \u0443\u0440\u044f\u0434", "\u0417\u0430\u043a\u0443\u043f\u0456\u0432\u043b\u044f", "\u041f\u0435\u0440\u0435\u0434\u0430\u0447\u0430 \u0432\u0456\u0434 \u0456\u043d\u0448\u043e\u0457 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438", "\u0406\u043d\u0448\u0435"]
	# end: auto-generated types

	pass
