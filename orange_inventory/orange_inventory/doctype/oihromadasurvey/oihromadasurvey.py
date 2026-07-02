# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import io
import os
import tempfile
import zipfile

import frappe
from frappe.utils import nowdate
from frappe.utils.data import cint, flt
from frappe.utils.nestedset import NestedSet
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation


class oiHromadaSurvey(NestedSet):
	def validate(self):
		"""Валідація перед збереженням."""
		self._validate_no_circular_reference()
		self._validate_data_values()
		self._validate_group_has_no_data()

	def _validate_data_values(self):
		"""Перевіряє що числові дані не від'ємні."""
		if self.type == "Кількісні дані" and self.int_data is not None:
			if cint(self.int_data) < 0:
				frappe.throw(
					"Значення кількісних даних не може бути від'ємним",
					frappe.ValidationError,
				)

	def _validate_group_has_no_data(self):
		"""Перевіряє що групи не мають значень int_data/bool_data."""
		if self.type == "Група":
			if self.int_data and cint(self.int_data) != 0:
				frappe.throw(
					"Група не може мати числове значення (int_data)",
					frappe.ValidationError,
				)
			if self.bool_data and cint(self.bool_data) != 0:
				frappe.throw(
					"Група не може мати якісне значення (bool_data)",
					frappe.ValidationError,
				)

	def _validate_no_circular_reference(self):
		"""Перевіряє що документ не посилається сам на себе як на батька."""
		if self.parent_oihromadasurvey and self.parent_oihromadasurvey == self.name:
			frappe.throw(
				"Документ не може посилатися сам на себе як на батьківський елемент",
				frappe.ValidationError,
			)

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oihromadasurveyhistory.oihromadasurveyhistory import (
			oiHromadaSurveyHistory,
		)

		bool_data: DF.Check
		description: DF.SmallText | None
		enabled: DF.Check
		frequency: DF.Literal[
			"\u0420\u0430\u0437 \u043d\u0430 \u0440\u0456\u043a",
			"\u0420\u0430\u0437 \u043d\u0430 \u043a\u0432\u0430\u0440\u0442\u0430\u043b",
		]
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
		type: DF.Literal[
			"\u041a\u0456\u043b\u044c\u043a\u0456\u0441\u043d\u0456 \u0434\u0430\u043d\u0456",
			"\u042f\u043a\u0456\u0441\u043d\u0456 \u0434\u0430\u043d\u0456",
			"\u0413\u0440\u0443\u043f\u0430",
		]
		value_display: DF.Data | None
		value_history: DF.Table[oiHromadaSurveyHistory]
	# end: auto-generated types

	def before_save(self):
		# 1) value_display для листів
		if self.type == "Група":
			# для груп власного значення не показуємо
			self.value_display = ""
		else:
			if self.type == "Якісні дані":
				self.value_display = "Так" if cint(self.bool_data) else "Ні"
			elif self.type == "Кількісні дані":
				self.value_display = str(self.int_data or "0")
			else:
				self.value_display = ""

		# 2) НІЧОГО не рахуємо для score тут — групові бали залежать від дітей.
		#    Розрахунок робимо окремою процедурою (див. recompute_group_scores).

		# 3) Автоматичне збереження історії при зміні значень
		self._track_value_changes()

	def _track_value_changes(self):
		"""
		Відстежує зміни в int_data та bool_data і автоматично додає запис в історію.
		"""
		# Пропускаємо для груп
		if self.type == "Група":
			return

		# Пропускаємо для нових документів
		if self.is_new():
			return

		# Перевіряємо чи змінилися значення
		value_changed = False

		if self.type == "Кількісні дані":
			if self.has_value_changed("int_data"):
				value_changed = True
				new_value = self.int_data
				display = str(new_value or "0")
		elif self.type == "Якісні дані":
			if self.has_value_changed("bool_data"):
				value_changed = True
				new_value = cint(self.bool_data)
				display = "Так" if new_value else "Ні"
		else:
			return

		# Якщо значення змінилося, додаємо запис в історію
		if value_changed:
			self.append(
				"value_history",
				{
					"recorded_date": frappe.utils.now(),
					"period": self._get_current_period(),
					"int_value": self.int_data if self.type == "Кількісні дані" else None,
					"bool_value": cint(self.bool_data) if self.type == "Якісні дані" else 0,
					"value_display": display,
					"changed_by": frappe.session.user,
					"notes": "Автоматичний запис при зміні значення",
				},
			)

	def after_save(self):
		"""Виконується після збереження документа."""
		# Автоматичний перерахунок score батьківських груп при зміні значень
		if self.type != "Група":
			self._update_parent_scores()

	def _update_parent_scores(self):
		"""
		Оновлює score всіх батьківських груп при зміні значення показника.
		Працює від безпосереднього батька до кореня.
		"""
		if not self.parent_oihromadasurvey:
			return

		from frappe.query_builder import DocType

		Survey = DocType("oiHromadaSurvey")

		# Отримуємо всіх предків-груп використовуючи QueryBuilder
		parent_groups = (
			frappe.qb.from_(Survey)
			.select(Survey.name)
			.where(Survey.lft < self.lft)
			.where(Survey.rgt > self.rgt)
			.where(Survey.type == "Група")
			.orderby(Survey.lft, order=frappe.qb.desc)
		).run(as_dict=True)

		# Перераховуємо score для кожної групи (від найближчого батька до кореня)
		for group in parent_groups:
			score, used_pairs, note = _compute_group_score_from_direct_leaves(group["name"])
			frappe.db.set_value(
				"oiHromadaSurvey",
				group["name"],
				{"score": flt(score, 2), "score_pairs": used_pairs, "score_note": note},
				update_modified=False,
			)

	def _get_current_period(self):
		"""
		Визначає поточний період на основі frequency.
		Повертає рядок типу "2025-Q1" або "2025-01" або "2025"
		"""
		from frappe.utils import now_datetime

		current = now_datetime()
		year = current.year

		if self.frequency == "Раз на квартал":
			quarter = (current.month - 1) // 3 + 1
			return f"{year}-Q{quarter}"
		elif self.frequency == "Раз на рік":
			return str(year)
		else:
			# За замовчуванням - місяць
			return f"{year}-{current.month:02d}"


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
		filters={"parent_oihromadasurvey": group_name, "type": "Група"},
		fields=["name", "lft", "type", "bool_data", "int_data"],
	)
	if not children:
		return (0.0, 0, "No leaf children")

	children.sort(key=lambda r: r.get("lft") or 0)
	# Базові числові значення: Boolean -> 0/100; Integer -> int_data

	def leaf_val(r):
		t = r.get("type")
		if t == "Якісні дані":
			return 100.0 if cint(r.get("bool_data")) else 0.0
		if t == "Кількісні дані":
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
			if den_row.get("type") == "Якісні дані":
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
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "write"):
		frappe.throw("Недостатньо прав для перерахунку балів", frappe.PermissionError)

	# Вибірка груп
	base_filters = {"type": "Група"}
	if root:
		# обмежуємо піддеревом
		node = frappe.get_value("oiHromadaSurvey", root, ["lft", "rgt"], as_dict=True)
		if not node:
			return {"status": "error", "msg": f"Root '{root}' not found"}
		groups = frappe.get_all(
			"oiHromadaSurvey",
			filters={"type": "Група", "lft": [">=", node.lft], "rgt": ["<=", node.rgt]},
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
			filters={"type": "Група", "lft": [">=", node.lft], "rgt": ["<=", node.rgt]},
			fields=["name"],
			order_by="lft asc",
		)
	else:
		groups = frappe.get_all(
			"oiHromadaSurvey", filters={"type": "Група"}, fields=["name"], order_by="lft asc"
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
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "write"):
		frappe.throw("Недостатньо прав для перерахунку балів", frappe.PermissionError)

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


