# Періодичні звіти (oiPeriodicReport) - Керівництво користувача

## 📋 Огляд

DocType **oiPeriodicReport** (Періодичний звіт) призначений для управління щоквартальними та щорічними звітами організацій. Він інтегрується з існуючим функціоналом імпорту/експорту Excel з oiHromadaSurvey та додає зручний workflow для відстеження заповнення звітів.

## 🎯 Основні можливості

### 1. Типи звітів
- **Квартальний звіт** - формат періоду: `РРРР-Q1/Q2/Q3/Q4` (наприклад, `2025-Q1`)
- **Річний звіт** - формат періоду: `РРРР` (наприклад, `2025`)

### 2. Статуси звіту
- **Чернетка** - початковий статус при створенні
- **Очікує заповнення** - після завантаження шаблону
- **Заповнено** - після прикріплення файлу
- **Імпортовано** - після успішного імпорту даних
- **Прийнято** - звіт затверджено адміністратором
- **Відхилено** - звіт відхилено (потребує виправлень)

### 3. Workflow процесу

```
1. Створення звіту → 2. Завантаження шаблону → 3. Заповнення форми
                                                           ↓
6. Прийняття ← 5. Імпорт даних ← 4. Прикріплення файлу ←
```

## 📝 Робота зі звітами

### Створення звіту (вручну)

1. **Перейдіть до DocType "oiPeriodicReport"**
   - Menu → Orange Inventory → Periodic Report

