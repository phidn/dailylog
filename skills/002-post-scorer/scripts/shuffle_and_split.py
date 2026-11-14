#!/usr/bin/env python3
"""
shuffle_and_split.py
Bước 1: Tách các bài viết theo delimiter (mặc định '---') và xáo trộn ngẫu nhiên (Blind Shuffle).
Ghi nhận manifest.json đối chiếu và xuất các file bài viết độc lập vào thư mục shuffled/.
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime
from pathlib import Path

def extract_title_or_snippet(text: str, max_len: int = 60) -> str:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return "Untitled"
    first = lines[0]
    first = first.lstrip("#-* ").strip()
    return first[:max_len] + ("..." if len(first) > max_len else "")

def main():
    parser = argparse.ArgumentParser(description="Tách và xáo trộn bài viết trước khi chấm điểm không cache.")
    parser.add_argument("--input", "-i", type=str, required=True, help="Đường dẫn file đầu vào chứa các bài viết")
    parser.add_argument("--output-dir", "-o", type=str, required=True, help="Thư mục xuất kết quả (vd: tmp/20261114-cham-diem)")
    parser.add_argument("--delimiter", "-d", type=str, default="---", help="Ký hiệu phân tách giữa các bài viết (mặc định: '---')")
    parser.add_argument("--seed", "-s", type=int, default=None, help="Random seed (tự sinh nếu không truyền)")
    
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Lỗi: Không tìm thấy file {input_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    shuffled_dir = output_dir / "shuffled"
    scores_dir = output_dir / "scores"
    output_dir.mkdir(parents=True, exist_ok=True)
    shuffled_dir.mkdir(parents=True, exist_ok=True)
    scores_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Lưu bản copy raw_input.md
    raw_copy_path = output_dir / "raw_input.md"
    with open(raw_copy_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    # Tách bài viết
    raw_articles = [part.strip() for part in raw_text.split(args.delimiter) if part.strip()]
    if not raw_articles:
        print("Cảnh báo: Không tìm thấy bài viết nào sau khi tách!", file=sys.stderr)
        sys.exit(1)

    # Sinh seed nếu chưa có
    seed = args.seed if args.seed is not None else random.randint(100000, 999999)
    rng = random.Random(seed)

    # Đóng gói dữ liệu bài viết gốc
    indexed_articles = []
    for idx, content in enumerate(raw_articles, start=1):
        words = content.split()
        snippet = extract_title_or_snippet(content)
        indexed_articles.append({
            "original_index": idx,
            "content": content,
            "char_count": len(content),
            "word_count": len(words),
            "snippet": snippet
        })

    # Xáo bài ngẫu nhiên (Step 1: Shuffle)
    shuffled_articles = list(indexed_articles)
    rng.shuffle(shuffled_articles)

    manifest_records = []
    for s_idx, art in enumerate(shuffled_articles, start=1):
        shuffled_code = f"BAI_{s_idx:02d}"
        file_name = f"bai_{s_idx:02d}.md"
        file_path = shuffled_dir / file_name

        # Ghi bài viết riêng biệt (Blind file - không lộ original_index cho người chấm)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {shuffled_code}\n\n")
            f.write(f"> **Mã ẩn danh:** `{shuffled_code}` | **Số chữ:** ~{art['word_count']} từ | **Ký tự:** {art['char_count']}\n\n")
            f.write(art["content"])
            f.write("\n")

        manifest_records.append({
            "shuffled_id": s_idx,
            "shuffled_code": shuffled_code,
            "file_name": file_name,
            "original_index": art["original_index"],
            "snippet": art["snippet"],
            "word_count": art["word_count"],
            "char_count": art["char_count"]
        })

    manifest = {
        "created_at": datetime.now().isoformat(),
        "seed": seed,
        "total_articles": len(manifest_records),
        "input_source": str(input_path),
        "articles": manifest_records
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"=== [B1 XÁO BÀI HOÀN TẤT] ===")
    print(f"Tổng số bài nhận diện: {len(manifest_records)}")
    print(f"Random Seed: {seed}")
    print(f"File cấu hình manifest: {manifest_path}")
    print(f"Thư mục bài viết đã xáo: {shuffled_dir}")
    print(f"Thư mục sẵn sàng chấm điểm: {scores_dir}")

if __name__ == "__main__":
    main()