# Глобальний кеш для шляхів груп (очищається при кожному експорті)
_group_paths_cache: dict[str, str] = {}


def _build_group_paths_cache():
	"""
	Будує кеш шляхів для всіх вузлів одним запитом.
	Значно швидше ніж робити окремий запит для кожного вузла.
	"""
	global _group_paths_cache
	_group_paths_cache.clear()

	from frappe.query_builder import DocType

	Survey = DocType("oiHromadaSurvey")

	# Отримуємо всі групи з їх lft/rgt
	groups = (
		frappe.qb.from_(Survey)
		.select(Survey.name, Survey.title, Survey.lft, Survey.rgt)
		.where(Survey.type == "Група")
		.orderby(Survey.lft)
	).run(as_dict=True)

	# Будуємо шляхи для кожної групи
	for group in groups:
		ancestors = [g["title"] for g in groups if g["lft"] <= group["lft"] and g["rgt"] >= group["rgt"]]
		_group_paths_cache[group["name"]] = " / ".join(ancestors)

	# Отримуємо всі листові вузли (не групи) з їх lft/rgt
	leaves = (
		frappe.qb.from_(Survey).select(Survey.name, Survey.lft, Survey.rgt).where(Survey.type != "Група")
	).run(as_dict=True)

	# Будуємо шляхи для листових вузлів
	for leaf in leaves:
		ancestors = [g["title"] for g in groups if g["lft"] <= leaf["lft"] and g["rgt"] >= leaf["rgt"]]
		_group_paths_cache[leaf["name"]] = " / ".join(ancestors)


def _get_group_path(docname: str) -> str:
	"""Повертає шлях груп для вузла: 'Група / Підгрупа / ...'."""
	global _group_paths_cache

	# Якщо кеш є, використовуємо його
	if docname in _group_paths_cache:
		return _group_paths_cache[docname]

	# Fallback: якщо немає в кеші, робимо запит (для поодиноких викликів)
	from frappe.query_builder import DocType

	Survey = DocType("oiHromadaSurvey")

	node = frappe.db.get_value("oiHromadaSurvey", docname, ["lft", "rgt"], as_dict=True)
	if not node:
		return ""

	rows = (
		frappe.qb.from_(Survey)
		.select(Survey.name, Survey.title)
		.where(Survey.lft <= node.lft)
		.where(Survey.rgt >= node.rgt)
		.where(Survey.type == "Група")
		.orderby(Survey.lft)
	).run(as_dict=True)

	path = " / ".join([r.title for r in rows])
	_group_paths_cache[docname] = path
	return path


