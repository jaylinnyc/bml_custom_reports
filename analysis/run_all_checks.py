#!/usr/bin/env python3
"""
Run all analysis scripts in sequence
"""
import subprocess
import sys
import os

scripts = [
    ('01_check_delivery_date_field.py', 'Check delivery_date field'),
    ('02_check_delivery_date_mismatch.py', 'Check delivery date mismatches'),
    ('03_check_account_move_fields.py', 'Check account.move fields'),
    ('04_get_sample_invoices.py', 'Get sample invoices'),
    ('05_check_installed_modules.py', 'Check installed modules'),
]


def main():
    print("=" * 60)
    print("Running All Analysis Scripts")
    print("=" * 60)
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    results = []
    
    for script, description in scripts:
        print(f"\n{'=' * 60}")
        print(f"Running: {description}")
        print(f"Script: {script}")
        print("=" * 60)
        
        try:
            result = subprocess.run(
                [sys.executable, script],
                capture_output=False,
                text=True
            )
            results.append((script, result.returncode == 0))
        except Exception as e:
            print(f"Error running {script}: {e}")
            results.append((script, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for script, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {script}")
    
    passed = sum(1 for _, s in results if s)
    print(f"\n  {passed}/{len(results)} scripts completed successfully")


if __name__ == '__main__':
    main()
