#!/usr/bin/env python3
"""
List available projects from config
"""
from config import PROJECTS, DEFAULT_PROJECT


def main():
    print("=" * 60)
    print("Available Odoo Projects")
    print("=" * 60)
    
    for key, config in PROJECTS.items():
        is_default = " (DEFAULT)" if key == DEFAULT_PROJECT else ""
        print(f"\n📦 {key}{is_default}")
        print(f"   {config.get('description', 'No description')}")
        print(f"   URL: {config['url']}")
        print(f"   DB: {config['db']}")
        print(f"   User: {config['username']}")
    
    print("\n" + "=" * 60)
    print("Usage in scripts:")
    print("=" * 60)
    print(f"   client = OdooClient()                 # Uses default: {DEFAULT_PROJECT}")
    print(f"   client = OdooClient(project='bml19')  # Uses specific project")


if __name__ == '__main__':
    main()