def _fetch_leaf_rows_for_org(org: str):
	"""Повертає листові показники для розпорядника org (включно з only_admin)."""
	return frappe.get_all(
		"oiHromadaSurvey",
		filters={
			"enabled": 1,
			"type": ["!=", "Група"],
			"master_info": org,
		},
		fields=[
			"name",
			"id",
			"title",
			"type",
			"frequency",
			"value_display",
			"int_data",
			"bool_data",
			"description",
			"only_admin",
			"parent_oihromadasurvey",
			"lft",
			"rgt",
			"modified",
			"modified_by",
		],
		order_by="lft asc",
	)


def _excel_styles():
	head_fill = PatternFill("solid", fgColor="E8EEF7")
	bold = Font(bold=True)
	center = Alignment(horizontal="center", vertical="center", wrap_text=True)
	wrap = Alignment(wrap_text=True)
	thin = Side(style="thin", color="D0D7E5")
	border = Border(left=thin, right=thin, top=thin, bottom=thin)
	return head_fill, bold, center, wrap, border


def _autowidth(ws, extra=2):
	widths = {}
	for row in ws.iter_rows(values_only=True):
		for idx, val in enumerate(row, start=1):
			l = len(str(val)) if val is not None else 0
			widths[idx] = max(widths.get(idx, 0), l)
	for col, width in widths.items():
		ws.column_dimensions[chr(64 + col)].width = min(max(width + extra, 10), 60)


def _make_data_sheet(wb: Workbook, org_meta: dict, period: str, rows: list[dict]):
	ws = wb.active
	ws.title = "Показники"
	head_fill, bold, center, wrap, border = _excel_styles()

	# Шапка
	ws.merge_cells("A1:I1")
	ws["A1"] = f"Організація: {org_meta['title']}"
	ws["A1"].font = Font(bold=True, size=13)
	ws["A1"].alignment = center

	ws.merge_cells("A2:I2")
	extra = f" | ЄДРПОУ: {org_meta['tax_code']}" if org_meta.get("tax_code") else ""
	ws["A2"] = f"Період: {period}{extra}"
	ws["A2"].alignment = center

	ws.append([""] * 9)  # рядок 3 — порожній

	# Заголовки (рядок 4)
	headers = [
		"Шлях групи",
		"ID",
		"Назва показника",
		"Тип",
		"Періодичність",
		"Поточне значення",
		"Значення для заповнення",
		"Остання зміна",
		"Примітка",
	]
	ws.append(headers)
	for cell in ws[4]:
		cell.fill = head_fill
		cell.font = bold
		cell.alignment = center
		cell.border = border

		# --- СЛУЖБОВИЙ ЛИСТ ДЛЯ ВАЛІДАЦІЇ “Так/Ні” ---
		# Валідації
		# Жорстка «Так/Ні» (errorStyle=stop, allow_blank=False)
		dv_bool = DataValidation(
			type="list",
			formula1='="Так,Ні"',  # або =DV!$A$1:$A$2, якщо лишаєш прихований аркуш
			allow_blank=False,
		)
		dv_bool.errorStyle = "stop"
		dv_bool.showErrorMessage = True
		dv_bool.errorTitle = "Некоректне значення"
		dv_bool.error = "Оберіть «Так» або «Ні» зі списку."
		dv_bool.showInputMessage = True
		dv_bool.promptTitle = "Оберіть зі списку"
		dv_bool.prompt = "Доступні значення: Так або Ні."
		ws.add_data_validation(dv_bool)

		# Для числових — тільки цілі >= 0, теж жорстко
		dv_int = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=False)
		dv_int.errorStyle = "stop"
		dv_int.showErrorMessage = True
		dv_int.errorTitle = "Некоректне число"
		dv_int.error = "Введіть ціле число 0 або більше."
		ws.add_data_validation(dv_int)

	# Глобальний "блокувальник" для не-редагованих колонок (і клітинок only_admin)
	dv_block = DataValidation(
		type="custom",
		formula1="FALSE",
		allow_blank=True,
		showErrorMessage=True,
		errorTitle="Заборонено",
		error="Редагуйте лише дозволені клітинки.",
	)
	ws.add_data_validation(dv_block)

	# Палітри підсвітки
	editable_fill = PatternFill("solid", fgColor="FFFCE0")  # жовтий для редаговних
	# сірий для заборонених
	locked_fill = PatternFill("solid", fgColor="F2F2F2")

	# Рядки даних (з 5-го)
	for r in rows:
		path = _get_group_path(r["name"])

		# F: Поточне значення — число для кількісних, "Так/Ні" для якісних
		if r.get("type") == "Кількісні дані":
			f_value = flt(r.get("int_data") if r.get("int_data") is not None else r.get("value_display") or 0)
		else:
			f_value = r.get("value_display") or ""

		# G: Значення для заповнення — якщо only_admin, ставимо таке саме і "блокуємо"
		is_admin = cint(r.get("only_admin"))
		g_value = f_value if is_admin else ""

		# H: Остання зміна
		modified_date = r.get("modified")
		if modified_date:
			from frappe.utils import get_datetime

			h_value = get_datetime(modified_date).strftime("%d.%m.%Y %H:%M")
		else:
			h_value = "-"

		ws.append(
			[
				path,  # A
				r.get("id") or "",  # B
				r.get("title") or "",  # C
				r.get("type") or "",  # D
				r.get("frequency") or "",  # E
				f_value,  # F (Поточне значення)
				g_value,  # G (Значення для заповнення)
				h_value,  # H (Остання зміна)
				r.get("description") or "",  # I (Примітка)
			]
		)

		row_idx = ws.max_row

		# Формати чисел
		if r.get("type") == "Кількісні дані":
			ws[f"F{row_idx}"].number_format = "#,##0"
			ws[f"G{row_idx}"].number_format = "#,##0"

		# ВАЛІДАЦІЇ ДЛЯ G:
		if is_admin:
			# для only_admin клітинка заблокована нашим dv_block (FALSE) як і раніше
			dv_block.add(f"G{row_idx}")
			ws[f"G{row_idx}"].fill = locked_fill
		else:
			ws[f"G{row_idx}"].fill = editable_fill
			if r.get("type") == "Якісні дані":
				# тепер з errorStyle=stop і allow_blank=False
				dv_bool.add(f"G{row_idx}")
			else:
				dv_int.add(f"G{row_idx}")
				ws[f"G{row_idx}"].number_format = "#,##0"

	# Заблокувати редагування ВСІХ колонок, крім G (ввод), через DV FALSE
	if ws.max_row >= 5:
		dv_block.add(f"A5:F{ws.max_row}")
		dv_block.add(f"H5:I{ws.max_row}")

	# Стилі для тіла таблиці
	for row in ws.iter_rows(min_row=5, max_row=ws.max_row, min_col=1, max_col=9):
		for cell in row:
			cell.alignment = wrap
			cell.border = border

	# Freeze + фільтри
	ws.freeze_panes = "A5"
	ws.auto_filter.ref = f"A4:I{ws.max_row}"

	_autowidth(ws)


