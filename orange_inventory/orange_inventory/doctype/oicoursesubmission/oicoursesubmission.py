# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class oiCourseSubmission(Document):
	def before_insert(self):
		"""Встановлюємо дефолтні значення при створенні"""
		# Якщо дата завершення не вказана, встановлюємо поточну дату
		if not self.completion_date:
			self.completion_date = frappe.utils.today()

	def before_save(self):
		"""Автоматично оновлюємо processed_by та processed_date коли статус змінюється"""
		if self.has_value_changed("status") and self.status != "Очікує обробки":
			if not self.processed_by:
				self.processed_by = frappe.session.user
			if not self.processed_date:
				self.processed_date = frappe.utils.now()


@frappe.whitelist()
def find_employee_by_name(last_name, first_name, patronymic=None):
	"""
	Функція для пошуку співробітника по ПІБ
	Доступна тільки для авторизованих користувачів (адміністраторів)
	"""
	# Формуємо ПІБ для пошуку
	full_name_variants = []

	if patronymic:
		full_name_variants.append(f"{last_name} {first_name} {patronymic}")
		full_name_variants.append(f"{last_name} {first_name[0]}. {patronymic[0]}.")
		full_name_variants.append(f"{last_name} {first_name[0]}. {patronymic}")

	full_name_variants.append(f"{last_name} {first_name}")
	full_name_variants.append(f"{last_name} {first_name[0]}.")

	# Шукаємо співробітника
	for variant in full_name_variants:
		employees = frappe.get_all(
			"hromsEmployee",
			filters={"full_name": ["like", f"%{variant}%"]},
			fields=["name", "full_name", "department"],
			limit=10,
		)

		if employees:
			return employees

	# Якщо не знайшли точного співпадіння, шукаємо по прізвищу
	employees = frappe.get_all(
		"hromsEmployee",
		filters={"full_name": ["like", f"%{last_name}%"]},
		fields=["name", "full_name", "department"],
		limit=10,
	)

	return employees
