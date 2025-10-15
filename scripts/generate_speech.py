#!/usr/bin/env python3
"""
Generate speech audio files from plain text files in storage directories.

This script processes plain text files from storage directories and generates
MP3 audio files using a text-to-speech API.
"""

import argparse
import os
import sys
import requests
import time
from pathlib import Path
from typing import List

from chat_with_llm import storage


def generate_speech(api_url: str, text: str, output_path: str, wav_name: str = None, timeout: int = 1800) -> bool:
    """Generate speech and save to file."""
    try:
        # Prepare request data
        data = {
            "text": text,
            "output_format": "mp3"
        }
        if wav_name:
            data["wav_name"] = wav_name

        print(f"正在生成语音...")
        print(f"文本长度: {len(text)} 字符")
        print(f"输出格式: mp3")
        if wav_name:
            print(f"使用语音: {wav_name}")

        start_time = time.time()

        # Send POST request
        response = requests.post(f"{api_url}/tts", json=data, timeout=timeout)

        processing_time = time.time() - start_time

        if response.status_code == 200:
            # Save audio file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✓ 语音文件已保存: {output_path}")
            print(f"✓ 处理时间: {processing_time:.2f} 秒")
            print(f"✓ 音频大小: {len(response.content)} 字节")
            return True

        else:
            print(f"✗ 语音生成失败: HTTP {response.status_code}")
            print(f"错误详情: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ 无法连接到API服务器: {api_url}")
        print("请确保API服务正在运行")
        return False
    except requests.exceptions.Timeout:
        print("✗ 请求超时，请稍后重试")
        return False
    except Exception as e:
        print(f"✗ 发生错误: {str(e)}")
        return False


def get_plain_text_files(storage_obj, n: int = 10) -> List[str]:
    """Get the latest n plain text files from storage."""
    keys = storage_obj.list()

    # Filter for .plain.txt files
    plain_files = [key for key in keys if key.endswith('.plain.txt')]

    # Sort by filename timestamp (newest first)
    # Extract timestamp from filename (format: YYYYMMDD_HHMMSS)
    plain_files_with_timestamp = []
    for key in plain_files:
        # Extract the timestamp part from filename
        # Example: "20250901_153902_deepseek-chat.plain.txt" -> "20250901_153902"
        filename = key.replace('.plain.txt', '')
        parts = filename.split('_')
        if len(parts) >= 2:
            timestamp_str = f"{parts[0]}_{parts[1]}"
            plain_files_with_timestamp.append((key, timestamp_str))
        else:
            # If filename doesn't match expected format, use filename as timestamp
            plain_files_with_timestamp.append((key, filename))

    # Sort by timestamp (newest first)
    plain_files_with_timestamp.sort(key=lambda x: x[1], reverse=True)
    return [key for key, _ in plain_files_with_timestamp[:n]]


def process_use_case(use_case: str, n: int, api_url: str, wav_name: str = None, timeout: int = 1800, dry_run: bool = False):
    """Process a single use case."""
    print(f"\n处理用例: {use_case}")
    print("=" * 50)

    storage_obj = storage.get_storage('chat_history', use_case)
    plain_files = get_plain_text_files(storage_obj, n)

    print(f"找到 {len(plain_files)} 个最新的 .plain.txt 文件")

    processed_count = 0
    error_count = 0
    skipped_count = 0

    for key in plain_files:
        # Check if MP3 file already exists
        mp3_key = key.replace('.plain.txt', '.mp3')
        mp3_path = os.path.join(storage_obj.storage_path, mp3_key)

        if os.path.exists(mp3_path):
            print(f"⏭️  跳过 (已存在): {key}")
            skipped_count += 1
            continue

        # Read plain text content
        plain_text_path = os.path.join(storage_obj.storage_path, key)
        try:
            with open(plain_text_path, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()

            if not text_content:
                print(f"⚠️  跳过 (空文件): {key}")
                skipped_count += 1
                continue

            if dry_run:
                print(f"📋  将处理 (预览): {key}")
                print(f"    文本长度: {len(text_content)} 字符")
                print(f"    输出文件: {mp3_key}")
                if wav_name:
                    print(f"    使用语音: {wav_name}")
                processed_count += 1
            else:
                print(f"\n处理文件: {key}")
                print("-" * 30)

                # Generate speech
                success = generate_speech(
                    api_url=api_url,
                    text=text_content,
                    output_path=mp3_path,
                    wav_name=wav_name,
                    timeout=timeout
                )

                if success:
                    processed_count += 1
                else:
                    error_count += 1

        except Exception as e:
            print(f"✗ 处理文件时发生错误 {key}: {str(e)}")
            error_count += 1

    print(f"\n处理完成: {use_case}")
    print(f"已处理: {processed_count}, 跳过: {skipped_count}, 错误: {error_count}")
    return processed_count, skipped_count, error_count


def main():
    parser = argparse.ArgumentParser(
        description='从存储目录中的纯文本文件生成语音音频文件'
    )
    parser.add_argument(
        '-u', '--use_cases',
        type=lambda s: s.split(','),
        required=True,
        help='逗号分隔的用例列表 (例如: sum_hn,sum_xwlb)'
    )
    parser.add_argument(
        '-n',
        type=int,
        default=10,
        help='每个用例处理的最新文件数量 (默认: 10)'
    )
    parser.add_argument(
        '--api-url',
        default='http://10.20.1.3:8000',
        help='TTS API服务器地址 (默认: http://10.20.1.3:8000)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=1800,
        help='请求超时时间（秒，默认: 1800秒）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，显示将要处理的内容而不实际生成语音'
    )
    parser.add_argument(
        '--wav-name',
        help='WAV文件名称 (可选，使用默认值如果未指定)'
    )

    args = parser.parse_args()

    print("语音生成工具")
    print("=" * 50)
    print(f"API地址: {args.api_url}")
    print(f"每个用例处理文件数: {args.n}")
    print(f"超时设置: {args.timeout} 秒")
    if args.wav_name:
        print(f"使用语音: {args.wav_name}")
    print("=" * 50)

    total_processed = 0
    total_skipped = 0
    total_errors = 0

    for use_case in args.use_cases:
        processed, skipped, errors = process_use_case(
            use_case=use_case,
            n=args.n,
            api_url=args.api_url,
            wav_name=args.wav_name,
            timeout=args.timeout,
            dry_run=args.dry_run
        )
        total_processed += processed
        total_skipped += skipped
        total_errors += errors

    print(f"\n" + "=" * 50)
    print("总体统计:")
    print(f"已处理: {total_processed}")
    print(f"跳过: {total_skipped}")
    print(f"错误: {total_errors}")
    print("=" * 50)

    if total_errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