def _save_bytes_as_private_file(
	filename: str,
	content: bytes,
	attached_to_doctype: str | None = None,
	attached_to_name: str | int | None = None,
	attached_to_field: str | None = None,
):
	"""Зберегти файл. Якщо вказана прив’язка — прив’язуємо, інакше створюємо просто приватний File."""
	file_args = {
		"doctype": "File",
		"file_name": filename,
		"content": content,
		"is_private": 1,
	}
	if attached_to_doctype and attached_to_name:
		file_args.update(
			{
				"attached_to_doctype": attached_to_doctype,
				"attached_to_name": attached_to_name,
			}
		)
		if attached_to_field:
			file_args["attached_to_field"] = attached_to_field
	# ВАЖЛИВО: не задаємо attached_to_* якщо name відсутній — інакше отримаємо ValidationError
	file_doc = frappe.get_doc(file_args)
	file_doc.insert(ignore_permissions=True)
	return file_doc.file_url


def _get_org_meta(org: str) -> dict:
	"""Повертає читабельну назву та метадані організації."""
	if not org:
		return {"title": "", "abbreviation": "", "tax_code": "", "name": ""}
	row = frappe.db.get_value(
		"hromsOrgStructure",
		org,
		["department_name", "tax_code", "name"],
		as_dict=True,
	)
	if not row:
		return {"title": str(org), "abbreviation": "", "tax_code": "", "name": str(org)}
	title = row.department_name or row.name
	return {
		"title": title,
		"abbreviation": "",
		"tax_code": row.tax_code or "",
		"name": row.name or org,
	}


@frappe.whitelist()
def export_org_template(org: str, period: str | None = None):
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "read"):
		frappe.throw("Недостатньо прав для експорту шаблону", frappe.PermissionError)

	if not org:
		frappe.throw("Не вказано розпорядника (org).")
	rows = _fetch_leaf_rows_for_org(org)
	if not rows:
		frappe.throw(f"Для розпорядника '{org}' не знайдено показників.")

	# Будуємо кеш шляхів груп для оптимізації
	_build_group_paths_cache()

	org_meta = _get_org_meta(org)
	the_period = period or nowdate()

	wb = Workbook()
	_make_data_sheet(wb, org_meta, the_period, rows)

	bio = io.BytesIO()
	wb.save(bio)
	# Обмежуємо довжину назви для уникнення помилки "File name too long"
	safe_title = org_meta["title"].replace("/", "-").replace("\\", "-").replace(" ", "_")
	if len(safe_title) > 80:
		safe_title = safe_title[:77] + "..."
	filename = f"{safe_title}_{the_period}.xlsx"

	url = _save_bytes_as_private_file(
		filename,
		bio.getvalue(),
		attached_to_doctype="hromsOrgStructure",
		attached_to_name=org,  # системне name (org-xxxxx)
	)
	return {"file_url": url}


@frappe.whitelist()
def get_value_trend_data(survey_id: str, limit: int = 50):
	"""
	Отримує дані для побудови графіка тенденцій для конкретного показника.

	Args:
	        survey_id: ID показника oiHromadaSurvey
	        limit: Кількість останніх записів (за замовчуванням 50)

	Returns:
	        dict: {
	                "labels": ["2025-Q1", "2025-Q2", ...],
	                "values": [10, 15, 12, ...],
	                "type": "Кількісні дані" | "Якісні дані",
	                "title": "Назва показника"
	        }
	"""
	survey = frappe.get_doc("oiHromadaSurvey", survey_id)

	if survey.type == "Група":
		frappe.throw("Для груп історія значень не відстежується")

	# Отримуємо історію з child table
	history = frappe.get_all(
		"oiHromadaSurveyHistory",
		filters={"parent": survey_id},
		fields=["recorded_date", "period", "int_value", "bool_value", "value_display"],
		order_by="recorded_date asc",
		limit=limit,
	)

	labels = []
	values = []

	for entry in history:
		# Використовуємо period якщо є, інакше дату
		label = entry.period or entry.recorded_date.split(" ")[0]
		labels.append(label)

		if survey.type == "Кількісні дані":
			values.append(flt(entry.int_value or 0))
		elif survey.type == "Якісні дані":
			# Конвертуємо булеве значення в 0/100 для графіка
			values.append(100 if cint(entry.bool_value) else 0)

	return {
		"labels": labels,
		"values": values,
		"type": survey.type,
		"title": survey.title,
		"frequency": survey.frequency,
	}


