# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.data import cint, flt
from frappe.utils.nestedset import NestedSet


class oiHromadaSurvey(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bool_data: DF.Check
		id: DF.Data
		int_data: DF.Int
		is_group: DF.Check
		lft: DF.Int
		master_info: DF.Link | None
		old_parent: DF.Link | None
		only_admin: DF.Check
		parent_oihromadasurvey: DF.Link | None
		rgt: DF.Int
		score: DF.Float
		score_note: DF.SmallText | None
		score_pairs: DF.Int
		title: DF.SmallText
		type: DF.Literal["Boolean", "Integer"]
		value_display: DF.Data | None
	# end: auto-generated types

	def before_save(self):
		# 1) value_display для листів
		if cint(self.is_group):
			# для груп власного значення не показуємо
			self.value_display = ""
		else:
			if self.type == "Boolean":
				self.value_display = "Так" if cint(self.bool_data) else "Ні"
			elif self.type == "Integer":
				self.value_display = str(self.int_data or "0")
			else:
				self.value_display = ""

		# 2) НІЧОГО не рахуємо для score тут — групові бали залежать від дітей.
		#    Розрахунок робимо окремою процедурою (див. recompute_group_scores).


def _leaf_numeric_value(row: dict) -> float:
	"""Перетворюємо лист у числове значення:
	Boolean -> 0 або 100; Integer -> int_data (float)."""
	t = row.get("type")
	if t == "Boolean":
		return 100.0 if cint(row.get("bool_data")) else 0.0
	if t == "Integer":
		return flt(row.get("int_data") or 0.0)
	return 0.0


def _clamp_0_100(x: float) -> float:
	return max(0.0, min(100.0, flt(x)))


def _compute_group_score_from_direct_leaves(group_name: str) -> tuple[float, int, str]:
	"""Рахує бали для ГРУПИ за її ПРЯМИМИ листовими дітьми:
	- Якщо 2 листи: score = clamp(100 * v1 / v2). Якщо v2==0 → 100 якщо v1>0, інакше 0.
	- Якщо >2: пари (1/2, 3/4, ...), 100*(odd/even); пари з den==0 намагаємось врятувати:
	  * якщо den boolean False -> беремо 1;
	  * якщо den numeric 0 -> пара дає 100 якщо num>0 інакше 0.
	- Якщо після всього пар немає:
	  * якщо 1 лист -> score = leaf_value (clamp 0..100);
	  * інакше -> score = середнє по leaf_value (clamp 0..100).
	Повертає (score, used_pairs, note)."""

	children = frappe.get_all(
		"oiHromadaSurvey",
		filters={"parent_oihromadasurvey": group_name, "is_group": 0},
		fields=["name", "lft", "type", "bool_data", "int_data"],
	)
	if not children:
		return (0.0, 0, "No leaf children")

	children.sort(key=lambda r: r.get("lft") or 0)
	# Базові числові значення: Boolean -> 0/100; Integer -> int_data

	def leaf_val(r):
		t = r.get("type")
		if t == "Boolean":
			return 100.0 if cint(r.get("bool_data")) else 0.0
		if t == "Integer":
			return flt(r.get("int_data") or 0.0)
		return 0.0

	values = [leaf_val(r) for r in children]
	n = len(values)

	# Випадок 1: рівно один лист
	if n == 1:
		v = _clamp_0_100(values[0])
		return (v, 0, "Fallback: single child -> direct value")

	pairs_scores = []
	skipped = 0
	i = 0
	while i + 1 < n:
		num = flt(values[i])
		den = flt(values[i + 1])

		if den != 0.0:
			pairs_scores.append(100.0 * (num / den))
		else:
			# Спробуємо «врятувати» пару.
			# Визначимо тип листа-деномінатора (по оригінальному rows):
			den_row = children[i + 1]
			if den_row.get("type") == "Boolean":
				# False у знаменнику -> вважаємо 1 (щоб не ламати ділення)
				pairs_scores.append(100.0 * (num / 1.0))
			else:
				# Числовий 0 у знаменнику: fallback до бінарного результату
				pairs_scores.append(100.0 if num > 0 else 0.0)
				skipped += 1  # позначимо, що була «аномальна» пара
		i += 2

	# Якщо пар немає зовсім (n==0 або мала кількість листів)
	if not pairs_scores:
		# Випадок 2: рівно 2 листи з den==0 та num==0 (дали 0/0) — зведеться сюди
		if n == 2:
			# обидва нулі -> 0
			return (0.0, 0, "Fallback: 2 children but 0/0 -> score=0")
		# Випадок 3: >2 листів, але жодної валідної пари -> середнє по листах
		avg_leaves = sum(values) / n
		return (_clamp_0_100(avg_leaves), 0, "Fallback: avg of leaf values (no valid pairs)")

	avg_pct = sum(pairs_scores) / len(pairs_scores)
	score = _clamp_0_100(avg_pct)
	note = f"Pairs used: {len(pairs_scores)}; adjusted: {skipped}; raw avg: {avg_pct:.2f}"
	return (score, len(pairs_scores), note)


@frappe.whitelist()
def recompute_group_scores(root: str | None = None):
	"""Перерахувати бали для ВСІХ груп (або піддерева root).
	Рахуємо лише для документів is_group=1 за їх ПРЯМИМИ листовими дітьми."""
	# Вибірка груп
	base_filters = {"is_group": 1}
	if root:
		# обмежуємо піддеревом
		node = frappe.get_value("oiHromadaSurvey", root, ["lft", "rgt"], as_dict=True)
		if not node:
			return {"status": "error", "msg": f"Root '{root}' not found"}
		groups = frappe.get_all(
			"oiHromadaSurvey",
			filters={"is_group": 1, "lft": [">=", node.lft], "rgt": ["<=", node.rgt]},
			fields=["name", "lft", "rgt"],
			order_by="lft asc",
		)
	else:
		groups = frappe.get_all(
			"oiHromadaSurvey", filters=base_filters, fields=["name", "lft", "rgt"], order_by="lft asc"
		)

	updated = 0
	for g in groups:
		score, used_pairs, note = _compute_group_score_from_direct_leaves(g["name"])
		frappe.db.set_value(
			"oiHromadaSurvey",
			g["name"],
			{"score": flt(score, 2), "score_pairs": used_pairs, "score_note": note},
		)
		updated += 1

	frappe.db.commit()
	return {"status": "ok", "groups_updated": updated}


def _recompute_all_groups_job(root: str | None = None):
	"""Виконує фактичний перерахунок балів для всіх груп (або піддерева root)."""
	if root:
		node = frappe.get_value("oiHromadaSurvey", root, ["lft", "rgt"], as_dict=True)
		if not node:
			return {"status": "error", "msg": f"Root '{root}' not found"}
		groups = frappe.get_all(
			"oiHromadaSurvey",
			filters={"is_group": 1, "lft": [">=", node.lft], "rgt": ["<=", node.rgt]},
			fields=["name"],
			order_by="lft asc",
		)
	else:
		groups = frappe.get_all(
			"oiHromadaSurvey", filters={"is_group": 1}, fields=["name"], order_by="lft asc"
		)

	updated = 0
	for g in groups:
		score, used_pairs, note = _compute_group_score_from_direct_leaves(g["name"])
		frappe.db.set_value(
			"oiHromadaSurvey",
			g["name"],
			{"score": flt(score, 2), "score_pairs": used_pairs, "score_note": note},
		)
		updated += 1

	frappe.db.commit()
	return {"status": "ok", "groups_updated": updated}


@frappe.whitelist()
def recompute_all_groups(root: str | None = None, background: int = 1):
	"""Публічний ендпоінт: перерахунок одразу для всіх груп.
	background=1 -> запускає у фоні через чергу."""
	if int(background or 0):
		frappe.enqueue(
			"orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey._recompute_all_groups_job",
			queue="long",
			job_name="HromadaSurvey: recompute ALL groups",
			root=root,
		)
		return {"status": "queued"}
	else:
		return _recompute_all_groups_job(root=root)
