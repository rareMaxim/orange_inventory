# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, nowdate


class oiPeriodicReport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		attachment_date: DF.Datetime | None
		attachment_notes: DF.SmallText | None
		description: DF.TextEditor | None
		download_template_html: DF.HTML | None
		filled_form_attachment: DF.Attach | None
		import_date: DF.Datetime | None
		import_details: DF.LongText | None
		import_status: DF.Literal["", "Очікує", "В процесі", "Успішно", "Помилка"]
		organization: DF.Link
		period: DF.Data
		report_type: DF.Literal["Квартальний", "Річний"]
		status: DF.Literal[
			"Чернетка", "Очікує заповнення", "Заповнено", "Імпортовано", "Прийнято", "Відхилено"
		]
		submission_deadline: DF.Date | None
		submitted_date: DF.Datetime | None
	# end: auto-generated types

	def before_save(self):
		"""Автоматичні дії перед збереженням"""
		# Встановити дату прикріплення якщо файл змінився
		if self.has_value_changed("filled_form_attachment") and self.filled_form_attachment:
			self.attachment_date = now()

			# Автоматично змінити статус на "Заповнено" якщо файл прикріплено
			if self.status == "Очікує заповнення":
				self.status = "Заповнено"

	def validate(self):
		"""Валідація документа"""
		# Перевірка формату періоду
		self._validate_period_format()

		# Перевірка унікальності (організація + період)
		self._check_duplicate_report()

	def _validate_period_format(self):
		"""Перевірка формату періоду"""
		import re

		if not self.period:
			return

		# Квартальний: YYYY-Q1/Q2/Q3/Q4
		quarterly_pattern = r"^\d{4}-Q[1-4]$"
		# Річний: YYYY
		yearly_pattern = r"^\d{4}$"

		if self.report_type == "Квартальний":
			if not re.match(quarterly_pattern, self.period):
				frappe.throw(
					"Некоректний формат періоду для квартального звіту. "
					"Очікується формат: РРРР-Q1/Q2/Q3/Q4 (наприклад, 2025-Q1)"
				)
		elif self.report_type == "Річний":
			if not re.match(yearly_pattern, self.period):
				frappe.throw(
					"Некоректний формат періоду для річного звіту. "
					"Очікується формат: РРРР (наприклад, 2025)"
				)

	def _check_duplicate_report(self):
		"""Перевірка чи не існує вже звіт для цієї організації за цей період"""
		if self.is_new():
			existing = frappe.db.exists(
				"oiPeriodicReport",
				{"organization": self.organization, "period": self.period, "name": ["!=", self.name]},
			)
			if existing:
				frappe.throw(
					f"Звіт для організації '{self.organization}' за період '{self.period}' вже існує"
				)


@frappe.whitelist()
def download_template(report_id: str):
	"""
	Завантажити шаблон Excel для заповнення.

	Args:
	    report_id: ID документа oiPeriodicReport

	Returns:
	    dict: {"file_url": str}
	"""
	report = frappe.get_doc("oiPeriodicReport", report_id)

	# Викликати існуючий метод export_org_template з oiHromadaSurvey
	result = frappe.call(
		"orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.export_org_template",
		org=report.organization,
		period=report.period,
	)

	return result


