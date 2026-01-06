# Odoo 19 Development Notes

This document captures key differences and patterns for Odoo 19 development, based on analysis of the enterprise source code.

---

## View Changes

### 1. List View (formerly Tree View)
- **Old (Odoo ≤17):** `<tree>` tag
- **New (Odoo 19):** `<list>` tag

```xml
<!-- OLD -->
<tree string="My List">
    <field name="name"/>
</tree>

<!-- NEW (Odoo 19) -->
<list string="My List">
    <field name="name"/>
</list>
```

### 2. View Mode in Actions
- **Old:** `tree,form,pivot,graph`
- **New:** `list,form,pivot,graph`

```xml
<!-- OLD -->
<field name="view_mode">tree,form,pivot,graph</field>

<!-- NEW (Odoo 19) -->
<field name="view_mode">list,form,pivot,graph</field>
```

### 3. Column Visibility in List Views
- **Old:** `invisible="1"`
- **New:** `column_invisible="True"`

```xml
<!-- OLD -->
<field name="currency_id" invisible="1"/>

<!-- NEW (Odoo 19) -->
<field name="currency_id" column_invisible="True"/>
```

### 4. Search View Group By
- The `<group>` tag in search views should NOT have `expand` or `string` attributes for Group By sections
- Keep it simple:

```xml
<!-- OLD (may cause errors in Odoo 19) -->
<group expand="0" string="Group By">
    <filter string="Partner" name="group_by_partner" context="{'group_by': 'partner_id'}"/>
</group>

<!-- NEW (Odoo 19) - simpler format -->
<group>
    <filter string="Partner" name="group_by_partner" context="{'group_by': 'partner_id'}"/>
</group>
```

### 5. Date Filters in Search Views
Use the `date` attribute for automatic date range filters:

```xml
<filter name="filter_date" date="date" default_period="month"/>
<filter string="Invoice Date" name="filter_invoice_date" date="invoice_date"/>
```

---

## Model Changes

### 1. SQL View Reports (_auto = False)
- **Old:** Use `init()` method with `CREATE OR REPLACE VIEW`
- **New (Odoo 19):** Use `_table_query` property

```python
# OLD (Odoo ≤17)
class MyReport(models.Model):
    _name = 'my.report'
    _auto = False
    
    def init(self):
        self._cr.execute("""
            CREATE OR REPLACE VIEW my_report AS (
                SELECT ...
            )
        """)

# NEW (Odoo 19)
class MyReport(models.Model):
    _name = 'my.report'
    _auto = False
    
    @property
    def _table_query(self):
        return """
            SELECT ...
        """
```

### 2. Field Attributes
- `readonly=True` is still valid for report fields
- Use `aggregator` attribute for aggregation in list views:

```python
price_unit = fields.Float(string="Unit Price", aggregator='avg', readonly=True)
order_reference = fields.Reference(
    string='Order',
    selection=[('sale.order', 'Sales Order')],
    aggregator="count_distinct",
```

### 3. Removed/Changed Fields in Odoo 19

#### account.account
- **`deprecated` field REMOVED** - Use `active` field instead
  ```python
  # OLD (Odoo ≤17) - WILL FAIL in Odoo 19
  account_id = fields.Many2one(
      'account.account',
      domain="[('deprecated', '=', False)]"
  )
  
  # NEW (Odoo 19) - deprecated field doesn't exist
  # Option 1: No filter needed (inactive accounts hidden by default)
  account_id = fields.Many2one('account.account')
  
  # Option 2: Explicitly filter by active if needed
  account_id = fields.Many2one(
      'account.account',
      domain="[('active', '=', True)]"
  )
  ```

### 4. Computed Fields - Stored vs Non-Stored (IMPORTANT)

In Odoo 19, computed fields with **different `store` values** must use **separate compute methods**.

```python
# BAD - Will cause UserWarning in Odoo 19
# "inconsistent 'store' for computed fields"
field_a = fields.One2many(..., compute='_compute_all')  # Not stored
field_b = fields.Float(..., compute='_compute_all', store=True)  # Stored

def _compute_all(self):  # Same method for both = WARNING
    ...

# GOOD - Separate compute methods for stored vs non-stored
field_a = fields.One2many(..., compute='_compute_field_a')  # Not stored
field_b = fields.Float(..., compute='_compute_stored_fields', store=True)  # Stored

def _compute_field_a(self):
    """Non-stored computed field"""
    ...

def _compute_stored_fields(self):
    """Stored computed fields"""
    ...
```

**Also applies to `compute_sudo`** - fields with different `compute_sudo` values need separate methods.

)
```

---

## Domain and Filter Syntax

### 1. Comparison Operators in XML
When using comparison operators in XML domains, use XML entities:
- `>` → `&gt;`
- `<` → `&lt;`
- `>=` → `&gt;=`
- `<=` → `&lt;=`

```xml
<filter string="Large Values" name="large" domain="[('amount', '&gt;', 1000)]"/>
```

### 2. Date Domains with Relative Dates
Use the `date` attribute instead of complex `relativedelta` expressions:

```xml
<!-- Preferred approach - automatic date picker -->
<filter name="filter_date" date="invoice_date"/>

