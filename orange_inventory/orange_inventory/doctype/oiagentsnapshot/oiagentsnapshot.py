# Copyright (c) 2026, Maxim Sysoev and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class oiAgentSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent: DF.Link
		cpu_usage: DF.Percent
		current_user: DF.Data | None
		disk_usage: DF.Code | None
		ip_addresses: DF.Code | None
		ram_usage: DF.Percent
		timestamp: DF.Datetime
		uptime_seconds: DF.Int
	# end: auto-generated types

	pass
