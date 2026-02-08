"""
Resource Management CLI
Manage books and articles without starting the server.

Usage:
    python scripts/manage_resources.py list
    python scripts/manage_resources.py list --type book
    python scripts/manage_resources.py list --type article
    python scripts/manage_resources.py delete "filename.pdf" --type book
    python scripts/manage_resources.py get-link "article.pdf"
    python scripts/manage_resources.py stats
"""

import sys
import os
import argparse

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.resources import ResourceManager


def main():
    parser = argparse.ArgumentParser(
        description="Manage resources (books/articles) for StartupGuru",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/manage_resources.py list
  python scripts/manage_resources.py list --type book
  python scripts/manage_resources.py list --type article
  python scripts/manage_resources.py delete "The Mom Test-by-Rob FitzPatrick.pdf" --type book
  python scripts/manage_resources.py get-link "article-name.pdf"
  python scripts/manage_resources.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all resources")
    list_parser.add_argument("--type", choices=["book", "article"], help="Filter by resource type")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a resource")
    delete_parser.add_argument("source_file", help="Source file name to delete")
    delete_parser.add_argument("--type", required=True, choices=["book", "article"], help="Resource type")
    
    # Get link command
    link_parser = subparsers.add_parser("get-link", help="Get article URL")
    link_parser.add_argument("source_file", help="Source file name")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show resource statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = ResourceManager()
    
    if args.command == "list":
        resources = manager.list_resources(resource_type=args.type)
        if not resources:
            print("No resources found.")
        else:
            # Separate books and articles
            books = [r for r in resources if r.resource_type == "book"]
            articles = [r for r in resources if r.resource_type == "article"]
            
            print(f"\n{'='*70}")
            print("  RESOURCES")
            print(f"{'='*70}")
            
            if books and (not args.type or args.type == "book"):
                print(f"\n  📚 BOOKS ({len(books)})")
                print(f"  {'-'*66}")
                for book in books:
                    print(f"    • {book.title}")
                    print(f"      Author: {book.author}")
                    print(f"      File: {book.source_file}")
                    print(f"      Chunks: {book.chunk_count}")
                    print()
            
            if articles and (not args.type or args.type == "article"):
                print(f"\n  📄 ARTICLES ({len(articles)})")
                print(f"  {'-'*66}")
                for article in articles:
                    print(f"    • {article.title}")
                    print(f"      Author: {article.author}")
                    print(f"      File: {article.source_file}")
                    print(f"      Chunks: {article.chunk_count}")
                    if article.url:
                        print(f"      URL: {article.url}")
                    print()
            
            print(f"{'='*70}\n")
    
    elif args.command == "delete":
        print(f"\n⚠️  Warning: This will permanently delete all vectors for '{args.source_file}'")
        confirm = input("Type 'yes' to confirm: ")
        
        if confirm.lower() == "yes":
            deleted = manager.delete_resource(args.source_file, args.type)
            if deleted:
                print(f"\n✅ Resource '{args.source_file}' deleted successfully!\n")
            else:
                print(f"\n❌ Failed to delete resource.\n")
                sys.exit(1)
        else:
            print("\n❌ Deletion cancelled.\n")
    
    elif args.command == "get-link":
        url = manager.get_article_link(args.source_file)
        if url:
            print(f"\n🔗 URL for '{args.source_file}':")
            print(f"   {url}\n")
        else:
            print(f"\n❌ No URL found for '{args.source_file}' (not an article or URL not stored)\n")
    
    elif args.command == "stats":
        counts = manager.get_resource_count()
        print(f"\n{'='*40}")
        print("  RESOURCE STATISTICS")
        print(f"{'='*40}")
        print(f"  📚 Books: {counts['books']}")
        print(f"  📄 Articles: {counts['articles']}")
        print(f"  📊 Total Chunks: {counts['total_chunks']}")
        print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
