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


# 只有以"评论"为主的用例才启用裸 id 清理。
# 其他用例（sum_xwlb / sum_hn / sum_yahoo 等）正文里含大量有实际含义的 6-8 位数字
# （统计数字、日期、版本号，如 870269亿元、20220417、KB5078127），不能被误删。
BARE_ID_STRIP_USE_CASES = {'sum_hn_comments'}


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


def transform_markdown_to_plain_text(markdown_content: str, strip_bare_ids: bool = False) -> str:
    """
    Transform markdown content to plain text format.

    Transformations:
    - Remove markdown links (keep only link text)
    - Convert bullet points to numbered lists
    - Remove markdown formatting (bold, italic, etc.)
    - Handle headers and other markdown elements
    - Replace separator lines (---, ----, ——, ...) with two blank lines
    - Remove comment-id references / raw links (meaningless when read aloud)
    - (removed)Add punctuation to lines without proper sentence-ending punctuation

    Args:
        strip_bare_ids: 是否清理"裸"评论 id（6-8 位数字）。仅对评论类用例安全；
            其他用例正文里的数字有实际含义，须保持 False。
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

    # Replace separator lines (runs of dashes / en dashes / em dashes) with two blank lines.
    # The LLM often echoes the article separators used by the sum_* scripts (e.g. '-' * 80)
    # and sometimes invents its own (----, ——, etc.).
    markdown_content = re.sub(r'^[ \t]*[-–—]{2,}[ \t]*$', '\n\n', markdown_content, flags=re.MULTILINE)

    # Remove comment-id references / raw links that are meaningless when read aloud, e.g.:
    #   "相关评论：47548623, 47548846, 47549133。" / "相关讨论： id:48037881 , id:48041909"
    #   "（id: 47939086）" / "（Groxx id: 48089092）" / "[id:47907861]" / "(hansmayer, id=47905267)"
    #   "（如 chromacity 47615578）" / "（#47105824）" / 裸 id "46655743, 46650459"
    #   "https://news.ycombinator.com/item?id=47912973"
    # 原始 URL：朗读无意义，且往往内含 ?id=<评论id>，整体删除
    markdown_content = re.sub(r'[ \t]*https?://\S+', '', markdown_content)
    # 带 "相关X：" 引导的 id 列表整体删除（数字 >=5 位，避免误删计数等小数字）
    markdown_content = re.sub(
        r'相关(?:评论|讨论|帖子|链接)[ \t]*[:：][ \t]*(?:(?:id[ \t]*[:：=]?[ \t]*)?[#＃]?\d{5,}[ \t]*[,，、]?[ \t]*)+[。.]?',
        '', markdown_content)
    # 括号内只含 id 的形式整体删除（"（id: 47939086）" / "（#47105824）" / "（47694076）" / "[id:47907861]"）
    markdown_content = re.sub(
        r'[ \t]*[（(\[][ \t]*id[ \t]*[:：=]?[ \t]*\d+[ \t]*[)）\]]', '', markdown_content, flags=re.IGNORECASE)
    markdown_content = re.sub(
        r'[ \t]*[（(\[][ \t]*[#＃]?\d{6,8}[ \t]*[)）\]]', '', markdown_content)
    # 带 id 标签的形式： "id:47939086" / "id=47905267"
    markdown_content = re.sub(
        r'(?<![A-Za-z])id[ \t]*[:：=][ \t]*\d+', '', markdown_content, flags=re.IGNORECASE)
    if strip_bare_ids:
        # 裸评论 id（6-8 位数字，可带 # 前缀，且不与其它数字/小数点相邻）
        markdown_content = re.sub(r'[ \t]*(?<![\d.])[#＃]?\d{6,8}(?![\d.])', '', markdown_content)
        # 只剩 id 的行（如 "46447585 46447840"）整体删除
        markdown_content = re.sub(
            r'^[ \t]*(?:[-*+]|\d+\.)?[ \t]*[#＃]?\d{6,8}(?:[ \t]*[,，、][ \t]*[#＃]?\d{6,8})*[ \t]*$',
            '', markdown_content, flags=re.MULTILINE)
    # 清掉内容全是 id、删除后只剩列表符号/序号的空行
    markdown_content = re.sub(r'^[ \t]*(?:[-*+]|\d+\.)[ \t]*$', '', markdown_content, flags=re.MULTILINE)

    # Clean up separators / brackets left dangling by the removals above, e.g.
    #   "讨论链接：, 。" -> "讨论链接。"
    markdown_content = re.sub(r'[:：][ \t]*(?:[,，、][ \t]*)+(?=[。.)）\]]|$)', '', markdown_content, flags=re.MULTILINE)
    markdown_content = re.sub(r'[,，、][ \t]*([。.])[ \t]*$', r'\1', markdown_content, flags=re.MULTILINE)
    markdown_content = re.sub(r'(?<![（(])[,，、][ \t]*([)）\]])', r'\1', markdown_content)
    # URL 被删除后可能留下悬空的方括号/圆括号，如 "(345条评论)[" -> "(345条评论)"
    markdown_content = re.sub(r'[(（\[](?=[ \t]*$)', '', markdown_content, flags=re.MULTILINE)

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

            # Add punctuation to lines without proper sentence-ending punctuation
            #if stripped and not re.search(r'[.。!！?？;；…，,]$', stripped):
            #    line = line + '.'
            transformed_lines.append(line)

    return '\n'.join(transformed_lines)


def process_file(storage_obj, key: str, output_dir: str = None, override: bool = False,
                 strip_bare_ids: bool = False) -> Tuple[str, str]:
    """Process a single chat history file.

    Returns:
        (status, detail) where status is one of:
          'processed' - plain text written; detail is the generated text
          'skipped'   - nothing to do; detail is the skip reason
          'error'     - failure; detail is the error message
    """
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
            return 'skipped', 'already exists'

        # Require the summary to be generated first. The plain text (and thus the
        # TTS audio) is only produced for conversations that already have a
        # .summary.txt, so we never fall back to the raw beginning of the article.
        summary_key = key[:-len('.txt')] + '.summary.txt'
        if not storage_obj.has(summary_key):
            return 'skipped', 'no summary'

        content = storage_obj.load(key)
        if not content:
            return 'error', f"Empty file: {key}"

        # Extract response
        response_content = extract_response(content)
        if not response_content:
            return 'error', f"No response found in: {key}"

        # Transform markdown to plain text
        plain_text = transform_markdown_to_plain_text(response_content, strip_bare_ids)

        # Save the transformed content
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(plain_text)

        return 'processed', plain_text

    except Exception as e:
        return 'error', f"Error processing {key}: {str(e)}"


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
            status, detail = process_file(storage_obj, key, args.output_dir, args.override,
                                          use_case in BARE_ID_STRIP_USE_CASES)

            if status == 'processed':
                processed_count += 1
                print(f"✅ Processed: {key}")
            elif status == 'skipped':
                skipped_count += 1
                if detail == 'no summary':
                    print(f"⏭️  Skipped (no summary): {key}")
            else:
                error_count += 1
                print(f"❌ {detail}")

        print(f"Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}")


if __name__ == '__main__':
    main()