@frappe.whitelist()
def export_all_org_templates(period: str | None = None):
	"""Згенерувати ZIP з шаблонами для всіх активних розпорядників + Summary.xlsx.
	Summary містить: Організація, Всього пунктів, К-ть only_admin, К-ть пунктів для заповнення.
	period (напр. '2025-Q4') можна передати з діалогу; якщо не вказано — nowdate()."""
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "read"):
		frappe.throw("Недостатньо прав для експорту шаблонів", frappe.PermissionError)

	orgs = frappe.get_all(
		"hromsOrgStructure",
		filters={"status": "Активний"},
		pluck="name",
	)
	if not orgs:
		frappe.throw("Немає активних організацій для експорту.")

	# Будуємо кеш шляхів груп для оптимізації (один раз для всіх організацій)
	_build_group_paths_cache()

	the_period = period or nowdate()
	safe_period = str(the_period).replace("/", "-").replace("\\", "-").replace(" ", "_")

	tmpdir = tempfile.mkdtemp()
	paths: list[tuple[str, str]] = []  # [(файл_шляг, org_name)]
	# [(org_title, total, admin, fillable)]
	summary_rows: list[tuple[str, int, int, int]] = []

	for org in orgs:
		rows = _fetch_leaf_rows_for_org(org)  # включає only_admin
		total_count = len(rows)

		# Пропускаємо організації без показників
		if total_count == 0:
			continue

		admin_count = sum(1 for r in rows if cint(r.get("only_admin")))
		fillable_count = total_count - admin_count

		org_meta = _get_org_meta(org)

		# Згенеруємо XLSX для організації
		wb = Workbook()
		_make_data_sheet(wb, org_meta, the_period, rows)
		# Обмежуємо довжину назви для уникнення помилки "File name too long"
		safe_title = org_meta["title"].replace("/", "-").replace("\\", "-").replace(" ", "_")
		# Максимум 80 символів для назви (+ Template_ + period + .xlsx ≈ 100 символів)
		if len(safe_title) > 80:
			safe_title = safe_title[:77] + "..."
		fname = f"Template_{safe_title}_{safe_period}.xlsx"
		fpath = os.path.join(tmpdir, fname)
		wb.save(fpath)

		paths.append((fpath, org))
		summary_rows.append((org_meta["title"], total_count, admin_count, fillable_count))

	if not paths:
		frappe.throw("Жоден шаблон не був згенерований (немає показників).")

	# --- Зведена таблиця (Summary) ---
	sum_wb = Workbook()
	sum_ws = sum_wb.active
	sum_ws.title = "Розпорядники"
	head_fill, bold, center, wrap, border = _excel_styles()

	# Заголовки
	sum_ws.append(["Організація", "Всього пунктів", "К-ть only_admin", "К-ть пунктів для заповнення"])
	for cell in sum_ws[1]:
		cell.fill = head_fill
		cell.font = bold
		cell.alignment = center
		cell.border = border

	# Рядки (відсортовано за назвою)
	for org_title, total, admin, fillable in sorted(summary_rows, key=lambda x: x[0].lower()):
		sum_ws.append([org_title, total, admin, fillable])

	# Стилі тіла
	for row in sum_ws.iter_rows(min_row=2, max_row=sum_ws.max_row, min_col=1, max_col=4):
		for cell in row:
			cell.alignment = wrap
			cell.border = border

	# Рядок підсумків
	last_data_row = sum_ws.max_row
	total_row = last_data_row + 1
	sum_ws.append(
		[
			"Разом",
			f"=SUM(B2:B{last_data_row})",
			f"=SUM(C2:C{last_data_row})",
			f"=SUM(D2:D{last_data_row})",
		]
	)
	for cell in sum_ws[total_row]:
		cell.font = bold
		cell.border = border
	sum_ws[f"A{total_row}"].alignment = center

	# Тюнінг
	sum_ws.freeze_panes = "A2"
	sum_ws.auto_filter.ref = f"A1:D{total_row}"
	_autowidth(sum_ws)

	# Зберегти summary-файл і додати до ZIP
	sum_fname = f"Templates_Summary_{safe_period}.xlsx"
	sum_fpath = os.path.join(tmpdir, sum_fname)
	sum_wb.save(sum_fpath)

	# --- ZIP ---
	zip_bytes = io.BytesIO()
	with zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED) as zf:
		# шаблони
		for fpath, _ in paths:
			zf.write(fpath, os.path.basename(fpath))
		# зведена таблиця
		zf.write(sum_fpath, os.path.basename(sum_fpath))

	zip_url = _save_bytes_as_private_file(
		f"oiHromadaSurvey_Templates_{safe_period}.zip", zip_bytes.getvalue()
	)
	return {"file_url": zip_url, "count": len(paths), "summary_rows": len(summary_rows)}


