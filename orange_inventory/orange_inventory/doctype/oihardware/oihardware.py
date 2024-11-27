# Copyright (c) 2024, Maxim Sysoev and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class oiHardware(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset_tag: DF.Data | None
		company: DF.Link | None
		contract: DF.Link | None
		decommissioning_contract: DF.Link | None
		fin_resp_company: DF.Link | None
		fin_resp_deparnament: DF.Link | None
		fin_resp_user_name: DF.Link | None
		financially_responsible_person: DF.Link | None
		inventory_date: DF.Date | None
		manufacturer: DF.Link | None
		model: DF.Link | None
		picture: DF.AttachImage | None
		purchase_cost: DF.Currency
		purchase_date: DF.Date | None
		serial_number: DF.Data | None
		status: DF.Link | None
		title: DF.Data | None
		type: DF.Link | None
		user: DF.Link | None
		user_name: DF.Link | None
	# end: auto-generated types

	pass
