# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiLocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		building: DF.Data
		city: DF.Autocomplete | None
		enabled: DF.Check
		floor: DF.Data | None
		full_address: DF.Data | None
		latitude: DF.Float
		longitude: DF.Float
		naming_series: DF.Literal["location-.#####"]
		note: DF.SmallText | None
		responsible_name: DF.Data | None
		responsible_phone: DF.Data | None
		responsible_user: DF.Link | None
		room: DF.Data
		room_type: DF.Literal[
			"\u041a\u0430\u0431\u0456\u043d\u0435\u0442",
			"\u0421\u043a\u043b\u0430\u0434",
			"\u041f\u0435\u0440\u0435\u0433\u043e\u0432\u043e\u0440\u043d\u0430",
			"\u0425\u043e\u043b",
			"\u0406\u043d\u0448\u0435",
		]
		street: DF.Data | None
	# end: auto-generated types

	def before_validate(self):
		def _norm(v):
			return str(v).strip() if v not in (None, "") else ""

		def _tag(label: str, v):
			v = _norm(v)
			return f"{label} {v}" if v else ""

		addr_parts = [
			_norm(getattr(self, "city", None)),
			_norm(getattr(self, "street", None)),
			_norm(getattr(self, "house_no", None)),
			_tag("поверх", getattr(self, "floor", None)),
			_tag("каб.", getattr(self, "room", None)),
		]

		# Прибираємо порожні значення і склеюємо комами
		full = ", ".join([p for p in addr_parts if p])

		self.full_address = full or None
		if getattr(self, "city", None):
			self.city = _title_ua(self.city)


def _title_ua(s: str) -> str:
	# М'яка нормалізація: «запоріжжя» → «Запоріжжя», «київ-святошинський» → «Київ-Святошинський»
	parts = []
	for token in (s or "").strip().split():
		sub = [p.capitalize() for p in token.split("-") if p]
		parts.append("-".join(sub))
	return " ".join([p for p in parts if p])


@frappe.whitelist()
def get_city_options(q: str | None = None, limit: int = 500):
	"""
	Повертає список унікальних міст з oiLocation, відфільтрований за q (якщо є).
	"""
	q = (q or "").strip()
	like = f"%{q}%" if q else "%"
	rows = frappe.db.sql(
		"""
        select distinct city
        from `taboiLocation`
        where coalesce(city,'') != '' and city like %s
        order by city
        limit %s
        """,
		(like, int(limit)),
	)
	# нормалізуємо для красивого показу
	res = []
	seen = set()
	for (city,) in rows:
		norm = _title_ua(city)
		if norm and norm.lower() not in seen:
			seen.add(norm.lower())
			res.append(norm)
	return res
