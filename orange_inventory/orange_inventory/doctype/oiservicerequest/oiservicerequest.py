# Copyright (c) 2025, Maxim Sysoev and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_fullname, now, nowdate


class oiServiceRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from orange_inventory.orange_inventory.doctype.oiservicerequestactivity.oiservicerequestactivity import (
			oiServiceRequestActivity,
		)

		activity_log: DF.Table[oiServiceRequestActivity]
		actual_hours: DF.Duration | None
		asset_inventory_no: DF.Data | None
		asset_location: DF.Data | None
		asset_serial_no: DF.Data | None
		assigned_to: DF.Link | None
		completion_date: DF.Datetime | None
		creation_date: DF.Date | None
		description: DF.TextEditor | None
		due_date: DF.Date | None
		estimated_hours: DF.Duration | None
		naming_series: DF.Literal["SR-.YYYY.-.#####", "MNT-.YYYY.-.#####", "INC-.YYYY.-.#####"]
		priority: DF.Literal[
			"\u041d\u0438\u0437\u044c\u043a\u0438\u0439",
			"\u0421\u0435\u0440\u0435\u0434\u043d\u0456\u0439",
			"\u0412\u0438\u0441\u043e\u043a\u0438\u0439",
			"\u041a\u0440\u0438\u0442\u0438\u0447\u043d\u0438\u0439",
		]
		related_asset: DF.Link | None
		request_type: DF.Autocomplete
		requester: DF.Link
		requester_contact: DF.Data | None
		requester_organization: DF.Link | None
		resolution: DF.TextEditor | None
		status: DF.Literal[
			"\u041d\u043e\u0432\u0430",
			"\u041f\u0440\u0438\u0439\u043d\u044f\u0442\u0430",
			"\u0412 \u0440\u043e\u0431\u043e\u0442\u0456",
			"\u041e\u0447\u0456\u043a\u0443\u0454 \u0437\u0430\u043f\u0447\u0430\u0441\u0442\u0438\u043d\u0438",
			"\u041e\u0447\u0456\u043a\u0443\u0454 \u043f\u0456\u0434\u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u043d\u044f",
			"\u0412\u0438\u043a\u043e\u043d\u0430\u043d\u0430",
			"\u0412\u0456\u0434\u0445\u0438\u043b\u0435\u043d\u0430",
			"\u0417\u0430\u043a\u0440\u0438\u0442\u0430",
		]
		title: DF.Data
	# end: auto-generated types

	def before_insert(self):
		"""Встановлюємо дату створення та додаємо запис до журналу активності"""
		self.creation_date = nowdate()
		self.add_activity("Створено", f"Заявка створена користувачем {get_fullname()}")

	def before_save(self):
		"""Відстежуємо зміни та додаємо їх до журналу активності"""
		if self.is_new():
			return

		# Отримуємо попередню версію документа
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		# Відстежуємо зміни в ключових полях
		tracked_fields = {
			"status": "Статус",
			"assigned_to": "Призначено",
			"priority": "Пріоритет",
			"due_date": "Планова дата",
		}

		for field, label in tracked_fields.items():
			old_value = getattr(old_doc, field, None)
			new_value = getattr(self, field, None)

			if old_value != new_value:
				self.add_activity(
					"Оновлено",
					f"Змінено {label}: з '{old_value or 'Не встановлено'}' на '{new_value or 'Не встановлено'}'",
					old_value,
					new_value,
				)

		# Автоматично встановлюємо дату завершення при зміні статусу
		if old_doc.status != self.status:
			if self.status in ["Виконана", "Закрита"]:
				if not self.completion_date:
					self.completion_date = nowdate()

	def add_activity(self, activity_type, description, previous_value=None, new_value=None):
		"""Додає запис до журналу активності"""
		self.append(
			"activity_log",
			{
				"activity_date": now(),
				"activity_type": activity_type,
				"description": description,
				"user": frappe.session.user,
				"previous_value": str(previous_value) if previous_value else None,
				"new_value": str(new_value) if new_value else None,
			},
		)

	def add_comment(self, comment):
		"""Додає коментар до заявки"""
		if self.comments:
			self.comments += f"\n\n[{now()}] {get_fullname()}: {comment}"
		else:
			self.comments = f"[{now()}] {get_fullname()}: {comment}"

		self.add_activity("Коментар", f"Додано коментар: {comment}")
		self.save()

	@frappe.whitelist()
	def assign_to_user(self, user):
		"""Призначає заявку користувачу"""
		old_assigned = self.assigned_to
		self.assigned_to = user
		self.status = "Прийнята" if self.status == "Нова" else self.status

		self.add_activity(
			"Призначено", f"Заявка призначена користувачу {get_fullname(user)}", old_assigned, user
		)
		self.save()

	@frappe.whitelist()
	def start_work(self):
		"""Починає роботу над заявкою"""
		if self.status not in ["Прийнята", "Нова"]:
			frappe.throw(_("Неможливо розпочати роботу. Поточний статус: {0}").format(self.status))

		self.status = "В роботі"
		self.add_activity("Оновлено", "Розпочато роботу над заявкою")
		self.save()

	@frappe.whitelist()
	def complete_work(self, resolution=None):
		"""Завершує роботу над заявкою"""
		if self.status not in ["В роботі", "Очікує підтвердження"]:
			frappe.throw(_("Неможливо завершити роботу. Поточний статус: {0}").format(self.status))

		self.status = "Виконана"
		self.completion_date = nowdate()

		if resolution:
			self.resolution = resolution

		self.add_activity("Виконано", "Роботу завершено")
		self.save()

	def validate(self):
		"""Перевірка даних перед збереженням"""
		# Перевіряємо, що заявник належить до організації
		if self.requester:
			requester_org = frappe.db.get_value("oiEmployee", self.requester, "organization")
			if requester_org:
				self.requester_organization = requester_org

		# Перевіряємо права доступу до активу
		if self.related_asset and self.requester_organization:
			asset_owner = frappe.db.get_value("oiAsset", self.related_asset, "current_owner")
			if asset_owner != self.requester_organization:
				frappe.throw(_("Ви не маєте доступу до цього активу"))

		# Перевіряємо дату виконання
		if self.due_date and self.creation_date:
			if self.due_date < self.creation_date:
				frappe.throw(_("Планова дата виконання не може бути раніше дати створення"))


