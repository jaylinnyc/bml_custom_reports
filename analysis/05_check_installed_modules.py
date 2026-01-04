#!/usr/bin/env python3
"""
Check installed modules and their versions
"""
import json
from odoo_client import OdooClient


def main():
    print("=" * 60)
    print("Checking Installed Modules")
    print("=" * 60)
    
    client = OdooClient()
    
    # Check our custom modules
    print("\n🔧 Checking custom modules...")
    custom_modules = ['bml_custom_reports', 'nexus_odoo_thailand_etax', 'nexus_odoo_sign_reports']
    
    for module_name in custom_modules:
        modules = client.search_read(
            'ir.module.module',
            [('name', '=', module_name)],
            ['name', 'state', 'installed_version', 'latest_version', 'summary']
        )
        if modules:
            m = modules[0]
            status = "✅" if m['state'] == 'installed' else "❌"
            print(f"   {status} {m['name']}: {m['state']} (v{m.get('installed_version', 'N/A')})")
            if m.get('summary'):
                print(f"      {m['summary']}")
        else:
            print(f"   ❌ {module_name}: NOT FOUND")
    
    # Get all installed modules
    print("\n📦 All installed modules:")
    installed = client.search_read(
        'ir.module.module',
        [('state', '=', 'installed')],
        ['name', 'installed_version', 'author'],
        order='name'
    )
    
    # Group by author
    by_author = {}
    for m in installed:
        author = m.get('author', 'Unknown') or 'Unknown'
        # Simplify author name
        if 'Odoo' in author:
            author = 'Odoo SA'
        elif len(author) > 30:
            author = author[:30] + '...'
        
        if author not in by_author:
            by_author[author] = []
        by_author[author].append(m['name'])
    
    print(f"\n   Total installed: {len(installed)}")
    for author, modules in sorted(by_author.items()):
        print(f"   {author}: {len(modules)} modules")
    
    # Save full list
    with open('installed_modules.json', 'w') as f:
        json.dump(installed, f, indent=2, default=str)
    print(f"\n💾 Saved module list to installed_modules.json")


if __name__ == '__main__':
    main()