@frappe.whitelist()
def import_from_attachment(report_id: str, force_reimport: int = 0):
	"""
	Імпортувати дані з прикріпленого Excel файлу.

	Args:
	    report_id: ID документа oiPeriodicReport
	    force_reimport: 1 = ре-імпорт (навіть якщо вже імпортовано)

	Returns:
	    dict: Результат імпорту
	"""
	report = frappe.get_doc("oiPeriodicReport", report_id)

	if not report.filled_form_attachment:
		frappe.throw("Файл не прикріплено. Будь ласка, спочатку прикріпіть заповнену форму.")

	# Перевірка чи це ре-імпорт
	is_reimport = force_reimport or report.import_status == "Успішно"

	# Зберегти попередні деталі для історії
	if is_reimport and report.import_details:
		previous_import = {
			"date": report.import_date,
			"status": report.import_status,
			"details": report.import_details,
		}
		# Зберегти в child table (якщо потрібно) або в примітках
		_add_import_history_note(report, previous_import)

	# Оновити статус
	report.import_status = "В процесі"
	report.import_date = now()
	report.save(ignore_permissions=True)
	frappe.db.commit()

	try:
		# Викликати існуючий метод імпорту з oiHromadaSurvey
		result = frappe.call(
			"orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.import_from_excel",
			file_url=report.filled_form_attachment,
			org=report.organization,
		)

		# Оновити статус документа
		if result.get("status") == "success":
			report.import_status = "Успішно"
			report.status = "Імпортовано"
			report.submitted_date = now()

			# Форматувати деталі імпорту
			details = [
				"✓ Імпорт завершено успішно",
				f"  • Оновлено записів: {result.get('updated', 0)}",
				f"  • Пропущено записів: {result.get('skipped', 0)}",
			]

			if result.get("errors"):
				details.append(f"\n⚠ Помилки ({len(result['errors'])}):")
				for error in result["errors"][:10]:  # Перші 10 помилок
					details.append(f"  • {error}")
				if len(result["errors"]) > 10:
					details.append(f"  ... та ще {len(result['errors']) - 10} помилок")

			if result.get("details"):
				details.append(f"\n📝 Змінені значення ({len(result['details'])}):")
				for detail in result["details"][:20]:  # Перші 20 змін
					details.append(f"  • {detail['id']}: {detail['old_value']} → {detail['new_value']}")
				if len(result["details"]) > 20:
					details.append(f"  ... та ще {len(result['details']) - 20} змін")

			report.import_details = "\n".join(details)
		else:
			report.import_status = "Помилка"
			report.import_details = "❌ Помилка імпорту:\n" + "\n".join(
				result.get("errors", ["Невідома помилка"])
			)

		report.save(ignore_permissions=True)
		frappe.db.commit()

		return result

	except Exception as e:
		# Обробка помилок
		report.import_status = "Помилка"
		report.import_details = f"❌ Помилка імпорту: {str(e)}"
		report.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.throw(f"Помилка при імпорті даних: {str(e)}")


def _add_import_history_note(report, previous_import: dict):
	"""
	Додати коментар з історією попереднього імпорту.

	Args:
	    report: Документ oiPeriodicReport
	    previous_import: Словник з деталями попереднього імпорту
	"""
	from frappe.utils import get_datetime

	history_text = f"""
<div style="border-left: 3px solid #ffc107; padding-left: 10px; margin: 10px 0;">
	<strong>🔄 Ре-імпорт</strong><br>
	<small>Попередній імпорт:</small><br>
	• Дата: {get_datetime(previous_import['date']).strftime('%d.%m.%Y %H:%M')}<br>
	• Статус: {previous_import['status']}<br>
	<details>
		<summary>Деталі попереднього імпорту</summary>
		<pre style="font-size: 11px; max-height: 200px; overflow-y: auto;">{previous_import['details']}</pre>
	</details>
</div>
	"""

	# Додати коментар до документа
	report.add_comment(comment_type="Info", text=history_text)


@frappe.whitelist()
def bulk_create_reports(
	organizations: list | str,
	period: str,
	report_type: str = "Квартальний",
	submission_deadline: str | None = None,
):
	"""
	Масове створення звітів для кількох організацій.

	Args:
	    organizations: Список ID організацій або JSON string
	    period: Період звіту (напр. "2025-Q1")
	    report_type: Тип звіту ("Квартальний" або "Річний")
	    submission_deadline: Термін подання (опціонально)

	Returns:
	    dict: {"created": int, "skipped": int, "errors": list}
	"""
	import json

	# Парсинг списку організацій
	if isinstance(organizations, str):
		organizations = json.loads(organizations)

	created = 0
	skipped = 0
	errors = []
	created_reports = []

	for org in organizations:
		try:
			# Перевірити чи не існує вже такий звіт
			existing = frappe.db.exists("oiPeriodicReport", {"organization": org, "period": period})

			if existing:
				skipped += 1
				continue

			# Створити новий звіт
			report = frappe.get_doc(
				{
					"doctype": "oiPeriodicReport",
					"organization": org,
					"period": period,
					"report_type": report_type,
					"status": "Очікує заповнення",
					"submission_deadline": submission_deadline,
				}
			)
			report.insert(ignore_permissions=True)
			created += 1
			created_reports.append(report.name)

		except Exception as e:
			errors.append(f"Організація {org}: {str(e)}")
			continue

	frappe.db.commit()

	return {"created": created, "skipped": skipped, "errors": errors, "report_ids": created_reports}


