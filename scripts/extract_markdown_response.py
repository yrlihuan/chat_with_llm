#!/usr/bin/env python3
"""
Extract and transform markdown responses from chat history files.

This script processes chat history files that contain markdown-formatted responses
and extracts the response content, transforming markdown formatting to plain text.
"""

import argparse
import os
import re
from typing import List, Tuple

from chat_with_llm import storage


def extract_response(content: str) -> str:
    """Extract the response part from chat history content."""
    lines = content.split('\n')
    response_started = False
    response_lines = []

    for line in lines:
        if line.startswith('response:'):
            response_started = True
            # Remove 'response:' prefix and any leading whitespace
            line_content = line[9:].lstrip()
            if line_content:
                response_lines.append(line_content)
        elif response_started:
            if line.strip() and not line.startswith('model:') and not line.startswith('prompt:'):
                response_lines.append(line)

    return '\n'.join(response_lines)


def transform_markdown_to_plain_text(markdown_content: str) -> str:
    """
    Transform markdown content to plain text format.

    Transformations:
    - Remove markdown links (keep only link text)
    - Convert bullet points to numbered lists
    - Remove markdown formatting (bold, italic, etc.)
    - Handle headers and other markdown elements
    - Replace --- separators with two blank lines
    """
    if not markdown_content:
        return ""

    # Remove markdown links: [text](url) -> text
    markdown_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', markdown_content)

    # Remove inline formatting: **bold** -> bold, *italic* -> italic
    markdown_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', markdown_content)
    markdown_content = re.sub(r'\*([^*]+)\*', r'\1', markdown_content)
    markdown_content = re.sub(r'`([^`]+)`', r'\1', markdown_content)

    # Convert headers to plain text
    markdown_content = re.sub(r'^#+\s+', '', markdown_content, flags=re.MULTILINE)

    # Replace --- separators with two blank lines
    markdown_content = re.sub(r'^---\s*$', '\n\n', markdown_content, flags=re.MULTILINE)

    # Process bullet points and numbered lists
    lines = markdown_content.split('\n')
    transformed_lines = []
    list_counter = 1
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Handle bullet points
        if stripped.startswith('- '):
            if not in_list:
                in_list = True
            transformed_lines.append(f'{list_counter}. {stripped[2:]}')
            list_counter += 1
        # Handle numbered lists (already numbered)
        elif re.match(r'^\d+\.\s+', stripped):
            if not in_list:
                in_list = True
            transformed_lines.append(stripped)
            list_counter += 1
        # Handle sub-bullets (indented with spaces)
        elif stripped.startswith('  - ') or stripped.startswith('   - '):
            transformed_lines.append(f'  {stripped}')
        else:
            # Reset counter when we're out of a list
            if in_list and stripped:
                list_counter = 1
                in_list = False
            transformed_lines.append(line)

    return '\n'.join(transformed_lines)


def process_file(storage_obj, key: str, output_dir: str = None, override: bool = False) -> Tuple[str, str]:
    """Process a single chat history file."""
    try:
        # Determine output path
        if output_dir:
            output_filename = key.replace('.txt', '.plain.txt')
            output_path = os.path.join(output_dir, output_filename)
        else:
            # Save in same directory as input file
            output_filename = key.replace('.txt', '.plain.txt')
            output_path = os.path.join(storage_obj.storage_path, output_filename)

        # Check if output file already exists
        if not override and os.path.exists(output_path):
            return None, None  # Skip silently

        content = storage_obj.load(key)
        if not content:
            return None, f"Empty file: {key}"

        # Extract response
        response_content = extract_response(content)
        if not response_content:
            return None, f"No response found in: {key}"

        # Transform markdown to plain text
        plain_text = transform_markdown_to_plain_text(response_content)

        # Save the transformed content
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(plain_text)

        return plain_text, None

    except Exception as e:
        return None, f"Error processing {key}: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description='Extract and transform markdown responses from chat history files'
    )
    parser.add_argument(
        '-u', '--use_cases',
        type=lambda s: s.split(','),
        required=True,
        help='Comma-separated list of use cases to process (e.g., sum_hn,sum_xwlb)'
    )
    parser.add_argument(
        '-o', '--output_dir',
        type=str,
        default=None,
        help='Output directory to save transformed files (optional)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )
    parser.add_argument(
        '--override',
        action='store_true',
        help='Override existing .plain.txt files'
    )

    args = parser.parse_args()

    for use_case in args.use_cases:
        print(f"\nProcessing use case: {use_case}")

        storage_obj = storage.get_storage('chat_history', use_case)
        keys = storage_obj.list()

        # Filter for .txt files (excluding .input.txt, .summary.txt, and .plain.txt)
        txt_files = [key for key in keys if key.endswith('.txt')
                    and not key.endswith('.input.txt')
                    and not key.endswith('.summary.txt')
                    and not key.endswith('.plain.txt')]

        print(f"Found {len(txt_files)} .txt files")

        if args.dry_run:
            print("Files to be processed:")
            for key in txt_files[:10]:  # Show first 10 files
                print(f"  - {key}")
            if len(txt_files) > 10:
                print(f"  ... and {len(txt_files) - 10} more")
            continue

        processed_count = 0
        error_count = 0
        skipped_count = 0

        for key in txt_files:
            plain_text, error = process_file(storage_obj, key, args.output_dir, args.override)

            if error:
                if error:  # Only print non-None errors
                    print(f"❌ {error}")
                    error_count += 1
                else:
                    skipped_count += 1  # Silent skip (error is None)
            elif plain_text:  # Only count if actually processed
                processed_count += 1
                print(f"✅ Processed: {key}")

        print(f"Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}")


if __name__ == '__main__':
    main()