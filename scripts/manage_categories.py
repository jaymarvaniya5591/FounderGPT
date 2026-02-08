"""
Category Management CLI
Manage categories without starting the server.

Usage:
    python scripts/manage_categories.py list
    python scripts/manage_categories.py add "Category Name" "Optional description"
    python scripts/manage_categories.py delete <category_id>
"""

import sys
import os
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.categories import CategoryManager


def main():
    parser = argparse.ArgumentParser(
        description="Manage categories for StartupGuru",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/manage_categories.py list
  python scripts/manage_categories.py add "Market Sizing" "Understanding market potential"
  python scripts/manage_categories.py delete market-sizing
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all categories")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new category")
    add_parser.add_argument("name", help="Category name")
    add_parser.add_argument("description", nargs="?", default=None, help="Category description (optional)")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a category")
    delete_parser.add_argument("category_id", help="Category ID to delete")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = CategoryManager()
    
    if args.command == "list":
        categories = manager.list_categories()
        if not categories:
            print("No categories found.")
        else:
            print(f"\n{'='*60}")
            print("  CATEGORIES")
            print(f"{'='*60}")
            for cat in categories:
                print(f"\n  ID: {cat.id}")
                print(f"  Name: {cat.name}")
                if cat.description:
                    print(f"  Description: {cat.description}")
            print(f"\n{'='*60}")
            print(f"  Total: {len(categories)} categories")
            print(f"{'='*60}\n")
    
    elif args.command == "add":
        try:
            category = manager.add_category(args.name, args.description)
            print(f"\n✅ Category created successfully!")
            print(f"   ID: {category.id}")
            print(f"   Name: {category.name}")
            if category.description:
                print(f"   Description: {category.description}")
            print()
        except Exception as e:
            print(f"\n❌ Error creating category: {e}\n")
            sys.exit(1)
    
    elif args.command == "delete":
        deleted = manager.delete_category(args.category_id)
        if deleted:
            print(f"\n✅ Category '{args.category_id}' deleted successfully!\n")
        else:
            print(f"\n❌ Category '{args.category_id}' not found.\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
