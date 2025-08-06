# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiOrganization(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		abbreviation: DF.Data | None
		contact_person: DF.Data | None
		email: DF.Data | None
		organization_name: DF.Data
		phone: DF.Data | None
		tax_code: DF.Data | None
	# end: auto-generated types

	pass
