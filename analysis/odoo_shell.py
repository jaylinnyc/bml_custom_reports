#!/usr/bin/env python3
"""
Interactive Odoo Shell - explore models and data interactively
"""
from odoo_client import OdooClient
import json
import readline  # For command history


def print_help():
    print("""
Available commands:
  models <search>     - Search for models (e.g., models account)
  fields <model>      - Show fields for a model
  count <model>       - Count records in a model
  read <model> [n]    - Read n records from model (default 5)
  search <model> <domain> - Search with domain (JSON format)
  sql <query>         - Execute raw SQL (read-only)
  help                - Show this help
  quit/exit           - Exit the shell
  
Examples:
  models invoice
  fields account.move
  count res.partner
  read res.partner 3
  search account.move [["state", "=", "posted"]]
""")


def main():
    print("=" * 60)
    print("Odoo Interactive Shell")
    print("=" * 60)
    
    client = OdooClient()
    print("\nType 'help' for available commands, 'quit' to exit.\n")
    
    while True:
        try:
            cmd = input("odoo> ").strip()
            if not cmd:
                continue
            
            parts = cmd.split(None, 2)
            action = parts[0].lower()
            
            if action in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break
            
            elif action == 'help':
                print_help()
            
            elif action == 'models':
                search = parts[1] if len(parts) > 1 else ''
                models = client.search_read(
                    'ir.model',
                    [('model', 'ilike', search)] if search else [],
                    ['model', 'name'],
                    limit=20
                )
                for m in models:
                    print(f"  {m['model']}: {m['name']}")
                print(f"\n  Found {len(models)} models" + (" (showing first 20)" if len(models) == 20 else ""))
            
            elif action == 'fields':
                if len(parts) < 2:
                    print("Usage: fields <model>")
                    continue
                model = parts[1]
                fields = client.get_fields(model)
                for name, info in sorted(fields.items()):
                    print(f"  {name}: {info.get('type')} - {info.get('string')}")
                print(f"\n  Total: {len(fields)} fields")
            
            elif action == 'count':
                if len(parts) < 2:
                    print("Usage: count <model>")
                    continue
                model = parts[1]
                count = client.search_count(model)
                print(f"  {model}: {count} records")
            
            elif action == 'read':
                if len(parts) < 2:
                    print("Usage: read <model> [limit]")
                    continue
                model = parts[1]
                limit = int(parts[2]) if len(parts) > 2 else 5
                records = client.search_read(model, [], limit=limit)
                print(json.dumps(records, indent=2, default=str))
            
            elif action == 'search':
                if len(parts) < 3:
                    print("Usage: search <model> <domain>")
                    print("Example: search account.move [[\"state\", \"=\", \"posted\"]]")
                    continue
                model = parts[1]
                domain = json.loads(parts[2])
                records = client.search_read(model, domain, limit=10)
                print(json.dumps(records, indent=2, default=str))
                print(f"\n  Found {len(records)} records (showing max 10)")
            
            else:
                print(f"Unknown command: {action}")
                print("Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == '__main__':
    main()
