# 📥 Функціонал Імпорту Даних - oiHromadaSurvey

## Огляд

Реалізовано повний функціонал для завантаження та автоматичного оновлення показників з Excel файлів.

## 🎯 Основні Можливості

### 1. Експорт Шаблону
- Генерація Excel файлів для конкретної організації
- Автоматичне заповнення поточних значень
- Захист від редагування службових колонок
- Валідація даних через Data Validation

### 2. Імпорт Даних
- Автоматичний парсинг Excel файлів
- Порівняння старих та нових значень
- Оновлення тільки змінених записів
- Створення історії для відстеження змін

### 3. Відстеження Історії
- Автоматичне збереження всіх змін
- Прив'язка до періоду (квартал/рік)
- Логування користувача та часу
- Візуалізація на графіках

## 📦 Файли

```
orange_inventory/
├── orange_inventory/doctype/oihromadasurvey/
│   ├── oihromadasurvey.py          # Backend: імпорт/експорт логіка
│   ├── oihromadasurvey.js          # Frontend: UI кнопки та діалоги
│   └── oihromadasurvey.json        # DocType конфігурація
├── HROMADA_SURVEY_TREND_TRACKING.md  # Повна документація
├── IMPORT_EXCEL_GUIDE.md            # Інструкція користувача
├── test_import_example.py           # Приклад тестування
└── README_IMPORT.md                 # Цей файл
```

## 🚀 Швидкий Старт

### Для Користувачів

1. **Експорт шаблону**
   ```
   UI: Відкрити список показників (ListView) → Меню "..." → "Export Excel Template..."
   ```

2. **Редагувати колонку G**
   ```
   Відкрити Excel → Змінити значення в колонці G → Зберегти
   ```

3. **Імпортувати назад**
   ```
   UI: Відкрити список показників (ListView) → Меню "..." → "Імпорт даних з Excel" → Завантажити файл → "Імпортувати"
   ```

**Важливо:** Всі операції виконуються через ListView показників, а не через окремі документи!

### Для Розробників

```python
# Експорт
from orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey import export_org_template

result = export_org_template(org="ORG-0001", period="2025-Q4")
file_url = result["file_url"]

# Імпорт
from orange_inventory.orange_inventory.doctype.oihromadasurvey.oihromadasurvey import import_from_excel

result = import_from_excel(file_url=file_url, org="ORG-0001")
print(f"Updated: {result['updated']}, Skipped: {result['skipped']}")
```

## 🧪 Тестування

```bash
# Запустити тестовий workflow
bench execute orange_inventory.test_import_example.test_import_workflow

# Або через frappe console
bench console
>>> from orange_inventory.test_import_example import test_import_workflow
>>> test_import_workflow()
```

## 📊 API Методи

### `export_org_template(org, period)`

**Призначення:** Генерує Excel шаблон для організації

**Параметри:**
- `org` (str): ID організації (обов'язковий)
- `period` (str): Період, наприклад "2025-Q4" (опціонально)

**Повертає:**
```python
{
    "file_url": "/private/files/Template_Org_2025-Q4.xlsx"
}
```

### `import_from_excel(file_url, org)`

**Призначення:** Імпортує дані з Excel файлу

**Параметри:**
- `file_url` (str): URL завантаженого файлу (обов'язковий)
- `org` (str): ID організації для валідації (опціонально)

**Повертає:**
```python
{
    "status": "success" | "error",
    "updated": 15,
    "skipped": 3,
    "errors": [],
    "details": [
        {
            "id": "показник-001",
            "title": "Назва",
            "type": "Кількісні дані",
            "old_value": 10,
            "new_value": 15
        }
    ]
}
```

### `get_value_trend_data(survey_id, limit)`

**Призначення:** Отримує дані для графіка тенденцій

**Параметри:**
- `survey_id` (str): ID показника (обов'язковий)
- `limit` (int): Кількість записів (за замовчуванням 50)

**Повертає:**
```python
{
    "labels": ["2025-Q1", "2025-Q2"],
    "values": [10, 15],
    "type": "Кількісні дані",
    "title": "Назва показника",
    "frequency": "Раз на квартал"
}
```

## 🔒 Безпека

- ✅ Валідація типів даних (int/bool)
- ✅ Автоматичний пропуск `only_admin` полів
- ✅ Перевірка належності до організації
- ✅ Транзакційне збереження (rollback при помилках)
- ✅ Логування всіх змін у History

## ⚠️ Обмеження

- Працює тільки з файлами, згенерованими через `export_org_template`
- Оновлює тільки існуючі показники (не створює нові)
- Не працює з груповими записами (`type="Група"`)
- Максимальний розмір файлу: згідно налаштувань Frappe

## 🐛 Troubleshooting

### Імпорт не працює

**Проблема:** Помилка "Файл не знайдено"
**Рішення:** Переконайтеся що файл завантажено в систему Frappe

**Проблема:** "Некоректне якісне значення"
**Рішення:** Використовуйте `Так` або `Ні` (з великої літери, українською)

**Проблема:** Багато пропущених записів
**Рішення:** Перевірте чи змінилися значення в колонці G

### Історія не створюється

**Проблема:** Зміни не відображаються в історії
**Рішення:**
1. Перевірте чи показник не є групою
2. Очистіть кеш: `bench clear-cache`
3. Перезавантажте сторінку

## 📚 Документація

- [HROMADA_SURVEY_TREND_TRACKING.md](./HROMADA_SURVEY_TREND_TRACKING.md) - Повна документація
- [IMPORT_EXCEL_GUIDE.md](./IMPORT_EXCEL_GUIDE.md) - Інструкція користувача

## 📝 Changelog

### v1.1.0 (2025-10-21)
- ✨ Додано функціонал імпорту даних з Excel
- ✨ Автоматичне створення історії при імпорті
- 🎨 UI діалог з детальним звітом
- 🔒 Валідація даних та безпека

### v1.0.0 (2025-10-21)
- ✨ Базовий функціонал відстеження історії
- 📊 Графіки тенденцій
- 📥 Експорт шаблонів

## 👥 Автори

Maxim Sysoev and contributors

## 📄 Ліцензія

Дивіться LICENSE файл

---

**Оновлено:** 21.10.2025