def _parse_excel_header(ws) -> dict:
	"""
	Парсить заголовок Excel файлу для отримання організації та періоду.

	Формат:
	- Рядок 1: "Організація: Назва організації"
	- Рядок 2: "Період: 2025-Q4 | ЄДРПОУ: 01993011"

	Returns:
	        dict: {"organization_name": str, "tax_code": str, "year": int, "quarter": str}
	"""
	import re

	result = {
		"organization_name": None,
		"tax_code": None,
		"year": None,
		"quarter": None,
	}

	# Рядок 1: Організація
	row1 = ws["A1"].value or ""
	if "Організація:" in row1:
		result["organization_name"] = row1.replace("Організація:", "").strip()

	# Рядок 2: Період та ЄДРПОУ
	row2 = ws["A2"].value or ""

	# Парсимо ЄДРПОУ
	edrpou_match = re.search(r"ЄДРПОУ:\s*(\d+)", row2)
	if edrpou_match:
		result["tax_code"] = edrpou_match.group(1)

	# Парсимо період (формат: 2025-Q4 або 2025-Q1)
	period_match = re.search(r"Період:\s*(\d{4})-?(Q\d)", row2)
	if period_match:
		result["year"] = int(period_match.group(1))
		result["quarter"] = period_match.group(2)

	return result


def _find_organization_by_tax_code(tax_code: str) -> str | None:
	"""Знаходить організацію по ЄДРПОУ."""
	if not tax_code:
		return None
	return frappe.db.get_value("hromsOrgStructure", {"tax_code": tax_code}, "name")


def _create_import_log(
	organization: str | None,
	year: int | None,
	quarter: str | None,
	file_url: str,
	total_parameters: int,
	details: list,
) -> str | None:
	"""
	Створює запис в журналі імпорту.

	Returns:
	        str: ID створеного документа або None при помилці
	"""
	if not organization or not year or not quarter:
		return None

	try:
		import_log = frappe.new_doc("oiHromadaImportLog")
		import_log.organization = organization
		import_log.year = year
		import_log.quarter = quarter
		import_log.file = file_url
		import_log.total_parameters = total_parameters
		import_log.status = "Імпортовано"

		# Додаємо деталі змін
		for change in details:
			import_log.append(
				"changes",
				{
					"survey": change.get("id"),
					"parameter_code": change.get("id"),
					"old_value": str(change.get("old_value", "")),
					"new_value": str(change.get("new_value", "")),
				},
			)

		import_log.insert(ignore_permissions=True)
		return import_log.name
	except Exception as e:
		frappe.log_error(f"Помилка створення журналу імпорту: {e}", "Import Log Error")
		return None