def get_permission_query_conditions(user):
	"""Фільтрує заявки за організацією користувача"""
	if "System Manager" in frappe.get_roles(user):
		return ""

	# Отримуємо організацію користувача
	user_org = frappe.db.get_value("oiEmployee", {"user": user}, "organization")

	if user_org:
		# Користувач може бачити заявки своєї організації або призначені йому
		return f"""
			(`taboiServiceRequest`.`requester_organization` = '{user_org}'
			OR `taboiServiceRequest`.`assigned_to` IN (
				SELECT name FROM `taboiEmployee` WHERE user = '{user}'
			))
		"""
	else:
		# Якщо у користувача немає організації, показуємо тільки призначені йому
		return f"""
			`taboiServiceRequest`.`assigned_to` IN (
				SELECT name FROM `taboiEmployee` WHERE user = '{user}'
			)
		"""


def has_permission(doc, user, permission_type):
	"""Перевіряє права доступу до конкретного документа"""
	if "System Manager" in frappe.get_roles(user):
		return True

	user_employee = frappe.db.get_value("oiEmployee", {"user": user}, "name")

	# Власник заявки або призначений виконавець може читати/редагувати
	if doc.requester == user_employee or doc.assigned_to == user_employee:
		return True

	# Співробітники тієї ж організації можуть читати
	if permission_type == "read":
		user_org = frappe.db.get_value("oiEmployee", {"user": user}, "organization")
		if user_org and doc.requester_organization == user_org:
			return True

	return False


@frappe.whitelist()
def create_service_request_from_asset(asset_name, request_type, title, description):
	"""Створює заявку на обслуговування з активу"""
	# Перевіряємо доступ до активу
	# asset = frappe.get_doc("oiAsset", asset_name)

	# Отримуємо поточного користувача як співробітника
	current_user_employee = frappe.db.get_value("oiEmployee", {"user": frappe.session.user}, "name")
	if not current_user_employee:
		frappe.throw(_("Ви не зареєстровані як співробітник"))

	# Створюємо заявку
	service_request = frappe.new_doc("oiServiceRequest")
	service_request.update(
		{
			"title": title,
			"request_type": request_type,
			"description": description,
			"related_asset": asset_name,
			"requester": current_user_employee,
			"priority": "Середній",
		}
	)

	service_request.insert()
	return service_request.name


@frappe.whitelist()
def get_dashboard_data():
	"""Отримує дані для дашборду заявок"""
	# Статистика по статусах
	status_stats = frappe.db.sql(
		"""
		SELECT status, COUNT(*) as count
		FROM `taboiServiceRequest`
		GROUP BY status
	""",
		as_dict=True,
	)

	# Заявки по пріоритетах
	priority_stats = frappe.db.sql(
		"""
		SELECT priority, COUNT(*) as count
		FROM `taboiServiceRequest`
		GROUP BY priority
	""",
		as_dict=True,
	)

	# Найактивніші типи заявок
	request_type_stats = frappe.db.sql(
		"""
		SELECT request_type, COUNT(*) as count
		FROM `taboiServiceRequest`
		GROUP BY request_type
		ORDER BY count DESC
		LIMIT 5
	""",
		as_dict=True,
	)

	# Прострочені заявки
	overdue_count = frappe.db.count(
		"oiServiceRequest",
		{"due_date": ["<", nowdate()], "status": ["not in", ["Виконана", "Закрита", "Відхилена"]]},
	)

	return {
		"status_stats": status_stats,
		"priority_stats": priority_stats,
		"request_type_stats": request_type_stats,
		"overdue_count": overdue_count,
	}
