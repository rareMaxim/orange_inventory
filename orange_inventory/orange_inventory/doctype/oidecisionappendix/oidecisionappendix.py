# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiDecisionAppendix(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from orange_inventory.orange_inventory.doctype.oiassettransferitem.oiassettransferitem import oiAssetTransferItem

		appendix_number: DF.Data | None
		decision: DF.Link
		from_donor: DF.Link | None
		is_new_assets: DF.Check
		items: DF.Table[oiAssetTransferItem]
		to_organization: DF.Link | None
		transaction_type: DF.Literal["\u041e\u0442\u0440\u0438\u043c\u0430\u043d\u043d\u044f", "\u041f\u0435\u0440\u0435\u0434\u0430\u0447\u0430"]
		звідки_організація: DF.Link | None
	# end: auto-generated types

	pass
