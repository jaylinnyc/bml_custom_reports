# BML Custom Reports - Analysis Scripts

This folder contains Python scripts for analyzing and testing the bml_custom_reports module against multiple Odoo staging servers.

## Setup

1. **Copy the config template:**
   ```bash
   cp config.py.example config.py
   ```

2. **Edit `config.py` with your credentials:**
   - Get API key from: Odoo > User Menu > My Profile > Account Security > API Keys
   - Create a new API key with a descriptive name for each project
   - The config supports multiple projects (e.g., panya19prod and bml19)

3. **Install dependencies (if needed):**
   ```bash
   pip install xmlrpc-client  # Usually included in Python stdlib
   ```

## Multi-Project Support

The analysis tools support multiple Odoo instances simultaneously. This is useful when:
- Testing changes across different environments
- Comparing field configurations between projects
- Ensuring consistency across deployments

**View configured projects:**
```bash
python list_projects.py
```

**Using specific projects in scripts:**
```python
# Use default project
client = OdooClient()

# Use specific project
client = OdooClient(project='bml19')
```

## Scripts

### Connection & General

| Script | Description |
|--------|-------------|
| `odoo_client.py` | Reusable Odoo XML-RPC client class with multi-project support |
| `list_projects.py` | Show all configured projects |
| `compare_projects.py` | Compare field configurations across projects |
| `odoo_shell.py` | Interactive shell for exploring Odoo data |
| `run_all_checks.py` | Run all numbered analysis scripts |

### Analysis Scripts

| Script | Description |
|--------|-------------|
| `01_check_delivery_date_field.py` | Verify delivery_date field exists on account.move |
| `02_check_delivery_date_mismatch.py` | Check the delivery date mismatch report |
| `03_check_account_move_fields.py` | Export all account.move fields to JSON |
| `04_get_sample_invoices.py` | Get sample invoices/bills for analysis |
| `05_check_installed_modules.py` | Check installed modules and versions |

## Usage

### Run Individual Script
```bash
python 01_check_delivery_date_field.py
```

### Run All Checks
```bash
python run_all_checks.py
```

### Interactive Shell
```bash
python odoo_shell.py
```

The interactive shell supports:
- `models <search>` - Search for models
- `fields <model>` - Show fields for a model
- `count <model>` - Count records
- `read <model> [n]` - Read records
- `search <model> <domain>` - Search with domain
- `help` - Show all commands

## Output Files

Scripts generate JSON files for detailed analysis:
- `account_move_fields.json` - All fields on account.move
- `sample_invoices.json` - Sample invoice/bill data
- `installed_modules.json` - List of installed modules

These are git-ignored and won't be committed.

## Troubleshooting

### Authentication Failed
- Verify API key in `config.py`
- Make sure API key has correct permissions
- Check URL is correct (use staging URL)

### SSL Errors
- The client handles SSL for dev environments
- If issues persist, check odoo.sh status

### Connection Timeout
- Check internet connection
- Verify odoo.sh instance is running
- Try accessing URL in browser first

## Security Notes

⚠️ **Never commit `config.py`** - It contains sensitive credentials!

The `.gitignore` file protects:
- `config.py` - Your credentials
- `*.json` - Generated output files
- `__pycache__/` - Python cache