@frappe.whitelist()
def import_from_excel(file_url: str, org: str | None = None):
	"""
	Імпорт даних з Excel файлу, згенерованого через export_org_template.

	Args:
	        file_url: URL завантаженого файлу (з Frappe File)
	        org: ID організації (опціонально, для валідації)

	Returns:
	        dict: {
	                "status": "success" | "error",
	                "updated": int,  # кількість оновлених записів
	                "skipped": int,  # кількість пропущених
	                "errors": list,  # список помилок
	                "details": list,  # детальна інформація про зміни
	                "import_log": str | None  # ID запису журналу імпорту
	        }
	"""
	from openpyxl import load_workbook

	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "write"):
		frappe.throw("Недостатньо прав для імпорту даних", frappe.PermissionError)

	# Отримати файл з системи
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	file_path = file_doc.get_full_path()

	if not os.path.exists(file_path):
		frappe.throw(f"Файл не знайдено: {file_path}")

	try:
		wb = load_workbook(file_path, data_only=True)
		ws = wb["Показники"]
	except Exception as e:
		frappe.throw(f"Помилка читання файлу Excel: {str(e)}")

	# Парсимо заголовок для отримання організації та періоду
	header_info = _parse_excel_header(ws)
	detected_org = _find_organization_by_tax_code(header_info.get("tax_code"))

	# Якщо org не передано, використовуємо виявлену організацію
	if not org and detected_org:
		org = detected_org

	updated = 0
	skipped = 0
	errors = []
	details = []
	critical_error = None
	total_rows = 0

	try:
		# Починаємо з 5-го рядка (перші 4 - шапка)
		for row_idx, row in enumerate(ws.iter_rows(min_row=5, values_only=True), start=5):
			total_rows += 1
			if not row or len(row) < 7:
				continue

			# Розпакування колонок (використовуємо тільки потрібні)
			survey_id = row[1]  # B: ID
			new_value = row[6]  # G: Значення для заповнення

			# Пропускаємо порожні рядки
			if not survey_id or not new_value:
				skipped += 1
				continue

			try:
				# Отримуємо документ
				if not frappe.db.exists("oiHromadaSurvey", survey_id):
					errors.append(f"Рядок {row_idx}: Показник {survey_id} не знайдено")
					skipped += 1
					continue

				survey = frappe.get_doc("oiHromadaSurvey", survey_id)

				# Валідація організації (якщо передано)
				if org and survey.master_info != org:
					errors.append(f"Рядок {row_idx}: Показник {survey_id} не належить організації {org}")
					skipped += 1
					continue

				# Пропускаємо only_admin записи
				if cint(survey.only_admin):
					skipped += 1
					continue

				# Перевіряємо тип і оновлюємо значення
				value_changed = False

				if survey.type == "Кількісні дані":
					# Конвертуємо в ціле число
					try:
						new_int_value = int(float(new_value)) if new_value else 0
					except (ValueError, TypeError):
						errors.append(f"Рядок {row_idx}: Некоректне числове значення '{new_value}'")
						skipped += 1
						continue

					if survey.int_data != new_int_value:
						old_val = survey.int_data
						survey.int_data = new_int_value
						value_changed = True
						details.append(
							{
								"id": survey_id,
								"title": survey.title,
								"type": survey.type,
								"old_value": old_val,
								"new_value": new_int_value,
							}
						)

				elif survey.type == "Якісні дані":
					# Конвертуємо "Так"/"Ні" в bool
					new_bool_str = str(new_value).strip()
					if new_bool_str == "Так":
						new_bool_value = 1
					elif new_bool_str == "Ні":
						new_bool_value = 0
					else:
						errors.append(
							f"Рядок {row_idx}: Некоректне якісне значення '{new_value}' (очікується 'Так' або 'Ні')"
						)
						skipped += 1
						continue

					if cint(survey.bool_data) != new_bool_value:
						old_val = "Так" if cint(survey.bool_data) else "Ні"
						survey.bool_data = new_bool_value
						value_changed = True
						details.append(
							{
								"id": survey_id,
								"title": survey.title,
								"type": survey.type,
								"old_value": old_val,
								"new_value": "Так" if new_bool_value else "Ні",
							}
						)

				# Зберігаємо тільки якщо були зміни
				if value_changed:
					survey.save()
					updated += 1
				else:
					skipped += 1

			except Exception as e:
				errors.append(f"Рядок {row_idx}: Помилка обробки - {str(e)}")
				skipped += 1
				continue

		# Commit тільки якщо немає критичних помилок
		frappe.db.commit()

	except Exception as e:
		# Rollback при критичній помилці
		frappe.db.rollback()
		critical_error = str(e)
		return {
			"status": "error",
			"message": f"Критична помилка імпорту: {critical_error}. Всі зміни скасовано.",
			"updated": 0,
			"skipped": skipped,
			"errors": errors + [f"Критична помилка: {critical_error}"],
			"details": [],
		}

	# Створюємо запис у журналі імпорту
	import_log_id = None
	if updated > 0 and detected_org:
		import_log_id = _create_import_log(
			organization=detected_org,
			year=header_info.get("year"),
			quarter=header_info.get("quarter"),
			file_url=file_url,
			total_parameters=total_rows,
			details=details,
		)

	return {
		"status": "success" if not errors or updated > 0 else "error",
		"updated": updated,
		"skipped": skipped,
		"errors": errors,
		"details": details,
		"import_log": import_log_id,
		"organization": detected_org,
		"period": f"{header_info.get('year')}-{header_info.get('quarter')}"
		if header_info.get("year")
		else None,
	}


