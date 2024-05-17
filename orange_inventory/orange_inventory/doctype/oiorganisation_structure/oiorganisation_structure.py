# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.utils.nestedset import NestedSet


class oiOrganisationStructure(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		edrpou: DF.Data | None
		full_name: DF.SmallText | None
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		parent_oiorganisation_structure: DF.Link | None
		rgt: DF.Int
		short_name: DF.Data | None
	# end: auto-generated types

	pass
