# Шаблон друку Видаткового ордеру - Керівництво

## 📋 Огляд

Професійний шаблон друку для **oiIssueOrder** (Видатковий ордер) з повною підтримкою української мови, автоматичними розрахунками та форматуванням для офіційних документів.

## 🎨 Особливості шаблону

### ✨ Функціональність:

1. **Професійний дизайн**
   - Чіткий заголовок з номером документа
   - Структуровані секції
   - Таблиця з автоматичними розрахунками
   - Місце для підписів та печатки

2. **Автоматичні розрахунки**
   - Підсумок кількості по всіх позиціях
   - Загальна вартість
   - Сума прописом (українською)

3. **Повна інформація**
   - Дата видачі
   - Рішення-підстава
   - Організація звідки/куди
   - МВО (якщо вказано)
   - Детальний перелік активів

4. **Готовність до друку**
   - Оптимізовано для A4
   - Відступи 10mm
   - Підтримка сторінкування
   - Адаптивне форматування

## 📥 Встановлення

### Автоматичне встановлення (при migrate):

```bash
cd /home/frappe/frappe-bench
bench migrate
```

Система автоматично знайде та зареєструє новий Print Format.

### Ручне встановлення:

1. **Перейдіть в Print Format List:**
   ```
   Desk → Print Format
   ```

2. **Створіть новий Print Format:**
   - DocType: `oiIssueOrder`
   - Print Format Name: `Issue Order Print`
   - Print Format Type: `Jinja`
   - Custom Format: ✓ (Yes)

3. **Скопіюйте HTML код:**
   - Відкрийте файл `issue_order_print.html`
   - Скопіюйте весь вміст
   - Вставте в поле "HTML"
   - Збережіть

## 🖨️ Використання

### Друк через інтерфейс:

1. **Відкрийте Видатковий ордер**
   ```
   Orange Inventory → Issue Order → [Виберіть документ]
   ```

2. **Натисніть кнопку "Print"**
   - З'явиться діалог вибору формату
   - Виберіть **"Issue Order Print"**
   - Натисніть "Print"

3. **Параметри друку:**
   - Мова: Українська
   - Формат: A4
   - Орієнтація: Портрет

### Друк через API:

```python
import frappe

# Отримати HTML для друку
html = frappe.get_print(
    doctype="oiIssueOrder",
    name="ВО-2025-00001",
    print_format="Issue Order Print",
    as_pdf=False
)

# Або отримати PDF
pdf = frappe.get_print(
    doctype="oiIssueOrder",
    name="ВО-2025-00001",
    print_format="Issue Order Print",
    as_pdf=True
)
```

### Масовий друк:

```python
# Друк кількох ордерів
import frappe

orders = frappe.get_all(
    "oiIssueOrder",
    filters={"issue_date": [">=", "2025-10-01"]},
    pluck="name"
)

for order in orders:
    pdf = frappe.get_print(
        doctype="oiIssueOrder",
        name=order,
        print_format="Issue Order Print",
        as_pdf=True
    )

    # Зберегти PDF
    frappe.attach_print(
        doctype="oiIssueOrder",
        name=order,
        file_name=f"{order}.pdf",
        print_format="Issue Order Print"
    )
```

## 📐 Структура шаблону

### 1. Заголовок
```
ВИДАТКОВИЙ ОРДЕР
№ ВО-2025-00001
[Рішення-підстава: БД-2025-001]
```

### 2. Основна інформація
- Дата видачі

### 3. Сторони
- Звідки (Організація) - назва з oiOrganization
- Куди (Організація) - назва з oiOrganization
- Кому (МВО) - ПІБ з oiEmployee (якщо вказано)

### 4. Таблиця активів

| № | Найменування | Серійний номер | Кількість | Вартість | Сума |
|---|--------------|----------------|-----------|----------|------|
| 1 | Starlink     | SN123456       | 1.00      | 15000.00 | 15000.00 |
| **РАЗОМ:**   |                |                | **1.00**  |          | **15000.00** |

