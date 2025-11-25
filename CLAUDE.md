# CLAUDE.md - Orange Inventory Development Guide for AI Assistants

**Last Updated:** 2025-11-25
**Version:** 1.0

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture & Patterns](#architecture--patterns)
4. [Codebase Structure](#codebase-structure)
5. [Development Workflow](#development-workflow)
6. [Naming Conventions](#naming-conventions)
7. [Key Conventions](#key-conventions)
8. [Common Tasks](#common-tasks)
9. [Testing](#testing)
10. [Important Gotchas](#important-gotchas)
11. [Git Workflow](#git-workflow)
12. [Resources](#resources)

---

## Project Overview

**Orange Inventory** is a comprehensive IT asset lifecycle management system built on the **Frappe Framework**. It manages the complete lifecycle of IT assets from procurement to decommissioning, including tracking, maintenance, transfers, and compliance.

### Core Capabilities
- **Asset Management**: Complete tracking of IT equipment, components, and hardware
- **Inventory Operations**: Receipt orders, issue orders, transfers, and decommissioning
- **Contracts & Procurement**: Contract management with donor and counterparty tracking
- **Network Infrastructure**: Network device management with port tracking and visualization
- **Compliance**: Credential management with audit logs, training courses, and documentation
- **Reporting**: Survey data collection, periodic reports, and price monitoring
- **Localization**: Full Ukrainian language support

### Domain Model Summary
```
Organization/Location
    ↓
Procurement Flow:
    Contract → Receipt Order → Asset Creation
    ↓
Asset Lifecycle:
    On Warehouse → In Use → Transferred → Decommissioned
    ↓
Supporting Entities:
    - Components (child assets)
    - Network Ports (connectivity)
    - Movement History (audit trail)
    - Service Requests (maintenance)
```

---

## Technology Stack

### Backend
- **Framework**: Frappe Framework (~15.0.0) - ERPNext-based
- **Language**: Python 3.10+
- **Database**: MariaDB/MySQL with InnoDB (managed by Frappe)
- **ORM**: Frappe Document Model
- **Build**: Flit (Python packaging)

### Frontend
- **Framework**: Frappe's Vue.js-based frontend
- **Language**: JavaScript (ES2022)
- **Libraries**: jQuery, Chart.js, Slick Grid (Frappe standard)

### Development Tools
- **Linting**: Ruff (Python), ESLint (JavaScript)
- **Formatting**: Ruff (Python), Prettier (JS/CSS)
- **Pre-commit**: Automated code quality checks
- **Type Hints**: Full Python type annotations using `frappe.types.DF`

### Key Dependencies
- `qrcode[pil]` - QR code generation for asset labels
- `dateutil` - Date calculations for inventory tracking
- `openpyxl` - Excel file handling (Frappe-managed)

---

## Architecture & Patterns

### 1. Frappe Document-Centric Architecture

Everything in Frappe revolves around **DocTypes** (document types). Each DocType represents a business entity or transaction.

**DocType Structure:**
```
doctype_name/
├── doctype_name.json          # Metadata: fields, permissions, settings
├── doctype_name.py            # Python controller: business logic
├── doctype_name.js            # JavaScript: form interactions
├── test_doctype_name.py       # Unit tests
└── __init__.py
```

### 2. Document Lifecycle Hooks

**Common hooks in Python controllers:**

```python
class oiAsset(Document):
    def validate(self):
        """Pre-save validation - runs before every save"""
        self.update_inventory_status()

    def before_save(self):
        """Calculations before committing to database"""
        self.total = self.cost * self.quantity

    def on_update(self):
        """Post-save operations - runs after save completes"""
        self.create_network_ports_from_model()

    def on_submit(self):
        """After document is submitted (locked)"""
        pass

    def on_cancel(self):
        """When document is cancelled"""
        pass

    def on_trash(self):
        """Before document is deleted"""
        pass
```

### 3. Parent-Child Relationships

Many DocTypes have child tables (one-to-many relationships):

```python
# Parent: oiContract
# Children: oiContractItem (items in contract)

# Parent: oiAsset
# Children: oiAssetComponent, oiAssetMovementHistory
```

Child documents are stored in `DF.Table` fields and accessed as lists.

### 4. API Whitelisting Pattern

All functions exposed to frontend/API must be explicitly whitelisted:

```python
@frappe.whitelist()
def reveal_secret(credential: str, reason: str | None = None):
    """Whitelisted function callable from frontend"""
    _assert_view_permission(credential)
    # Function logic...
    return secret
```

**Security Note**: Always validate permissions in whitelisted functions!

### 5. Permission System

Two levels of permissions:

**1. DocPerm (Standard Frappe permissions)**
- Defined in JSON metadata
- Role-based: Read, Write, Create, Delete, Submit, Cancel

**2. Custom Permission Queries**
- Defined in `hooks.py`
- SQL-based filtering by organization/location
- Example: Users only see assets from their organization

```python
# In hooks.py
permission_query_conditions = {
    "oiAsset": "orange_inventory.orange_inventory.doctype.oiasset.oiasset.get_permission_query_conditions"
}
```

### 6. NestedSet Pattern (Tree Structures)

`oiHromadaSurvey` uses the NestedSet pattern for hierarchical data:
- Parent-child relationships
- Automatic lft/rgt values
- Tree navigation methods
- Score/value aggregation from children to parents

### 7. Report Architecture

Custom reports follow this pattern:

```python
def execute(filters=None):
    """
    Entry point for Frappe reports

    Returns:
        tuple: (columns, data)
    """
    columns = get_columns()  # List of column definitions
    data = get_data(filters)  # Query results
    return columns, data
```

---

## Codebase Structure

```
/home/user/orange_inventory/
├── orange_inventory/                    # Main app module
│   ├── orange_inventory/                # Core application
│   │   ├── doctype/                     # 41 custom DocTypes
│   │   │   ├── oiasset/                 # Asset management
│   │   │   ├── oicontract/              # Contracts
│   │   │   ├── oireceiptorder/          # Receiving
│   │   │   ├── oiissueorder/            # Distribution
│   │   │   ├── oihromadasurvey/         # Survey/metrics
│   │   │   ├── oicredential/            # Credentials
│   │   │   └── ...                      # 35 more doctypes
│   │   ├── report/                      # Custom reports
│   │   │   ├── contract_summary/
│   │   │   ├── price_monitoring_report/
│   │   │   └── обладнання_по_користувачу/
│   │   └── workspace/                   # UI workspaces
│   ├── config/                          # App configuration
│   ├── templates/                       # HTML templates
│   ├── public/                          # Static assets
│   │   ├── js/                          # JavaScript utilities
│   │   └── css/                         # Stylesheets
│   ├── print_utils/                     # QR code generation
│   ├── hooks.py                         # Frappe hooks & config
│   ├── api.py                           # Whitelisted API functions
│   └── network_map.py                   # Network visualization
├── pyproject.toml                       # Python config & dependencies
├── .pre-commit-config.yaml              # Pre-commit hooks
├── .eslintrc                            # JavaScript linting rules
└── [Documentation].md                   # User guides (9 files)
```

### Key DocTypes (41 Total)

**Core Entities:**
- `oiAsset` - IT assets (primary entity)
- `oiAssetComponent` - Asset components/parts
- `oiAssetType` - Asset categorization
- `oiLocation` - Physical locations
- `oiOrganization` - Organizations
- `oiEmployee` - Staff/personnel

**Transactions:**
- `oiReceiptOrder`, `oiReceiptOrderItem` - Asset receiving
- `oiIssueOrder`, `oiIssueOrderItem` - Asset distribution
- `oiDecommissioningAct`, `oiDecommissioningItem` - Asset retirement
- `oiServiceRequest`, `oiServiceRequestActivity` - Maintenance

**Procurement:**
- `oiContract`, `oiContractItem` - Contracts
- `oiCounterparty` - Vendors/partners
- `oiDonor`, `oiDonorProject` - Donors/funding

**Hardware Reference Data:**
- `oiHardwareModel`, `oiHardwareType`, `oiManufacturer`
- `oiNetworkPort`, `oiNetworkPortTemplate`
- `oiAssetStarlink` - Starlink-specific assets

**Monitoring & Compliance:**
- `oiHromadaSurvey`, `oiHromadaSurveyHistory` - Surveys with history
- `oiPeriodicReport` - Periodic reporting
- `oPriceMonitoring`, `oPriceMonitoringItem` - Price tracking
- `oiCredential`, `oiCredentialAccessLog` - Credential management
- `oiCourse`, `oiCourseSubmission` - Training courses

---

## Development Workflow

### Initial Setup

```bash
# 1. Install via bench (assumes Frappe bench is already set up)
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/rareMaxim/orange_inventory.git --branch develop
bench install-app orange_inventory

# 2. Enable pre-commit hooks (REQUIRED)
cd apps/orange_inventory
pre-commit install

# 3. Start development server (in bench directory)
cd ../..
bench start
```

### Development Cycle

1. **Make Changes**
   - Edit Python controllers, JavaScript handlers, or JSON metadata
   - Follow naming conventions (see below)

2. **Pre-commit Checks** (Automatic)
   - Ruff (Python linting + formatting)
   - ESLint (JavaScript linting)
   - Prettier (code formatting)
   - PyUpgrade (Python syntax modernization)

3. **Testing**
   ```bash
   # Run specific test
   bench execute orange_inventory.tests.test_module.function_name

   # Run all tests for a doctype
   bench run-tests --app orange_inventory --doctype oiAsset
   ```

4. **Migration/Patches**
   - If schema changes, add to `patches.txt`
   - Run migrations: `bench migrate`

5. **Commit & Push**
   - Pre-commit hooks run automatically
   - Fix any issues before committing

### Working with Frappe

**Key Frappe APIs:**

```python
import frappe

# Get a document
doc = frappe.get_doc("oiAsset", "ASSET-00001")

# Create new document
doc = frappe.get_doc({
    "doctype": "oiAsset",
    "asset_name": "Laptop",
    # ... other fields
})
doc.insert()

# Save changes
doc.save()

# Delete
doc.delete()

# Database queries
assets = frappe.get_all("oiAsset",
    filters={"status": "В експлуатації"},
    fields=["name", "asset_name", "serial_no"]
)

# Direct SQL (use sparingly)
result = frappe.db.sql("""
    SELECT name, asset_name
    FROM `taboiAsset`
    WHERE status = %s
""", ("В експлуатації",), as_dict=True)

# Error handling
frappe.throw("Error message", frappe.ValidationError)

# Logging
frappe.log_error("Error details", "Error Title")

# User/permissions
user = frappe.session.user
has_perm = frappe.has_permission("oiAsset", "write", doc.name)
```

---

## Naming Conventions

### DocType Names
- **Prefix**: `oi` (Orange Inventory) or `o` for some reports
- **Pattern**: `oi[EntityName]` (PascalCase, no underscores)
- **Examples**: `oiAsset`, `oiContract`, `oiHromadaSurvey`

### Python Files
- **DocType controller**: `[doctype_name].py` (lowercase with underscores in directory path)
- **Class name**: PascalCase matching DocType (e.g., `class oiAsset`)
- **Tests**: `test_[doctype_name].py`
- **Utilities**: `snake_case.py`

### JavaScript Files
- **Form scripts**: `[doctype_name].js`
- **List views**: `[doctype_name]_list.js`
- **Utilities**: `snake_case.js`

### Field Names (in DocTypes)
- **Pattern**: `snake_case`
- **Examples**: `asset_name`, `serial_no`, `inventory_status`
- **Labels**: Ukrainian (e.g., "Найменування", "Серійний номер")
- **Sections**: `[name]_section` or `[name]_sb`
- **Column breaks**: `column_break_[id]`

### Database Tables
- **Pattern**: `tab[DocTypeName]` (Frappe auto-generates)
- **Example**: `taboiAsset`, `taboiContract`

---

## Key Conventions

### 1. Type Hints (REQUIRED)

All DocType controllers include auto-generated type hints:

```python
class oiAsset(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        asset_name: DF.SmallText
        serial_no: DF.Data | None
        cost: DF.Currency
        location: DF.Link | None
        components: DF.Table[oiAssetComponent]
        status: DF.Literal["На складі", "В експлуатації", ...]
    # end: auto-generated types
```

**Do NOT manually edit the auto-generated section!** Frappe regenerates this from JSON metadata.

### 2. Code Style (Enforced by Ruff)

```python
# Line length: 110 characters
# Indentation: TABS (not spaces)
# Quotes: Double quotes
# Python version: 3.10+ (use modern syntax)

# Good
def calculate_total(items: list[dict]) -> float:
	"""Calculate total with modern type hints"""
	return sum(item.get("amount") or 0 for item in items)

# Bad
def calculate_total(items):  # Missing type hints
    return sum([item.get('amount') or 0 for item in items])  # Single quotes, list comprehension
```

### 3. Error Handling

```python
# Use frappe.throw() for user-facing errors
if not self.serial_no:
    frappe.throw("Серійний номер обов'язковий", frappe.ValidationError)

# Use frappe.log_error() for unexpected errors
try:
    process_data()
except Exception as e:
    frappe.log_error("Деталі помилки", "Назва помилки")
    frappe.throw("Не вдалося обробити дані")
```

### 4. Ukrainian Localization

- **Field labels**: Always in Ukrainian
- **Error messages**: In Ukrainian
- **Status values**: In Ukrainian (e.g., "На складі", "Списано")
- **UI text**: In Ukrainian
- **Code comments**: Can be in English or Ukrainian
- **Documentation**: Mixed (technical docs in English, user guides in Ukrainian)

### 5. Permission Checks

Always check permissions in whitelisted functions:

```python
@frappe.whitelist()
def reveal_secret(credential: str, reason: str | None = None):
    # Check permission FIRST
    if not frappe.has_permission("oiCredential", "read", credential):
        frappe.throw("Немає доступу", frappe.PermissionError)

    # Then perform operation
    secret = get_decrypted_password("oiCredential", credential, "secret")
    return secret
```

### 6. Child Table Handling

```python
# Access child table
for component in self.components:
    print(component.component_name)

# Add child row
self.append("components", {
    "component_name": "RAM Module",
    "quantity": 2
})

# Update child
for comp in self.components:
    if comp.component_name == "RAM":
        comp.quantity = 4
        break
```

### 7. Date Handling

```python
from frappe.utils import getdate, now, today, add_days, date_diff
from dateutil.relativedelta import relativedelta

# Get dates
today_date = getdate(today())
now_datetime = now()

# Calculate differences
months_diff = relativedelta(current_date, past_date).months

# Add/subtract
future_date = add_days(today(), 30)
```

---

## Common Tasks

### 1. Creating a New DocType

```bash
# In bench directory
bench new-doctype --app orange_inventory

# Follow prompts:
# - DocType name: oiNewEntity
# - Module: Orange Inventory
# - Is Submittable: No (usually)
# - Is Child Table: No (usually)
```

Then:
1. Edit JSON in desk (Frappe UI)
2. Add Python logic in `oiNewEntity.py`
3. Add JavaScript handlers in `oiNewEntity.js` (if needed)
4. Write tests in `test_oiNewEntity.py`

### 2. Adding a New Field to Existing DocType

**Option A: Via Desk (Recommended)**
1. Go to DocType list in Frappe UI
2. Open the DocType
3. Add field via form
4. Save and reload

**Option B: Edit JSON directly** (not recommended for beginners)
1. Edit `[doctype].json`
2. Add field definition
3. Run `bench migrate`
4. Update type hints: `bench generate-type-annotations --app orange_inventory`

### 3. Creating a Custom Report

```bash
# Create report directory
mkdir -p orange_inventory/orange_inventory/report/my_report

# Create files:
# 1. my_report.json - Report metadata
# 2. my_report.py - Report logic
# 3. my_report.js - Frontend customization (optional)
```

**my_report.py:**
```python
def execute(filters=None):
    columns = [
        {
            "fieldname": "asset_name",
            "label": "Asset Name",
            "fieldtype": "Data",
            "width": 200
        },
        # ... more columns
    ]

    data = frappe.db.sql("""
        SELECT asset_name, serial_no, location
        FROM `taboiAsset`
        WHERE status = %(status)s
    """, filters, as_dict=1)

    return columns, data
```

### 4. Adding a Whitelisted API Function

In `orange_inventory/api.py` or doctype controller:

```python
@frappe.whitelist()
def my_custom_function(param1: str, param2: int = 0):
    """
    Custom function callable from frontend

    Args:
        param1: Description
        param2: Description (optional)

    Returns:
        dict: Result data
    """
    # Check permissions
    if not frappe.has_permission("oiAsset", "read"):
        frappe.throw("Access denied", frappe.PermissionError)

    # Your logic here
    result = do_something(param1, param2)

    return result
```

**Call from JavaScript:**
```javascript
frappe.call({
    method: "orange_inventory.api.my_custom_function",
    args: {
        param1: "value",
        param2: 42
    },
    callback: function(r) {
        console.log(r.message);  // Result
    }
});
```

### 5. Adding Custom Validation

In DocType controller:

```python
def validate(self):
    """Runs before every save"""
    self.validate_serial_number()
    self.calculate_totals()
    self.check_duplicate_assets()

def validate_serial_number(self):
    if self.serial_no:
        # Check for duplicates
        existing = frappe.db.exists("oiAsset", {
            "serial_no": self.serial_no,
            "name": ["!=", self.name]
        })
        if existing:
            frappe.throw(f"Серійний номер {self.serial_no} вже використовується")
```

### 6. Working with Child Tables

```python
def validate_components(self):
    """Validate child table: components"""
    if not self.components:
        return

    total_qty = 0
    seen_names = set()

    for comp in self.components:
        # Check duplicates
        if comp.component_name in seen_names:
            frappe.throw(f"Дублікат компонента: {comp.component_name}")
        seen_names.add(comp.component_name)

        # Sum quantities
        total_qty += comp.quantity or 0

    self.total_components = total_qty
```

### 7. Creating Network Ports Dynamically

See `oiAsset.create_network_ports_from_model()` for example:

```python
def create_network_ports_from_model(self):
    if not self.hardware_model or not self.is_network_device:
        return

    # Get port templates from hardware model
    model = frappe.get_doc("oiHardwareModel", self.hardware_model)
    if not model.network_port_templates:
        return

    # Create ports from templates
    for template in model.network_port_templates:
        # Check if port already exists
        if not frappe.db.exists("oiNetworkPort", {
            "asset": self.name,
            "port_name": template.port_name
        }):
            port = frappe.get_doc({
                "doctype": "oiNetworkPort",
                "asset": self.name,
                "port_name": template.port_name,
                "port_type": template.port_type
            })
            port.insert(ignore_permissions=True)
```

---

## Testing

### Test Structure

```python
# test_oiasset.py
import frappe
from frappe.tests.utils import FrappeTestCase

class TestoiAsset(FrappeTestCase):
    def setUp(self):
        """Runs before each test"""
        # Create test data
        self.test_asset = frappe.get_doc({
            "doctype": "oiAsset",
            "asset_name": "Test Laptop",
            "serial_no": "TEST001"
        }).insert()

    def tearDown(self):
        """Runs after each test"""
        # Clean up
        self.test_asset.delete()

    def test_inventory_status_calculation(self):
        """Test inventory status updates correctly"""
        self.test_asset.inventory_date = "2023-01-01"
        self.test_asset.save()
        self.assertEqual(
            self.test_asset.inventory_status,
            "⚠️ Інвентаризація не проводилась більше 12 міс."
        )
```

### Running Tests

```bash
# All tests for app
bench run-tests --app orange_inventory

# Specific doctype
bench run-tests --app orange_inventory --doctype oiAsset

# Specific test
bench execute orange_inventory.orange_inventory.doctype.oiasset.test_oiasset.test_inventory_status
```

---

## Important Gotchas

### 1. Tab Indentation (Not Spaces!)

This project uses **TABS** for indentation. Pre-commit will fail with spaces.

```python
# CORRECT
def my_function():
→	return True  # Tab character

# WRONG
def my_function():
    return True  # Spaces - will fail pre-commit
```

### 2. Auto-Generated Type Hints

**NEVER manually edit the auto-generated types section!**

```python
class oiAsset(Document):
    # begin: auto-generated types
    # DO NOT EDIT THIS SECTION
    # end: auto-generated types

    # Your code goes here
    def validate(self):
        pass
```

To regenerate: `bench generate-type-annotations --app orange_inventory`

### 3. Ukrainian Field Values

Status fields and dropdowns use Ukrainian values:

```python
# CORRECT
if self.status == "В експлуатації":
    pass

# WRONG
if self.status == "In Use":  # This won't match!
    pass
```

### 4. Permission Queries

Custom permission queries in `hooks.py` can restrict data visibility. If data seems "missing", check permission functions.

### 5. Child Table Modifications

When modifying child tables, you must save the parent:

```python
# CORRECT
asset = frappe.get_doc("oiAsset", "ASSET-00001")
asset.append("components", {"component_name": "RAM"})
asset.save()  # Must save parent

# WRONG
asset = frappe.get_doc("oiAsset", "ASSET-00001")
asset.components[0].quantity = 5
# No save() - changes lost!
```

### 6. Frappe Caching

Frappe caches heavily. Clear cache when things don't update:

```bash
bench clear-cache
bench clear-website-cache
```

### 7. Database Table Names

Always use `tab` prefix in SQL queries:

```sql
-- CORRECT
SELECT * FROM `taboiAsset`

-- WRONG
SELECT * FROM oiAsset  -- Table doesn't exist!
```

### 8. Date Formats

Frappe expects `YYYY-MM-DD` format. Always use `getdate()`:

```python
from frappe.utils import getdate

# CORRECT
date = getdate("2025-01-15")
date = getdate(some_date_field)

# WRONG
date = "15/01/2025"  # Will fail
```

---

## Git Workflow

### Branch Structure

- **main/master**: Production-ready code
- **develop**: Development branch
- **feature/[name]**: Feature branches
- **claude/[session-id]**: AI assistant branches (auto-generated)

### Commit Guidelines

```bash
# Good commit messages
git commit -m "feat: Add parent asset and components functionality"
git commit -m "fix: Correct inventory status calculation for edge cases"
git commit -m "docs: Update HROMADA_SURVEY_TREND_TRACKING guide"

# Commit types: feat, fix, docs, refactor, test, chore
```

### Pre-commit Checks

Before every commit:
1. Ruff linting + formatting (Python)
2. ESLint (JavaScript)
3. Prettier (formatting)
4. PyUpgrade (modernize Python syntax)

**If pre-commit fails:**
1. Review the errors
2. Fix issues (or let auto-fix handle it)
3. Stage fixed files: `git add .`
4. Commit again

### Pushing Changes

```bash
# Development branch
git push -u origin develop

# Feature branch
git push -u origin feature/my-feature

# AI assistant branch (always use -u)
git push -u origin claude/[session-id]
```

---

## Resources

### Documentation Files (in Repository)

1. **IMPORT_QUICK_START.md** - Excel import quick start
2. **IMPORT_EXCEL_GUIDE.md** - Detailed Excel import guide
3. **PERIODIC_REPORTS_GUIDE.md** - Periodic reporting features
4. **PERIODIC_REPORTS_QUICK_START.md** - Quick start for reports
5. **HROMADA_SURVEY_TREND_TRACKING.md** - Survey/metrics system
6. **COMPLETION_REPORT_GUIDE.md** - Report completion workflow
7. **ISSUE_ORDER_PRINT_GUIDE.md** - Asset distribution printing
8. **README_IMPORT.md** - Import system technical docs

### Frappe Documentation

- **Frappe Framework**: https://frappeframework.com/docs
- **ERPNext**: https://docs.erpnext.com/
- **Frappe School**: https://frappe.school/

### Key Frappe Concepts

- **DocTypes**: Document types (database tables + logic)
- **DocFields**: Fields in a DocType
- **Controller**: Python class for DocType logic
- **Hooks**: Event handlers defined in `hooks.py`
- **Whitelisting**: Exposing functions to API/frontend
- **Permissions**: Role-based access control
- **Fixtures**: Reference data for testing/deployment

### Development Commands

```bash
# Start development server
bench start

# Create new app
bench new-app app_name

# Install app
bench install-app app_name

# Create DocType
bench new-doctype --app app_name

# Migrate database
bench migrate

# Clear cache
bench clear-cache

# Generate type annotations
bench generate-type-annotations --app orange_inventory

# Run tests
bench run-tests --app orange_inventory

# Console (Python REPL)
bench console

# Update bench apps
bench update
```

### Code Quality Commands

```bash
# Run ruff manually
ruff check .
ruff format .

# Run ESLint
eslint .

# Run pre-commit on all files
pre-commit run --all-files
```

---

## Quick Reference: Key Files

| File | Purpose |
|------|---------|
| `hooks.py` | App configuration, hooks, permissions |
| `api.py` | Whitelisted API functions |
| `network_map.py` | Network visualization logic |
| `pyproject.toml` | Python dependencies, Ruff config |
| `.eslintrc` | JavaScript linting rules |
| `.pre-commit-config.yaml` | Pre-commit hook configuration |
| `modules.txt` | Module name definition |
| `patches.txt` | Database migration patches |

---

## Quick Reference: Common Patterns

### Get/Create/Update Document

```python
# Get existing
doc = frappe.get_doc("oiAsset", "ASSET-00001")

# Create new
doc = frappe.new_doc("oiAsset")
doc.asset_name = "New Asset"
doc.insert()

# Update
doc.cost = 1000
doc.save()

# Delete
doc.delete()
```

### Query Database

```python
# Get all with filters
assets = frappe.get_all("oiAsset",
    filters={"status": "В експлуатації"},
    fields=["name", "asset_name", "cost"],
    order_by="creation desc",
    limit=10
)

# Get single value
count = frappe.db.count("oiAsset", {"status": "На складі"})

# Get single field
name = frappe.db.get_value("oiAsset", "ASSET-00001", "asset_name")

# Raw SQL
results = frappe.db.sql("""
    SELECT name, cost FROM `taboiAsset`
    WHERE cost > %s
""", (1000,), as_dict=True)
```

### Frontend JavaScript

```javascript
frappe.ui.form.on("oiAsset", {
    refresh: function(frm) {
        // Runs when form loads/refreshes
        if (frm.doc.status === "На складі") {
            frm.add_custom_button("Issue Asset", function() {
                // Button action
            });
        }
    },

    cost: function(frm) {
        // Runs when 'cost' field changes
        frm.set_value("total", frm.doc.cost * frm.doc.quantity);
    }
});
```

---

## Summary for AI Assistants

When working with Orange Inventory:

1. **Always use TABS** (not spaces) for indentation
2. **Never edit auto-generated type hints** in Python files
3. **Check Ukrainian field values** for statuses and dropdowns
4. **Use `frappe.get_doc()`** instead of direct SQL when possible
5. **Whitelist all API functions** with `@frappe.whitelist()`
6. **Check permissions** in whitelisted functions
7. **Use `frappe.throw()`** for user-facing errors
8. **Follow naming conventions**: `oi` prefix, snake_case fields
9. **Run pre-commit checks** before committing
10. **Reference line numbers** when discussing code: `file:line`

This is a **mature, production-grade** codebase with:
- 41 DocTypes
- ~6,000 lines of Python
- Full Ukrainian localization
- Comprehensive testing
- Enforced code quality
- Active development

Treat it with care and follow established patterns!

---

**End of CLAUDE.md**