<!-- For relative dates (e.g., last 365 days) -->
<filter name="filter_order_date" string="Last 365 Days" domain="[('date', '&gt;=', '-365d')]"/>
```

---

## Action Window Configuration

### 1. Search View Reference
Explicitly reference the search view in actions:

```xml
<record id="action_my_report" model="ir.actions.act_window">
    <field name="name">My Report</field>
    <field name="res_model">my.report</field>
    <field name="view_mode">list,pivot,graph</field>
    <field name="search_view_id" ref="view_my_report_search"/>
</record>
```

### 2. Empty Context
Don't include empty context - just omit it:

```xml
<!-- Avoid -->
<field name="context">{}</field>

<!-- Better - just omit the field or use meaningful context -->
<field name="context">{'search_default_filter_name': 1}</field>
```

---

## Security (ir.model.access.csv)

Format remains the same:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_report_user,my.report.user,model_my_report,account.group_account_readonly,1,0,0,0
```

---

## Common Patterns from Enterprise Code

### Report Model Example (based on sale.report)

```python
from odoo import api, fields, models

class MyReport(models.Model):
    _name = 'my.report'
    _description = "My Analysis Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    # Fields
    name = fields.Char(string="Reference", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner", readonly=True)
    amount = fields.Monetary(string="Amount", readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)

    @property
    def _table_query(self):
        return """
            SELECT
                t.id,
                t.name,
                t.date,
                t.partner_id,
                t.amount,
                t.currency_id,
                t.company_id
            FROM my_table t
            WHERE t.state = 'posted'
        """
```

### Report View Example

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_my_report_list" model="ir.ui.view">
        <field name="name">my.report.list</field>
        <field name="model">my.report</field>
        <field name="arch" type="xml">
            <list create="false" edit="false" delete="false">
                <field name="name"/>
                <field name="date"/>
                <field name="partner_id"/>
                <field name="amount" sum="Total"/>
                <field name="currency_id" column_invisible="True"/>
                <field name="company_id" groups="base.group_multi_company"/>
            </list>
        </field>
    </record>

    <record id="view_my_report_search" model="ir.ui.view">
        <field name="name">my.report.search</field>
        <field name="model">my.report</field>
        <field name="arch" type="xml">
            <search string="My Report">
                <field name="name"/>
                <field name="partner_id"/>
                <filter string="Filter A" name="filter_a" domain="[('field', '=', 'value')]"/>
                <filter name="filter_date" date="date"/>
                <group>
                    <filter string="Partner" name="group_by_partner" context="{'group_by': 'partner_id'}"/>
                    <filter string="Date" name="group_by_date" context="{'group_by': 'date:month'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="view_my_report_pivot" model="ir.ui.view">
        <field name="name">my.report.pivot</field>
        <field name="model">my.report</field>
        <field name="arch" type="xml">
            <pivot string="My Analysis">
                <field name="partner_id" type="row"/>
                <field name="date" interval="month" type="col"/>
                <field name="amount" type="measure"/>
            </pivot>
        </field>
    </record>

    <record id="view_my_report_graph" model="ir.ui.view">
        <field name="name">my.report.graph</field>
        <field name="model">my.report</field>
        <field name="arch" type="xml">
            <graph string="My Analysis" type="bar">
                <field name="partner_id"/>
                <field name="amount" type="measure"/>
            </graph>
        </field>
    </record>

    <record id="action_my_report" model="ir.actions.act_window">
        <field name="name">My Report</field>
        <field name="res_model">my.report</field>
        <field name="view_mode">list,pivot,graph</field>
        <field name="search_view_id" ref="view_my_report_search"/>
    </record>

    <menuitem id="menu_my_report"
              name="My Report"
              parent="account.menu_finance_reports"
              action="action_my_report"
              sequence="50"/>

</odoo>
```

---

## Troubleshooting

### Common Error: "Invalid view type: 'tree'"
- Change `<tree>` to `<list>` in view definitions
- Change `tree` to `list` in `view_mode`

### Common Error: "Invalid view XXX definition"
- Check for unsupported attributes in search view `<group>` tags
- Remove `expand` and `string` attributes from Group By groups
- Verify date filter syntax

### Common Error: "function date_part(unknown, integer) does not exist"
- When calculating date differences in PostgreSQL, subtracting two DATE types returns an integer (days)
- Use `ABS(date1 - date2)` directly instead of `DATE_PART('day', date1 - date2)`

---

## Reference Files in Enterprise

- **SQL View Report Model:** `enterprise/odoo/addons/sale/report/sale_report.py`
- **Report Views:** `enterprise/odoo/addons/sale/report/sale_report_views.xml`
- **Account Move Views:** `enterprise/odoo/addons/account/views/account_move_views.xml`

---

*Last Updated: January 4, 2026*
*Based on: Odoo 19 Enterprise Source Code Analysis*
