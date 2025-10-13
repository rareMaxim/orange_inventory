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
		enabled: DF.Check
		is_group: DF.Check
		lft: DF.Int
		naming_series: DF.Literal["ORG-.#####"]
		old_parent: DF.Link | None
		organization_name: DF.Data
		parent_oiorganization: DF.Link | None
		phone: DF.Data | None
		rgt: DF.Int
		tax_code: DF.Data | None
	# end: auto-generated types

	pass