@frappe.whitelist()
def get_overdue_reports(days_overdue: int = 0):
	"""
	Отримати список прострочених звітів.

	Args:
	    days_overdue: Кількість днів після дедлайну (0 = всі прострочені)

	Returns:
	    list: Список прострочених звітів
	"""
	from frappe.utils import add_days

	filters = {
		"status": ["in", ["Чернетка", "Очікує заповнення", "Заповнено"]],
		"submission_deadline": ["<", nowdate()],
	}

	if days_overdue > 0:
		cutoff_date = add_days(nowdate(), -days_overdue)
		filters["submission_deadline"] = ["<", cutoff_date]

	reports = frappe.get_all(
		"oiPeriodicReport",
		filters=filters,
		fields=["name", "period", "organization", "status", "submission_deadline", "filled_form_attachment"],
		order_by="submission_deadline asc",
	)

	# Додати деталі організації
	for report in reports:
		org_data = frappe.db.get_value(
			"oiOrganization", report.organization, ["organization_name", "email"], as_dict=True
		)
		if org_data:
			report.update(org_data)

	return reports


@frappe.whitelist()
def get_organizations_with_indicators(txt: str = ""):
	"""
	Отримати список організацій, які мають показники в oiHromadaSurvey.

	Args:
	    txt: Текст для фільтрації (опціонально)

	Returns:
	    list: Список організацій у форматі для MultiSelectList
	"""
	# Отримати унікальні організації з oiHromadaSurvey
	query = """
		SELECT DISTINCT
			org.name as value,
			org.organization_name as description,
			COUNT(survey.name) as indicator_count
		FROM `taboiOrganization` org
		INNER JOIN `taboiHromadaSurvey` survey
			ON survey.master_info = org.name
		WHERE org.enabled = 1
			AND survey.enabled = 1
			AND survey.is_group = 0
	"""

	# Додати фільтр за текстом
	if txt:
		query += """
			AND (
				org.name LIKE %(txt)s
				OR org.organization_name LIKE %(txt)s
				OR org.abbreviation LIKE %(txt)s
			)
		"""

	query += """
		GROUP BY org.name, org.organization_name
		ORDER BY org.organization_name
	"""

	results = frappe.db.sql(query, {"txt": f"%{txt}%"}, as_dict=True)

	# Форматувати для MultiSelectList
	return [
		{"value": r.value, "description": f"{r.description} ({r.indicator_count} показників)"}
		for r in results
	]


@frappe.whitelist()
def send_reminder_emails(report_ids: list | str):
	"""
	Відправити нагадування про заповнення звітів.

	Args:
	    report_ids: Список ID звітів або JSON string

	Returns:
	    dict: {"sent": int, "failed": int, "errors": list}
	"""
	import json

	if isinstance(report_ids, str):
		report_ids = json.loads(report_ids)

	sent = 0
	failed = 0
	errors = []

	for report_id in report_ids:
		try:
			report = frappe.get_doc("oiPeriodicReport", report_id)
			org = frappe.get_doc("oiOrganization", report.organization)

			if not org.email:
				errors.append(f"{report_id}: Організація не має email")
				failed += 1
				continue

			# Визначити тип нагадування
			if report.status == "Очікує заповнення":
				subject = f"Нагадування: Заповніть звіт за {report.period}"
				message = f"""
					<p>Шановні колеги,</p>
					<p>Нагадуємо, що необхідно заповнити звіт за період <strong>{report.period}</strong>.</p>
					<p><strong>Термін подання:</strong> {report.submission_deadline or 'не вказано'}</p>
					<p><strong>Інструкції:</strong></p>
					<ol>
						<li>Відкрийте звіт у системі: <a href="{frappe.utils.get_url_to_form('oiPeriodicReport', report.name)}">{report.name}</a></li>
						<li>Завантажте шаблон Excel</li>
						<li>Заповніть всі необхідні поля</li>
						<li>Прикріпіть заповнений файл до звіту</li>
					</ol>
					<p>З повагою,<br>Orange Inventory</p>
				"""
			elif report.status == "Заповнено":
				subject = f"Нагадування: Підтвердіть імпорт звіту за {report.period}"
				message = f"""
					<p>Шановні колеги,</p>
					<p>Ви прикріпили заповнену форму звіту за період <strong>{report.period}</strong>, але дані ще не імпортовано.</p>
					<p>Будь ласка, натисніть кнопку "Імпортувати дані" у документі звіту.</p>
					<p><a href="{frappe.utils.get_url_to_form('oiPeriodicReport', report.name)}">Перейти до звіту</a></p>
					<p>З повагою,<br>Orange Inventory</p>
				"""
			else:
				continue

			frappe.sendmail(recipients=[org.email], subject=subject, message=message)
			sent += 1

		except Exception as e:
			errors.append(f"{report_id}: {str(e)}")
			failed += 1

	return {"sent": sent, "failed": failed, "errors": errors}
