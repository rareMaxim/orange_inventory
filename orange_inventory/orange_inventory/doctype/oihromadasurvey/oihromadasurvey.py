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
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

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


def _get_group_path(docname: str) -> str:
	"""Повертає шлях груп для вузла-листа: 'Група / Підгрупа / ...'."""
	# Беремо усіх предків типу 'Група', від кореня до батька
	node = frappe.db.get_value("oiHromadaSurvey", docname, ["lft", "rgt"], as_dict=True)
	if not node:
		return ""
	rows = frappe.db.sql(
		"""
        select name, title
        from `taboiHromadaSurvey`
        where lft <= %s and rgt >= %s and type = "Група"
        order by lft asc
        """,
		(node.lft, node.rgt),
		as_dict=True,
	)
	return " / ".join([r.title for r in rows])


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
	ws.merge_cells("A1:H1")
	ws["A1"] = f"Організація: {org_meta['title']}"
	ws["A1"].font = Font(bold=True, size=13)
	ws["A1"].alignment = center

	ws.merge_cells("A2:H2")
	extra = f" | ЄДРПОУ: {org_meta['tax_code']}" if org_meta.get("tax_code") else ""
	ws["A2"] = f"Період: {period}{extra}"
	ws["A2"].alignment = center

	ws.append([""] * 8)  # рядок 3 — порожній

	# Заголовки (рядок 4)
	headers = [
		"Шлях групи",
		"ID",
		"Назва показника",
		"Тип",
		"Періодичність",
		"Поточне значення",
		"Значення для заповнення",
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

		ws.append(
			[
				path,  # A
				r.get("id") or "",  # B
				r.get("title") or "",  # C
				r.get("type") or "",  # D
				r.get("frequency") or "",  # E
				f_value,  # F (Поточне значення)
				g_value,  # G (Значення для заповнення)
				r.get("description") or "",  # H (Примітка)
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
		dv_block.add(f"H5:H{ws.max_row}")

	# Стилі для тіла таблиці
	for row in ws.iter_rows(min_row=5, max_row=ws.max_row, min_col=1, max_col=8):
		for cell in row:
			cell.alignment = wrap
			cell.border = border

	# Freeze + фільтри
	ws.freeze_panes = "A5"
	ws.auto_filter.ref = f"A4:H{ws.max_row}"

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
		"oiOrganization",
		org,
		["organization_name", "abbreviation", "tax_code", "name"],
		as_dict=True,
	)
	if not row:
		return {"title": str(org), "abbreviation": "", "tax_code": "", "name": str(org)}
	title = row.organization_name or row.abbreviation or row.name
	return {
		"title": title,
		"abbreviation": row.abbreviation or "",
		"tax_code": row.tax_code or "",
		"name": row.name or org,
	}


@frappe.whitelist()
def export_org_template(org: str, period: str | None = None):
	if not org:
		frappe.throw("Не вказано розпорядника (org).")
	rows = _fetch_leaf_rows_for_org(org)
	if not rows:
		frappe.throw(f"Для розпорядника '{org}' не знайдено показників.")

	org_meta = _get_org_meta(org)
	the_period = period or nowdate()

	wb = Workbook()
	_make_data_sheet(wb, org_meta, the_period, rows)

	bio = io.BytesIO()
	wb.save(bio)
	safe_title = org_meta["title"].replace("/", "-").replace("\\", "-")
	filename = f"{safe_title}_{the_period}.xlsx".replace(" ", "_")

	url = _save_bytes_as_private_file(
		filename,
		bio.getvalue(),
		attached_to_doctype="oiOrganization",
		attached_to_name=org,  # системне name (ORG-xxxxx)
	)
	return {"file_url": url}


@frappe.whitelist()
def export_all_org_templates(period: str | None = None):
	"""Згенерувати ZIP з шаблонами для всіх активних розпорядників + Summary.xlsx.
	Summary містить: Організація, Всього пунктів, К-ть only_admin, К-ть пунктів для заповнення.
	period (напр. '2025-Q4') можна передати з діалогу; якщо не вказано — nowdate()."""
	orgs = frappe.get_all(
		"oiOrganization",
		filters={"enabled": 1},
		pluck="name",
	)
	if not orgs:
		frappe.throw("Немає активних організацій для експорту.")

	the_period = period or nowdate()
	safe_period = str(the_period).replace("/", "-").replace("\\", "-").replace(" ", "_")

	tmpdir = tempfile.mkdtemp()
	paths: list[tuple[str, str]] = []  # [(файл_шляг, org_name)]
	# [(org_title, total, admin, fillable)]
	summary_rows: list[tuple[str, int, int, int]] = []

	for org in orgs:
		rows = _fetch_leaf_rows_for_org(org)  # включає only_admin
		total_count = len(rows)
		admin_count = sum(1 for r in rows if cint(r.get("only_admin")))
		fillable_count = total_count - admin_count

		org_meta = _get_org_meta(org)

		# Згенеруємо XLSX для організації (навіть якщо рядків 0 — отримаємо «порожній» шаблон з шапкою)
		wb = Workbook()
		_make_data_sheet(wb, org_meta, the_period, rows)
		safe_title = org_meta["title"].replace("/", "-").replace("\\", "-")
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
