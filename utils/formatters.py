"""
Formatters for query results
Convert query results to various output formats
"""

import json
from typing import List, Dict, Any


def format_as_table(results: List[Dict[str, Any]], columns: List[str] = None) -> str:
    """
    Format results as ASCII table

    Args:
        results: List of result dictionaries
        columns: List of column names (if None, uses keys from first result)

    Returns:
        ASCII table string
    """
    if not results:
        return "No results found."

    # Determine columns
    if columns is None:
        columns = list(results[0].keys())

    # Calculate column widths
    widths = {}
    for col in columns:
        widths[col] = len(col)
        for row in results:
            value = str(row.get(col, ''))
            widths[col] = max(widths[col], len(value))

    # Build table
    lines = []

    # Header
    header = "| " + " | ".join(col.ljust(widths[col]) for col in columns) + " |"
    separator = "|-" + "-|-".join("-" * widths[col] for col in columns) + "-|"

    lines.append(header)
    lines.append(separator)

    # Rows
    for row in results:
        line = "| " + " | ".join(str(row.get(col, '')).ljust(widths[col]) for col in columns) + " |"
        lines.append(line)

    return "\n".join(lines)


def format_as_markdown(results: List[Dict[str, Any]], title: str = None, columns: List[str] = None) -> str:
    """
    Format results as Markdown

    Args:
        results: List of result dictionaries
        title: Optional title
        columns: List of column names (if None, uses keys from first result)

    Returns:
        Markdown formatted string
    """
    if not results:
        return f"# {title}\n\nNo results found." if title else "No results found."

    lines = []

    if title:
        lines.append(f"# {title}\n")

    # Determine columns
    if columns is None:
        columns = list(results[0].keys())

    # Create markdown table
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"

    lines.append(header)
    lines.append(separator)

    for row in results:
        line = "| " + " | ".join(str(row.get(col, '')) for col in columns) + " |"
        lines.append(line)

    return "\n".join(lines)


def format_as_json(results: Any, pretty: bool = True) -> str:
    """
    Format results as JSON

    Args:
        results: Results to format (can be list, dict, etc.)
        pretty: Whether to pretty-print with indentation

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(results, indent=2, default=str)
    else:
        return json.dumps(results, default=str)


def format_as_csv(results: List[Dict[str, Any]], columns: List[str] = None) -> str:
    """
    Format results as CSV

    Args:
        results: List of result dictionaries
        columns: List of column names (if None, uses keys from first result)

    Returns:
        CSV formatted string
    """
    if not results:
        return ""

    # Determine columns
    if columns is None:
        columns = list(results[0].keys())

    lines = []

    # Header
    lines.append(",".join(columns))

    # Rows
    for row in results:
        values = []
        for col in columns:
            value = str(row.get(col, ''))
            # Escape commas and quotes
            # if ',' in value or '"' in value:
            #     value = f'"{value.replace('"', '""')}"'
            values.append(value)
        lines.append(",".join(values))

    return "\n".join(lines)


def format_as_list(results: List[Dict[str, Any]], item_format: str = "{name} - {file}") -> str:
    """
    Format results as simple list

    Args:
        results: List of result dictionaries
        item_format: Format string for each item (e.g., "{name} in {file}")

    Returns:
        Formatted list string
    """
    if not results:
        return "No results found."

    lines = []
    for i, row in enumerate(results, 1):
        try:
            line = f"{i}. {item_format.format(**row)}"
        except KeyError:
            # Fallback if format string has missing keys
            line = f"{i}. {row}"
        lines.append(line)

    return "\n".join(lines)


def print_results(results: Any, format_type: str = "table", **kwargs):
    """
    Print results in specified format

    Args:
        results: Results to print
        format_type: One of: table, markdown, json, csv, list
        **kwargs: Additional arguments for formatter
    """
    if format_type == "table":
        print(format_as_table(results, **kwargs))
    elif format_type == "markdown":
        print(format_as_markdown(results, **kwargs))
    elif format_type == "json":
        print(format_as_json(results, **kwargs))
    elif format_type == "csv":
        print(format_as_csv(results, **kwargs))
    elif format_type == "list":
        print(format_as_list(results, **kwargs))
    else:
        print(results)