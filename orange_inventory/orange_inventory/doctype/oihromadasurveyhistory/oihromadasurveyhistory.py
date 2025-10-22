# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiHromadaSurveyHistory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bool_value: DF.Check
		changed_by: DF.Link | None
		int_value: DF.Int
		notes: DF.SmallText | None
		period: DF.Data | None
		recorded_date: DF.Datetime
		value_display: DF.Data | None
	# end: auto-generated types

	pass
