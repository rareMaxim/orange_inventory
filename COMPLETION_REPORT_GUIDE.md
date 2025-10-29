# Звіт про заповнення показників - Керівництво користувача

## 📋 Огляд

Функціонал "Звіт про заповнення показників" дозволяє відстежувати, які організації заповнили свої показники, а які ще ні. Це допомагає контролювати процес збору даних та нагадувати організаціям про необхідність заповнення.

## 🎯 Основні можливості

### 1. **Звіт про заповнення**
- Показує статус заповнення для кожної організації
- Відображає кількість заповнених та незаповнених показників
- Вказує дату останнього оновлення та користувача, який вніс зміни
- Розраховує процент виконання для кожної організації
- Містить детальний список незаповнених показників

### 2. **Відстеження в шаблонах Excel**
- В експортованих шаблонах Excel додано колонку "Остання зміна"
- Показує дату та час останнього оновлення кожного показника
- Допомагає визначити застарілі дані

## 📊 Як використовувати

### Генерація звіту про заповнення

1. **Перейдіть до списку oiHromadaSurvey**
   - Відкрийте DocType "oiHromadaSurvey"
   - Натисніть на меню (три крапки)

2. **Виберіть "Звіт про заповнення показників"**
   - У діалоговому вікні вкажіть період (напр. "2025-Q1")
   - Натисніть "Згенерувати звіт"

3. **Перегляньте результати**
   - Система автоматично відкриє згенерований Excel файл
   - У повідомленні з'явиться статистика: скільки організацій заповнили показники

### Структура звіту

#### Аркуш "Звіт про заповнення"

| Колонка | Опис |
|---------|------|
| **Організація** | Назва організації |
| **Статус** | ✓ Заповнено / ⚠ Частково (X%) / ✗ Не заповнено |
| **Всього показників** | Загальна кількість показників для заповнення |
| **Заповнено** | Кількість заповнених показників |
| **Не заповнено** | Кількість незаповнених показників |
| **% виконання** | Процент заповнення |
| **Остання зміна** | Дата та час останнього оновлення |
| **Змінив** | Користувач, який вніс останні зміни |

**Колірне кодування:**
- 🟢 **Зелений** - Заповнено повністю (100%)
- 🟡 **Жовтий** - Частково заповнено (1-99%)
- 🔴 **Червоний** - Не заповнено (0%)

#### Аркуш "Незаповнені показники"

Містить детальний список усіх незаповнених показників:
- Організація
- ID показника
- Назва показника

### Перегляд дати оновлення в шаблонах Excel

При експорті шаблонів для організацій (через "Export Excel Template" або "Export All Templates (ZIP)"):

1. У колонці **H** ("Остання зміна") відображається дата та час останнього оновлення
2. Формат: `ДД.ММ.РРРР ГГ:ХХ` (наприклад, `23.10.2025 14:30`)
3. Якщо показник ще не оновлювався - відображається `-`

## 🔧 API методи

### `generate_completion_report(period=None)`

Генерує звіт про заповнення показників для всіх організацій.

**Параметри:**
- `period` (str, опціонально): Період для звіту (напр. '2025-Q1'). Якщо не вказано - використовується поточна дата.

**Повертає:**
```python
{
    "file_url": str,  # URL згенерованого Excel файлу
    "total_orgs": int,  # Загальна кількість організацій
    "filled_orgs": int,  # Кількість організацій що заповнили
    "unfilled_orgs": int  # Кількість організацій що не заповнили
}
```

**Приклад виклику через API:**

```bash
# Через curl
curl -X POST "https://your-site.com/api/method/orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.generate_completion_report" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"period": "2025-Q1"}'
```

**Приклад виклику через frappe.call:**

```javascript
frappe.call({
    method: "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.generate_completion_report",
    args: {
        period: "2025-Q1"
    },
    callback: function(r) {
        if (r.message && r.message.file_url) {
            console.log("Звіт готовий:", r.message);
            window.open(r.message.file_url, "_blank");
        }
    }
});
```

**Приклад виклику через Python:**

```python
import frappe

# Згенерувати звіт
result = frappe.call(
    "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.generate_completion_report",
    period="2025-Q1"
)

print(f"Всього організацій: {result['total_orgs']}")
print(f"Заповнили: {result['filled_orgs']}")
print(f"Не заповнили: {result['unfilled_orgs']}")
print(f"Файл: {result['file_url']}")
```

## 📈 Логіка визначення заповнення

### Кількісні дані
Показник вважається **заповненим**, якщо:
- Поле `int_data` не є `NULL` (навіть якщо значення = 0)

### Якісні дані
Показник вважається **заповненим**, якщо:
- В історії змін (`oiHromadaSurveyHistory`) є хоча б один запис для цього показника
- Це означає, що користувач свідомо встановив значення "Так" або "Ні"

### Виключення
- Показники з прапорцем `only_admin = 1` **НЕ враховуються** у звіті
- Неактивні показники (`enabled = 0`) також не враховуються