@frappe.whitelist()
def generate_completion_report(period: str | None = None):
	"""
	Генерує звіт про заповнення показників для всіх організацій за вказаний період.

	Args:
	        period: Період для звіту (напр. '2025-Q1'). Якщо не вказано - поточна дата.

	Returns:
	        dict: {
	                "file_url": str,  # URL згенерованого Excel файлу
	                "total_orgs": int,  # Загальна кількість організацій
	                "filled_orgs": int,  # Кількість організацій що заповнили
	                "unfilled_orgs": int  # Кількість організацій що не заповнили
	        }
	"""
	# Перевірка прав доступу
	if not frappe.has_permission("oiHromadaSurvey", "read"):
		frappe.throw("Недостатньо прав для генерації звіту", frappe.PermissionError)

	the_period = period or nowdate()

	# Отримати всі активні організації
	orgs = frappe.get_all(
		"hromsOrgStructure",
		filters={"status": "Активний"},
		fields=["name", "department_name"],
		order_by="department_name",
	)

	if not orgs:
		frappe.throw("Немає активних організацій для звіту.")

	report_data = []
	filled_count = 0
	unfilled_count = 0

	for org in orgs:
		org_name = org.name
		org_title = org.department_name or org_name

		# Отримати всі показники для організації (листи, не групи)
		indicators = frappe.get_all(
			"oiHromadaSurvey",
			filters={
				"master_info": org_name,
				"is_group": 0,
				"enabled": 1,
				"only_admin": 0,  # Тільки показники для заповнення
			},
			fields=["name", "title", "type", "int_data", "bool_data", "modified", "modified_by"],
			order_by="name",
		)

		total_indicators = len(indicators)
		filled_indicators = 0
		unfilled_indicators = 0
		last_update_date = None
		last_update_by = None
		unfilled_list = []

		for ind in indicators:
			# Перевірити чи показник заповнено
			is_filled = False

			if ind.type == "Кількісні дані":
				# Вважаємо заповненим, якщо значення не None (навіть 0 - це заповнено)
				is_filled = ind.int_data is not None
			elif ind.type == "Якісні дані":
				# Для якісних даних завжди є значення (0 або 1), тому перевіряємо чи modified після базової дати
				# Альтернативно можна перевірити наявність історії
				history_count = frappe.db.count("oiHromadaSurveyHistory", filters={"parent": ind.name})
				is_filled = history_count > 0

			if is_filled:
				filled_indicators += 1
				# Оновлюємо дату останнього оновлення
				if not last_update_date or ind.modified > last_update_date:
					last_update_date = ind.modified
					last_update_by = ind.modified_by
			else:
				unfilled_indicators += 1
				unfilled_list.append(f"{ind.name}: {ind.title}")

		# Статус організації
		completion_percentage = (filled_indicators / total_indicators * 100) if total_indicators > 0 else 0

		if completion_percentage == 100:
			status = "✓ Заповнено"
			filled_count += 1
		elif completion_percentage > 0:
			status = f"⚠ Частково ({completion_percentage:.0f}%)"
			unfilled_count += 1
		else:
			status = "✗ Не заповнено"
			unfilled_count += 1

		report_data.append(
			{
				"organization": org_title,
				"status": status,
				"total": total_indicators,
				"filled": filled_indicators,
				"unfilled": unfilled_indicators,
				"completion_pct": completion_percentage,
				"last_update": last_update_date.strftime("%d.%m.%Y %H:%M") if last_update_date else "-",
				"updated_by": last_update_by or "-",
				"unfilled_items": unfilled_list,
			}
		)

	# Створити Excel звіт
	wb = Workbook()
	ws = wb.active
	ws.title = "Звіт про заповнення"

	# Стилі
	head_fill, bold, center, wrap, border = _excel_styles()

	# Шапка звіту
	ws.merge_cells("A1:H1")
	ws["A1"] = f"Звіт про заповнення показників за період: {the_period}"
	ws["A1"].font = Font(size=14, bold=True)
	ws["A1"].alignment = center

	ws.merge_cells("A2:H2")
	ws["A2"] = f"Дата формування: {nowdate()}"
	ws["A2"].alignment = center

	# Заголовки колонок
	headers = [
		"Організація",
		"Статус",
		"Всього показників",
		"Заповнено",
		"Не заповнено",
		"% виконання",
		"Остання зміна",
		"Змінив",
	]

	ws.append(headers)
	for cell in ws[4]:
		cell.fill = head_fill
		cell.font = bold
		cell.alignment = center
		cell.border = border

	# Дані
	for row_data in report_data:
		ws.append(
			[
				row_data["organization"],
				row_data["status"],
				row_data["total"],
				row_data["filled"],
				row_data["unfilled"],
				f"{row_data['completion_pct']:.1f}%",
				row_data["last_update"],
				row_data["updated_by"],
			]
		)

	# Стилі для даних
	for row in ws.iter_rows(min_row=5, max_row=ws.max_row, min_col=1, max_col=8):
		for cell in row:
			cell.alignment = wrap
			cell.border = border

			# Підсвітка статусу
			if cell.column == 2:  # Колонка "Статус"
				if "✓" in str(cell.value):
					cell.fill = PatternFill("solid", fgColor="C6EFCE")  # Зелений
				elif "✗" in str(cell.value):
					cell.fill = PatternFill("solid", fgColor="FFC7CE")  # Червоний
				elif "⚠" in str(cell.value):
					cell.fill = PatternFill("solid", fgColor="FFEB9C")  # Жовтий

	# Рядок підсумків
	last_data_row = ws.max_row
	total_row = last_data_row + 1
	ws.append(
		[
			"Разом",
			"",
			f"=SUM(C5:C{last_data_row})",
			f"=SUM(D5:D{last_data_row})",
			f"=SUM(E5:E{last_data_row})",
			f"=AVERAGE(F5:F{last_data_row})",
			"",
			"",
		]
	)
	for cell in ws[total_row]:
		cell.font = bold
		cell.border = border
	ws[f"A{total_row}"].alignment = center

	# Налаштування
	ws.freeze_panes = "A5"
	ws.auto_filter.ref = f"A4:H{total_row}"
	_autowidth(ws)

	# Створити окремий аркуш з деталями незаповнених показників
	ws_details = wb.create_sheet("Незаповнені показники")
	ws_details.append(["Організація", "ID показника", "Назва показника"])
	for cell in ws_details[1]:
		cell.fill = head_fill
		cell.font = bold
		cell.alignment = center
		cell.border = border

	for row_data in report_data:
		if row_data["unfilled_items"]:
			for item in row_data["unfilled_items"]:
				parts = item.split(": ", 1)
				ws_details.append(
					[
						row_data["organization"],
						parts[0] if len(parts) > 0 else "",
						parts[1] if len(parts) > 1 else "",
					]
				)

	for row in ws_details.iter_rows(min_row=2, max_row=ws_details.max_row, min_col=1, max_col=3):
		for cell in row:
			cell.alignment = wrap
			cell.border = border

	ws_details.freeze_panes = "A2"
	ws_details.auto_filter.ref = f"A1:C{ws_details.max_row}"
	_autowidth(ws_details)

	# Зберегти файл
	bio = io.BytesIO()
	wb.save(bio)

	safe_period = str(the_period).replace("/", "-").replace("\\", "-").replace(" ", "_")
	filename = f"Completion_Report_{safe_period}.xlsx"

	file_url = _save_bytes_as_private_file(filename, bio.getvalue())

	return {
		"file_url": file_url,
		"total_orgs": len(orgs),
		"filled_orgs": filled_count,
		"unfilled_orgs": unfilled_count,
	}