**Загальна вартість:** 15000.00 грн
*(П'ятнадцять тисяч гривень 00 копійок)*

### 5. Підписи
```
Видав:                    Отримав:
___________________       ___________________
(підпис, П.І.Б.)         (підпис, П.І.Б.)
```

### 6. Місце для печатки
```
                          М.П.
```

## 🎨 Кастомізація

### Зміна кольорів:

Відредагуйте CSS змінні в `<style>`:

```css
.header h1 {
    color: #2c3e50;  /* Колір заголовка */
}

.section-title {
    border-bottom: 2px solid #3498db;  /* Колір підкреслення */
}

.items-table thead {
    background-color: #34495e;  /* Колір шапки таблиці */
}
```

### Додавання логотипу:

Додайте в секцію `.header`:

```html
<div class="header">
    <img src="/files/logo.png" style="height: 60px; margin-bottom: 10px;" />
    <h1>ВИДАТКОВИЙ ОРДЕР</h1>
    ...
</div>
```

### Додавання QR коду:

Додайте в шаблон:

```html
<div class="qr-code">
    <img src="/api/method/frappe.utils.print_format.get_qr_code?data={{ doc.name }}"
         width="100" height="100" />
</div>
```

### Зміна формату дати:

```html
<!-- Замість -->
{{ frappe.utils.formatdate(doc.issue_date, "dd.MM.yyyy") }}

<!-- Використайте -->
{{ frappe.utils.formatdate(doc.issue_date, "dd MMMM yyyy") }}  <!-- 23 жовтня 2025 -->
```

### Додавання додаткових полів:

```html
<div class="info-row">
    <div class="info-label">Ваше поле:</div>
    <div class="info-value">{{ doc.custom_field }}</div>
</div>
```

## 💡 Корисні функції Jinja

### 1. Отримання даних з пов'язаних DocType:

```jinja
{# Назва організації #}
{{ frappe.db.get_value("oiOrganization", doc.from_organization, "organization_name") }}

{# Кілька полів #}
{% set org_data = frappe.db.get_value("oiOrganization", doc.from_organization, ["organization_name", "tax_code", "address"], as_dict=True) %}
{{ org_data.organization_name }} (ЄДРПОУ: {{ org_data.tax_code }})
```

### 2. Умови:

```jinja
{% if doc.to_employee %}
    <div>МВО: {{ doc.to_employee }}</div>
{% else %}
    <div>МВО не вказано</div>
{% endif %}
```

### 3. Цикли:

```jinja
{% for item in doc.items %}
    <tr>
        <td>{{ loop.index }}</td>
        <td>{{ item.asset }}</td>
    </tr>
{% endfor %}
```

### 4. Форматування чисел:

```jinja
{# 2 знаки після коми #}
{{ "%.2f"|format(item.qty) }}

{# З розділювачем тисяч #}
{{ "{:,.2f}".format(item.value) }}

{# Сума прописом #}
{{ frappe.utils.money_in_words(total_value, "UAH") }}
```

### 5. Форматування дат:

```jinja
{# dd.MM.yyyy #}
{{ frappe.utils.formatdate(doc.issue_date, "dd.MM.yyyy") }}

{# dd MMMM yyyy (українською) #}
{{ frappe.utils.formatdate(doc.issue_date, "dd MMMM yyyy") }}

{# Поточна дата та час #}
{{ frappe.utils.now_datetime().strftime("%d.%m.%Y %H:%M") }}
```

## 🐛 Відладка

### Перевірка змінних:

```html
<!-- Виведення всіх полів документа -->
<pre>{{ doc.as_dict() }}</pre>

<!-- Перевірка конкретного значення -->
<div>Debug: {{ doc.from_organization }}</div>
```

### Перевірка циклів:

```jinja
{% for item in doc.items %}
    <div>Item {{ loop.index }}: {{ item.as_dict() }}</div>
{% endfor %}
```

### Помилки при друку:

1. **"Template not found"**
   - Перевірте що Print Format збережено
   - Виконайте `bench clear-cache`

2. **"Field not found"**
   - Перевірте назву поля в DocType
   - Використайте `{{ doc.as_dict() }}` для відладки

3. **Некоректне форматування**
   - Перевірте CSS
   - Використайте інструменти розробника браузера

## 📱 Адаптивність

Шаблон оптимізовано для:
- 🖨️ Друку на A4
- 📄 PDF генерації
- 👁️ Перегляду в браузері

## 🔧 Налаштування за замовчуванням

Щоб зробити цей шаблон основним:

1. **Через інтерфейс:**
   ```
   Settings → Print Settings → Default Print Format for oiIssueOrder
   → Виберіть "Issue Order Print"
   ```

2. **Через код:**
   ```python
   frappe.db.set_value("Property Setter",
       {"doc_type": "oiIssueOrder", "property": "default_print_format"},
       "value", "Issue Order Print")
   ```

## 📝 Приклади використання

### Друк з email:

```python
frappe.sendmail(
    recipients=["recipient@example.com"],
    subject=f"Видатковий ордер {doc.name}",
    message="Доброго дня,\n\nВ додатку Видатковий ордер.",
    attachments=[{
        "fname": f"{doc.name}.pdf",
        "fcontent": frappe.get_print(
            "oiIssueOrder",
            doc.name,
            "Issue Order Print",
            as_pdf=True
        )
    }]
)
```

### Автоматичний друк при Submit:

Додайте в `oiissueorder.py`:

```python
def on_submit(self):
    # Автоматично створити PDF
    pdf = frappe.get_print(
        "oiIssueOrder",
        self.name,
        "Issue Order Print",
        as_pdf=True
    )

    # Прикріпити до документа
    frappe.attach_print(
        "oiIssueOrder",
        self.name,
        file_name=f"{self.name}.pdf",
        print_format="Issue Order Print"
    )
```

## 🔗 Пов'язані документи

- [Orange Inventory Documentation](../README.md)
- [Frappe Print Format Guide](https://frappeframework.com/docs/user/en/desk/printing)

## 📝 Changelog

### v1.0 (2025-10-23)
- ✨ Створено базовий шаблон
- ✨ Додано автоматичні розрахунки
- ✨ Підтримка української мови
- ✨ Професійний дизайн для офіційних документів
- ✨ Місце для підписів та печатки

---

**Автор:** Orange Inventory Team
**Ліцензія:** MIT