2. **Створіть новий документ**
   - Виберіть організацію
   - Вкажіть період (напр. "2025-Q1")
   - Виберіть тип звіту (Квартальний/Річний)
   - Вкажіть термін подання (необов'язково - встановиться автоматично)

3. **Збережіть документ**

### Завантаження шаблону Excel

1. **Відкрийте створений звіт**
2. **Натисніть "Дії" → "Завантажити шаблон Excel"**
   - Система згенерує Excel файл з поточними даними організації
   - Файл автоматично відкриється в новій вкладці
   - Статус зміниться на "Очікує заповнення"

### Заповнення та прикріплення форми

1. **Заповніть Excel файл**
   - Редагуйте тільки колонку **G** ("Значення для заповнення")
   - НЕ змінюйте структуру файлу, ID показників, назви колонок

2. **Збережіть файл на комп'ютері**

3. **Поверніться до форми звіту**
   - У полі "Заповнена форма" натисніть "Прикріпити"
   - Виберіть збережений Excel файл
   - Додайте примітки (необов'язково)
   - Збережіть документ

4. **Статус автоматично зміниться на "Заповнено"**

### Імпорт даних

1. **Після прикріплення файлу**
2. **Натисніть "Дії" → "Імпортувати дані"**
   - Підтвердіть дію
   - Система обробить файл та імпортує дані в oiHromadaSurvey
   - Статус зміниться на "Імпортовано"

3. **Перегляньте результати імпорту**
   - "Дії" → "Переглянути деталі імпорту"
   - Показує кількість оновлених записів, помилки, зміни

### Ре-імпорт даних (виправлення помилок)

**Якщо знайдено помилку після імпорту:**

1. **Виправте дані в Excel файлі**
   - Відкрийте оригінальний файл
   - Внесіть корективи
   - Збережіть

2. **Прикріпіть виправлений файл**
   - У полі "Заповнена форма" замініть файл
   - Збережіть документ

3. **Виконайте ре-імпорт**
   - "Дії" → "Ре-імпорт даних"
   - Прочитайте попередження
   - Поставте галочку "Я розумію що попередні дані будуть замінені"
   - Натисніть "Виконати ре-імпорт"

4. **Історія збережеться**
   - Деталі попереднього імпорту зберігаються в Timeline (коментарі)
   - Історія змін в oiHromadaSurveyHistory

**⚠️ Важливо:**
- Ре-імпорт замінює попередні дані
- Історія зберігається для аудиту
- Використовуйте для виправлення помилок, а не для регулярних оновлень

## 🔄 Масові операції

### Масове створення звітів

**Використання через інтерфейс:**

1. **Перейдіть до списку oiPeriodicReport**
2. **Меню → "Масове створення звітів"**
3. **Заповніть діалог:**
   - Період (напр. "2025-Q2")
   - Тип звіту (Квартальний/Річний)
   - Термін подання (опціонально)
   - Виберіть організації:
     - **Автоматично показуються тільки організації з показниками** в oiHromadaSurvey
     - Відображається кількість показників для кожної організації
     - Можна натиснути **"Вибрати всі організації"** для швидкого вибору
     - Або вибрати конкретні організації зі списку

4. **Натисніть "Створити звіти"**
   - Система створить звіти для всіх обраних організацій
   - Показує результат: створено, пропущено, помилки
   - Можна одразу відправити нагадування

**Через API:**

```javascript
frappe.call({
    method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.bulk_create_reports",
    args: {
        organizations: ["ORG-00001", "ORG-00002", "ORG-00003"],
        period: "2025-Q2",
        report_type: "Квартальний",
        submission_deadline: "2025-07-15"
    },
    callback: function(r) {
        console.log("Створено:", r.message.created);
        console.log("Пропущено:", r.message.skipped);
        console.log("ID звітів:", r.message.report_ids);
    }
});
```

**Python приклад:**

```python
import frappe

result = frappe.call(
    "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.bulk_create_reports",
    organizations=["ORG-00001", "ORG-00002"],
    period="2025-Q2",
    report_type="Квартальний",
    submission_deadline="2025-07-15"
)

print(f"Створено {result['created']} звітів")
```

### Прострочені звіти

**Через інтерфейс:**

1. **Список oiPeriodicReport → Меню → "Прострочені звіти"**
2. **Вкажіть мінімум днів прострочення** (0 = всі прострочені)
3. **Переглянете таблицю** з організаціями, термінами, статусами

**Через API:**

```javascript
frappe.call({
    method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.get_overdue_reports",
    args: {
        days_overdue: 7  // Прострочені більше ніж на 7 днів
    },
    callback: function(r) {
        console.log("Прострочених звітів:", r.message.length);
        r.message.forEach(report => {
            console.log(`${report.organization_name}: ${report.period}`);
        });
    }
});
```

### Відправка нагадувань

**Одиночне нагадування (з форми звіту):**

1. **Відкрийте звіт**
2. **"Дії" → "Відправити нагадування"**
3. **Підтвердіть відправку**

**Масові нагадування (зі списку):**

1. **Виберіть звіти (чекбокси)**
2. **Меню → "Відправити нагадування"**
3. **Підтвердіть**

**Через API:**

```javascript
frappe.call({
    method: "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.send_reminder_emails",
    args: {
        report_ids: ["PER-2025-Q1-0001", "PER-2025-Q1-0002"]
    },
    callback: function(r) {
        console.log("Відправлено:", r.message.sent);
        console.log("Помилок:", r.message.failed);
    }
});
```

## 🎨 Візуальні підказки

### Колірні індикатори статусів

| Статус | Колір | Значення |
|--------|-------|----------|
| Чернетка | Сірий | Тільки створено |
| Очікує заповнення | Помаранчевий | Шаблон завантажено, чекає заповнення |
| Заповнено | Синій | Файл прикріплено, чекає імпорту |
| Імпортовано | Зелений | Дані успішно імпортовано |
| Прийнято | Зелений | Звіт затверджено |
| Відхилено | Червоний | Потребує виправлень |
| Прострочено | Червоний | Минув термін подання |

### Формат дедлайну в списку

```
2025-07-15 (залишилось 5 днів)      - Зелений/Помаранчевий
2025-06-01 (прострочено на 10 днів) - Червоний
```

## 🔧 API Методи

### 1. download_template(report_id)

Завантажити шаблон Excel для звіту.

**Параметри:**
- `report_id` (str): ID документа oiPeriodicReport

**Повертає:**
```python
{
    "file_url": str  # URL згенерованого Excel файлу
}
```

**Приклад:**
```python
result = frappe.call(
    "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.download_template",
    report_id="PER-2025-Q1-0001"
)
print(result['file_url'])
```

### 2. import_from_attachment(report_id, force_reimport)

Імпортувати дані з прикріпленого файлу.

**Параметри:**
- `report_id` (str): ID документа oiPeriodicReport
- `force_reimport` (int, optional): 1 = ре-імпорт (замінити існуючі дані)

**Повертає:**
```python
{
    "status": "success" | "error",
    "updated": int,  # Кількість оновлених записів
    "skipped": int,  # Кількість пропущених
    "errors": list,  # Список помилок
    "details": list  # Детальна інформація про зміни
}
```

**Приклад (звичайний імпорт):**
```python
result = frappe.call(
    "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.import_from_attachment",
    report_id="PER-2025-Q1-0001"
)
print(f"Оновлено: {result['updated']}")
```

**Приклад (ре-імпорт):**
```python
# Виправлення помилок після першого імпорту
result = frappe.call(
    "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.import_from_attachment",
    report_id="PER-2025-Q1-0001",
    force_reimport=1  # Ре-імпорт
)

# Історія попереднього імпорту зберігається в Timeline
print(f"Ре-імпорт: оновлено {result['updated']} записів")
```

**Особливості ре-імпорту:**
- Автоматично зберігає історію попереднього імпорту в коментарях
- Створює нові записи в oiHromadaSurveyHistory
- Дозволяє виправляти помилки без створення нового звіту
- Зберігає audit trail для відстеження змін

### 3. bulk_create_reports(organizations, period, report_type, submission_deadline)

Масове створення звітів.

**Параметри:**
- `organizations` (list): Список ID організацій
- `period` (str): Період (напр. "2025-Q2")
- `report_type` (str): "Квартальний" або "Річний"
- `submission_deadline` (str, optional): Термін подання (YYYY-MM-DD)

**Повертає:**
```python
{
    "created": int,
    "skipped": int,
    "errors": list,
    "report_ids": list  # ID створених звітів
}
```

### 4. get_overdue_reports(days_overdue)

Отримати список прострочених звітів.

**Параметри:**
- `days_overdue` (int): Мінімум днів прострочення (0 = всі прострочені)

**Повертає:**
```python
[
    {
        "name": str,
        "period": str,
        "organization": str,
        "organization_name": str,
        "email": str,
        "status": str,
        "submission_deadline": str,
        "filled_form_attachment": str
    },
    ...
]
```

### 5. get_organizations_with_indicators(txt)

Отримати список організацій, які мають показники в oiHromadaSurvey.

**Параметри:**
- `txt` (str, optional): Текст для фільтрації за назвою організації

**Повертає:**
```python
[
    {
        "value": str,  # ID організації
        "description": str  # Назва + кількість показників
    },
    ...
]
```

**Приклад:**
```python
orgs = frappe.call(
    "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.get_organizations_with_indicators",
    txt="Київ"  # Фільтр за назвою
)

for org in orgs:
    print(f"{org['value']}: {org['description']}")
    # ORG-00001: Київська міська рада (145 показників)
```

**Особливості:**
- Показує тільки активні організації (`enabled = 1`)
- Показує тільки організації з активними показниками
- Підраховує кількість показників для кожної організації
- Виключає групи (`is_group = 0`)

### 6. send_reminder_emails(report_ids)

Відправити нагадування про заповнення.

**Параметри:**
- `report_ids` (list): Список ID звітів

**Повертає:**
```python
{
    "sent": int,
    "failed": int,
    "errors": list
}
```

## 📊 Практичні сценарії

### Сценарій 1: Щоквартальне створення звітів

```python
def create_quarterly_reports():
    """Автоматичне створення квартальних звітів для всіх організацій"""
    import frappe
    from frappe.utils import nowdate, add_months

    # Визначити поточний квартал
    today = nowdate()
    quarter = (int(today[5:7]) - 1) // 3 + 1
    period = f"{today[:4]}-Q{quarter}"

    # Термін подання - 15 число наступного місяця після кварталу
    deadline_month = quarter * 3 + 1
    deadline = f"{today[:4]}-{deadline_month:02d}-15"

    # Отримати тільки організації з показниками
    orgs_data = frappe.call(
        "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.get_organizations_with_indicators"
    )
    orgs = [org['value'] for org in orgs_data]

    print(f"Знайдено {len(orgs)} організацій з показниками")

    # Створити звіти
    result = frappe.call(
        "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.bulk_create_reports",
        organizations=orgs,
        period=period,
        report_type="Квартальний",
        submission_deadline=deadline
    )

    print(f"Створено {result['created']} звітів за {period}")

    # Відправити нагадування
    if result['report_ids']:
        frappe.call(
            "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.send_reminder_emails",
            report_ids=result['report_ids']
        )

# Додати в hooks.py для автоматичного виконання:
# scheduler_events = {
#     "cron": {
#         "0 9 1 1,4,7,10 *": [  # 1 число січня, квітня, липня, жовтня о 9:00
#             "path.to.create_quarterly_reports"
#         ]
#     }
# }
```

### Сценарій 2: Щоденна перевірка прострочених

```python
def check_overdue_and_send_reminders():
    """Щоденна перевірка прострочених звітів та відправка нагадувань"""
    import frappe

    # Отримати прострочені звіти
    overdue = frappe.call(
        "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.get_overdue_reports",
        days_overdue=0
    )

    if not overdue:
        print("Прострочених звітів немає")
        return

    # Групувати за кількістю днів прострочення
    critical = []  # > 7 днів
    warning = []   # 1-7 днів

    from datetime import datetime, timedelta
    today = datetime.now().date()

    for report in overdue:
        deadline = datetime.strptime(report['submission_deadline'], '%Y-%m-%d').date()
        days = (today - deadline).days

        if days > 7:
            critical.append(report['name'])
        else:
            warning.append(report['name'])

    # Відправити нагадування
    if critical:
        print(f"Критичні прострочення: {len(critical)}")
        frappe.call(
            "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.send_reminder_emails",
            report_ids=critical
        )

    if warning:
        print(f"Нещодавні прострочення: {len(warning)}")

# Додати в hooks.py:
# scheduler_events = {
#     "daily": [
#         "path.to.check_overdue_and_send_reminders"
#     ]
# }
```

### Сценарій 3: Автоматичний імпорт після прикріплення

```python
# Додати в oiperiodicreport.py в метод before_save:

def before_save(self):
    # ... існуючий код ...

    # Автоматичний імпорт якщо увімкнено
    if self.has_value_changed("filled_form_attachment") and self.filled_form_attachment:
        # Перевірити налаштування
        auto_import = frappe.db.get_single_value("Orange Inventory Settings", "auto_import_reports")

        if auto_import:
            # Імпортувати автоматично
            frappe.enqueue(
                "orange_inventory.orange_inventory.doctype.oiperiodicreport.oiperiodicreport.import_from_attachment",
                report_id=self.name,
                queue="long"
            )

            frappe.msgprint("Дані будуть імпортовані автоматично в фоновому режимі")
```

## ⚙️ Налаштування

### Автоматичні терміни подання

Система автоматично встановлює терміни подання:

**Для квартальних звітів:**
- Q1 (січень-березень) → дедлайн 15 квітня
- Q2 (квітень-червень) → дедлайн 15 липня
- Q3 (липень-вересень) → дедлайн 15 жовтня
- Q4 (жовтень-грудень) → дедлайн 15 січня наступного року

**Для річних звітів:**
- РРРР → дедлайн 31 січня наступного року

### Email шаблони

Нагадування використовують два типи email:

1. **"Очікує заповнення"** - нагадування про необхідність заповнити звіт
2. **"Заповнено"** - нагадування про необхідність імпортувати дані

Шаблони можна кастомізувати у файлі `oiperiodicreport.py`, метод `send_reminder_emails()`.

## ❓ FAQ

**Q: Чи можна створити кілька звітів для однієї організації за один період?**
A: Ні, система автоматично перевіряє унікальність і не дозволить створити дублікати.

**Q: Що робити якщо імпорт завершився з помилками?**
A: Перегляньте деталі імпорту ("Дії" → "Переглянути деталі імпорту"), виправте помилки в Excel файлі, прикріпіть знову та запустіть імпорт повторно.

**Q: Чи можна змінити період після створення звіту?**
A: Так, але тільки якщо статус "Чернетка" і дані ще не імпортовані.

**Q: Як переглянути історію змін звіту?**
A: Увімкнено track_changes, всі зміни відображаються в Timeline документа.

**Q: Чи відправляються нагадування автоматично?**
A: Ні, потрібно налаштувати scheduler events в hooks.py (див. приклади вище).

**Q: Що означає "Пропущено" при масовому створенні?**
A: Звіт для цієї організації за цей період вже існує в системі.

## 🔗 Пов'язані документи

- [IMPORT_EXCEL_GUIDE.md](cci:7://file:///home/frappe/frappe-bench/apps/orange_inventory/IMPORT_EXCEL_GUIDE.md:0:0-0:0) - Керівництво по імпорту/експорту Excel
- [COMPLETION_REPORT_GUIDE.md](cci:7://file:///home/frappe/frappe-bench/apps/orange_inventory/COMPLETION_REPORT_GUIDE.md:0:0-0:0) - Звіт про заповнення показників
- [HROMADA_SURVEY_TREND_TRACKING.md](cci:7://file:///home/frappe/frappe-bench/apps/orange_inventory/HROMADA_SURVEY_TREND_TRACKING.md:0:0-0:0) - Відстеження трендів

## 📝 Changelog

### v1.0 (2025-10-23)
- ✨ Створено DocType oiPeriodicReport
- ✨ Інтеграція з oiHromadaSurvey для імпорту/експорту
- ✨ Масове створення звітів
- ✨ Автоматична відправка нагадувань
- ✨ Відстеження прострочених звітів
- ✨ Колірне кодування статусів
- ✨ Автоматичне визначення термінів подання

---

**Підтримка:** Якщо у вас виникли питання, зверніться до команди розробки.
