"""
Example Usage of CodeCompass Query Interface

Run this after parsing a repository to explore the codebase
"""

from query import Query
from utils.formatters import print_results, format_as_markdown
import sys


def main():
    """Example queries"""

    # Initialize CodeCompass (uses config defaults)
    with Query() as query:

        print("CODEBASE OVERVIEW")
        print("-" * 60)
        stats = query.get_codebase_stats()
        print(f"Files:       {stats.get('files', 0)}")
        print(f"Directories: {stats.get('directories', 0)}")
        print(f"Classes:     {stats.get('classes', 0)}")
        print(f"Functions:   {stats.get('functions', 0)}")
        print(f"Methods:     {stats.get('methods', 0)}")
        print()

        # ========== ENTRY POINTS ==========
        print("ENTRY POINTS (Where to start)")
        print("-" * 60)
        entry_points = query.get_entry_points(limit=5)
        if entry_points:
            for i, func in enumerate(entry_points, 1):
                print(f"{i}. {func['name']}")
                print(f"   {func['file']}:{func['line']}")
                print(f"   Called by {func['called_by']} functions, calls {func['calls_out']}")
                print()
        else:
            print("No entry points found.")
        print()

        # ========== LEARNING PATH ==========
        print("LEARNING PATH (Simple → Complex)")
        print("-" * 60)
        learning_path = query.get_learning_path(limit=5)
        if learning_path:
            for i, func in enumerate(learning_path, 1):
                print(f"{i}. {func['name']} (Complexity: {func['complexity_score']})")
                print(f"   📁 {func['file']}:{func['line']}")
                print()
        else:
            print("No learning path found.")
        print()

        # ========== DEAD CODE ==========
        print("DEAD CODE (Unused functions)")
        print("-" * 60)
        dead_code = query.find_dead_code()
        if dead_code:
            print(f"Found {len(dead_code)} unused functions:")
            for func in dead_code[:5]:
                print(f"  - {func['name']} in {func['file']}:{func['line']}")
            if len(dead_code) > 5:
                print(f"  ... and {len(dead_code) - 5} more")
        else:
            print("No dead code found!")
        print()

        # ========== GOD FUNCTIONS ==========
        print("🔥 COMPLEX FUNCTIONS (Need refactoring)")
        print("-" * 60)
        god_functions = query.find_god_functions()
        if god_functions:
            for i, func in enumerate(god_functions[:5], 1):
                print(f"{i}. {func['name']}")
                print(f"   {func['file']}:{func['line']}")
                print(f"   {func['lines']} lines, {func['calls']} calls")
                print(f"   Complexity: {func['complexity_score']}")
                print()
        else:
            print("No overly complex functions found!")
        print()

        # ========== COMPLEXITY HOTSPOTS ==========
        print("COMPLEXITY HOTSPOTS")
        hotspots = query.get_complexity_hotspots(limit=5)
        if hotspots:
            for i, file_info in enumerate(hotspots, 1):
                print(f"{i}. {file_info['file']}")
                print(f"   Score: {file_info['hotspot_score']} | "
                      f"Entities: {file_info['entities']} | "
                      f"In: {file_info['incoming']} | "
                      f"Out: {file_info['outgoing']}")
                print()
        else:
            print("No hotspots found.")
        print()

        # ========== MOST CALLED FUNCTIONS ==========
        print("MOST CALLED FUNCTIONS (Critical)")
        most_called = query.get_most_called_functions(limit=5)
        if most_called:
            for i, func in enumerate(most_called, 1):
                print(f"{i}. {func['name']} ({func['times_called']} calls)")
                print(f"  {func['file']}:{func['line']}")
                print()
        else:
            print("No function call data found.")
        print()


def demo_blast_radius():
    """Demo: Check blast radius for a specific function"""

    function_name = input("Enter function name to analyze: ")

    with Query() as query:
        print(f"\nBLAST RADIUS ANALYSIS: {function_name}")

        # Get function context
        context = query.get_function_context(function_name)

        if 'error' in context:
            print(f"{context['error']}")
            return

        func = context['function']
        print(f"\n Function: {func['name']}")
        print(f"File: {func['file']}:{func['start_line']}-{func['end_line']}")

        callers = context['callers']
        callees = context['callees']

        print(f"\nCalled by {len(callers)} functions:")
        for caller in callers[:5]:
            print(f" {caller['name']} ({caller['file']})")
        if len(callers) > 5:
            print(f"  ... and {len(callers) - 5} more")

        print(f"\nCalls {len(callees)} functions:")
        for callee in callees[:5]:
            print(f" {callee['name']} ({callee['file']})")
        if len(callees) > 5:
            print(f"  ... and {len(callees) - 5} more")

        # Full blast radius
        blast_radius = query.get_blast_radius(function_name, max_depth=3)
        print(f"\nTotal blast radius: {len(blast_radius)} functions affected")

        if blast_radius:
            print("\nAffected functions (by depth):")
            for affected in blast_radius[:10]:
                print(f"  Depth {affected['depth']}: {affected['affected_function']} ({affected['affected_file']})")
            if len(blast_radius) > 10:
                print(f"  ... and {len(blast_radius) - 10} more")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "blast-radius":
        demo_blast_radius()
    else:
        main()