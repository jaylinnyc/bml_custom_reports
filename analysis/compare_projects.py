#!/usr/bin/env python3
"""
Compare field configurations across multiple Odoo projects
"""
import json
from odoo_client import OdooClient
from config import PROJECTS


def compare_fields(field1, field2, field_name):
    """Compare two field definitions and return differences"""
    differences = []
    
    # Compare key attributes
    attrs = ['type', 'string', 'required', 'readonly', 'store', 'help']
    for attr in attrs:
        val1 = field1.get(attr)
        val2 = field2.get(attr)
        if val1 != val2:
            differences.append({
                'attribute': attr,
                'project1': val1,
                'project2': val2
            })
    
    return differences


def main():
    print("=" * 60)
    print("Multi-Project Field Comparison")
    print("=" * 60)
    
    if len(PROJECTS) < 2:
        print("\n⚠️  Only one project configured. Add more projects to config.py")
        return
    
    projects = list(PROJECTS.keys())
    print(f"\n📋 Comparing projects: {', '.join(projects)}\n")
    
    # Connect to all projects
    clients = {}
    for project in projects:
        print(f"Connecting to {project}...")
        clients[project] = OdooClient(project=project, verbose=True)
        print()
    
    # Fields to check
    target_fields = [
        'date',
        'invoice_date',
        'delivery_date',
        'x_studio_taxinvoice_date',
        'taxinvoice_date'
    ]
    
    print("\n" + "=" * 60)
    print("Field Existence Check")
    print("=" * 60)
    
    # Get fields from all projects
    all_fields = {}
    for project, client in clients.items():
        all_fields[project] = client.get_fields('account.move')
    
    # Check field existence
    print("\n📊 Field Existence:")
    for field_name in target_fields:
        print(f"\n  {field_name}:")
        for project in projects:
            exists = field_name in all_fields[project]
            status = "✅" if exists else "❌"
            print(f"    {status} {project}")
    
    # Compare field definitions for fields that exist in multiple projects
    print("\n" + "=" * 60)
    print("Field Definition Comparison")
    print("=" * 60)
    
    for field_name in target_fields:
        # Skip if field doesn't exist in at least 2 projects
        exists_in = [p for p in projects if field_name in all_fields[p]]
        if len(exists_in) < 2:
            continue
        
        print(f"\n🔍 {field_name}:")
        
        # Compare first two projects that have this field
        p1, p2 = exists_in[0], exists_in[1]
        field1 = all_fields[p1][field_name]
        field2 = all_fields[p2][field_name]
        
        diffs = compare_fields(field1, field2, field_name)
        
        if not diffs:
            print(f"  ✅ Identical in {p1} and {p2}")
        else:
            print(f"  ⚠️  Differences found:")
            for diff in diffs:
                print(f"     {diff['attribute']}:")
                print(f"       {p1}: {diff['project1']}")
                print(f"       {p2}: {diff['project2']}")
    
    # Check Studio fields
    print("\n" + "=" * 60)
    print("Studio Fields (x_studio_*)")
    print("=" * 60)
    
    for project in projects:
        print(f"\n📦 {project}:")
        studio_fields = [name for name in all_fields[project].keys() 
                        if name.startswith('x_studio_')]
        if studio_fields:
            for field_name in sorted(studio_fields):
                info = all_fields[project][field_name]
                print(f"  • {field_name}: {info.get('type')} - {info.get('string')}")
        else:
            print("  (none)")
    
    # Save detailed comparison
    comparison = {
        'projects': {p: PROJECTS[p]['description'] for p in projects},
        'field_existence': {
            field: {p: field in all_fields[p] for p in projects}
            for field in target_fields
        },
        'studio_fields': {
            p: [name for name in all_fields[p].keys() if name.startswith('x_studio_')]
            for p in projects
        }
    }
    
    with open('project_comparison.json', 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    print(f"\n💾 Saved detailed comparison to project_comparison.json")


if __name__ == '__main__':
    main()