## 💡 Практичні сценарії використування

### 1. Щотижневий моніторинг заповнення
```python
# Автоматична генерація звіту щотижня
def weekly_completion_report():
    import frappe
    from frappe.utils import nowdate, get_first_day, get_last_day

    # Визначити поточний квартал
    today = nowdate()
    period = f"{today[:4]}-Q{(int(today[5:7])-1)//3 + 1}"

    # Згенерувати звіт
    result = frappe.call(
        "orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey.generate_completion_report",
        period=period
    )

    # Відправити на email
    if result['unfilled_orgs'] > 0:
        frappe.sendmail(
            recipients=["manager@example.com"],
            subject=f"Звіт про заповнення показників - {period}",
            message=f"""
                Не заповнили показники: {result['unfilled_orgs']} організацій
                Заповнили: {result['filled_orgs']} організацій
                Деталі у вкладеному файлі.
            """,
            attachments=[{"file_url": result['file_url']}]
        )
```

### 2. Нагадування організаціям
```python
def send_reminders_to_unfilled():
    """Відправити нагадування організаціям що не заповнили показники"""
    import frappe

    # Отримати список організацій
    orgs = frappe.get_all("oiOrganization", filters={"enabled": 1}, fields=["name", "email"])

    for org in orgs:
        # Перевірити чи є незаповнені показники
        unfilled_count = frappe.db.count(
            "oiHromadaSurvey",
            filters={
                "master_info": org.name,
                "is_group": 0,
                "enabled": 1,
                "only_admin": 0,
                "int_data": ["is", "not set"]
            }
        )

        if unfilled_count > 0:
            frappe.sendmail(
                recipients=[org.email],
                subject="Нагадування: Заповніть показники",
                message=f"У вас {unfilled_count} незаповнених показників. Будь ласка, заповніть їх."
            )
```

## 🎨 Налаштування та кастомізація

### Зміна формату дати
Якщо потрібно змінити формат відображення дати в звітах:

```python
# У файлі oihromadasurvey.py знайдіть:
h_value = get_datetime(modified_date).strftime("%d.%m.%Y %H:%M")

# Змініть на бажаний формат, наприклад:
h_value = get_datetime(modified_date).strftime("%Y-%m-%d %H:%M:%S")  # ISO формат
h_value = get_datetime(modified_date).strftime("%d/%m/%Y")  # Тільки дата
```

### Додавання додаткових колонок
Щоб додати додаткову колонку в звіт про заповнення:

1. Відредагуйте `generate_completion_report()` в [oihromadasurvey.py](cci:7://file:///home/frappe/frappe-bench/apps/orange_inventory/orange_inventory/orange_inventory/doctype/oihromadasurvey/oihromadasurvey.py:900:0-1137:1)
2. Додайте нову колонку в масив `headers`
3. Додайте відповідне значення в `ws.append([...])`

## ❓ FAQ

**Q: Чи можна отримати звіт тільки для однієї організації?**
A: Наразі звіт генерується для всіх організацій. Але ви можете відфільтрувати Excel файл за колонкою "Організація".

**Q: Як часто оновлюється дата "Остання зміна"?**
A: Дата оновлюється автоматично при кожному збереженні документа oiHromadaSurvey.

**Q: Чи враховуються показники з only_admin?**
A: Ні, показники з прапорцем `only_admin = 1` не враховуються у звіті про заповнення.

**Q: Що означає "Частково заповнено"?**
A: Це означає, що організація заповнила деякі показники, але не всі. Процент відображає відсоток виконання.

**Q: Чи можна автоматизувати генерацію звітів?**
A: Так, використовуйте Scheduler Jobs в Frappe для автоматичної генерації звітів за розкладом.

## 🔗 Пов'язані документи

- [IMPORT_EXCEL_GUIDE.md](cci:7://file:///home/frappe/frappe-bench/apps/orange_inventory/IMPORT_EXCEL_GUIDE.md:0:0-0:0) - Керівництво по імпорту/експорту Excel
- [HROMADA_SURVEY_TREND_TRACKING.md](cci:7://file:///home/frappe/frappe-bench/apps/orange_inventory/HROMADA_SURVEY_TREND_TRACKING.md:0:0-0:0) - Відстеження трендів показників
- [README_IMPORT.md](cci:7://file:///home/frappe/frappe-bench/apps/orange_inventory/README_IMPORT.md:0:0-0:0) - Огляд функціоналу імпорту

## 📝 Changelog

### v1.0 (2025-10-23)
- ✨ Додано функцію генерації звіту про заповнення показників
- ✨ Додано колонку "Остання зміна" в експорт Excel
- ✨ Додано кнопку в List View для генерації звіту
- ✨ Додано колірне кодування статусів організацій
- ✨ Додано детальний аркуш незаповнених показників

---

**Підтримка:** Якщо у вас виникли питання, зверніться до команди розробки або створіть issue в репозиторії проекту.
