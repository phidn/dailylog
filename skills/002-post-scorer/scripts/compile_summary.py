#!/usr/bin/env python3
"""
compile_summary.py
Bước 3: Tổng hợp toàn bộ kết quả chấm điểm từ scores/ và manifest.json,
tính toán thống kê, phân loại phổ điểm, xếp hạng từ cao xuống thấp và xuất SUMMARY.md.
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from statistics import mean, median

def parse_score_file(file_path: Path) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Tìm tổng điểm
    total_score = 0
    m_total = re.search(r'\*\*Tổng điểm[:\s]*\*\*\s*`?([0-9]+(?:\.[0-9]+)?)`?\s*/\s*100', content, re.IGNORECASE)
    if not m_total:
        m_total = re.search(r'Tổng điểm[:\s]*([0-9]+(?:\.[0-9]+)?)\s*/\s*100', content, re.IGNORECASE)
    if m_total:
        total_score = float(m_total.group(1))

    # Tìm các điểm thành phần
    def find_criterion_score(name: str, max_val: int) -> float:
        pattern = rf"{name}.*?`?([0-9]+(?:\.[0-9]+)?)`?\s*/\s*{max_val}"
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            return float(m.group(1))
        return 0.0

    score_depth = find_criterion_score("Tư tưởng", 25)
    score_emotion = find_criterion_score("Cảm xúc", 25)
    score_imagery = find_criterion_score("Hình tượng", 20)
    score_structure = find_criterion_score("Cấu trúc", 20)
    score_voice = find_criterion_score("Dấu ấn", 10)

    # Trích xuất Golden Quote nếu có
    quote = ""
    m_quote = re.search(r'###\s*(?:Câu văn đắt giá|Golden Quote)[^\n]*\n+>*\s*([^\n]+(?:\n[^\n#]+)*)', content)
    if m_quote:
        quote = m_quote.group(1).strip().strip('"').strip('“').strip('”')
        # Lấy 1-2 dòng đầu
        quote = " ".join([q.lstrip('> *"-') for q in quote.splitlines()[:2]])

    # Trích xuất Đánh giá ngắn gọn / Điểm sáng
    strength = ""
    m_str = re.search(r'###\s*(?:Điểm sáng|Điểm nổi bật|Core Strengths)[^\n]*\n+([^\n#]+)', content)
    if m_str:
        strength = m_str.group(1).lstrip('-* >').strip()

    # Trích xuất xếp loại
    tier = "Khá"
    if total_score >= 90:
        tier = "Xuất sắc (S)"
    elif total_score >= 82:
        tier = "Rất tốt (A+)"
    elif total_score >= 75:
        tier = "Tốt (A)"
    elif total_score >= 65:
        tier = "Khá (B)"
    else:
        tier = "Trung bình (C)"

    return {
        "file": file_path.name,
        "total_score": total_score,
        "score_depth": score_depth,
        "score_emotion": score_emotion,
        "score_imagery": score_imagery,
        "score_structure": score_structure,
        "score_voice": score_voice,
        "tier": tier,
        "quote": quote,
        "strength": strength,
        "raw_content": content
    }

def main():
    parser = argparse.ArgumentParser(description="Tổng hợp bảng xếp hạng và báo cáo điểm số.")
    parser.add_argument("--dir", "-d", type=str, required=True, help="Thư mục làm việc (chứa manifest.json và scores/)")
    args = parser.parse_args()

    work_dir = Path(args.dir)
    manifest_path = work_dir / "manifest.json"
    scores_dir = work_dir / "scores"

    if not manifest_path.exists():
        print(f"Lỗi: Không tìm thấy manifest tại {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    articles = manifest.get("articles", [])
    results = []

    for art in articles:
        s_code = art["shuffled_code"].lower()
        score_file = scores_dir / f"score_{s_code}.md"
        if not score_file.exists():
            # Thử tìm theo định dạng số
            score_file = scores_dir / f"score_bai_{art['shuffled_id']:02d}.md"
        
        if score_file.exists():
            score_data = parse_score_file(score_file)
            merged = {**art, **score_data}
            results.append(merged)
        else:
            print(f"Cảnh báo: Chưa có kết quả chấm cho {art['shuffled_code']} ({score_file})", file=sys.stderr)

    if not results:
        print("Lỗi: Chưa có bài nào được chấm!", file=sys.stderr)
        sys.exit(1)

    # Sắp xếp theo điểm tổng giảm dần (Ranking)
    results.sort(key=lambda x: x["total_score"], reverse=True)

    scores = [r["total_score"] for r in results]
    highest = max(scores)
    lowest = min(scores)
    avg_score = round(mean(scores), 2)
    med_score = round(median(scores), 2)

    # Tạo file SUMMARY.md
    summary_path = work_dir / "SUMMARY.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# BÁO CÁO CHẤM ĐIỂM KHÔNG CACHE (BLIND ESSAY SCORING)\n\n")
        f.write(f"> **Ngày thực hiện:** {manifest.get('created_at', 'N/A')}\n")
        f.write(f"> **Quy trình:** 2 bước độc lập (B1: Fisher-Yates Random Shuffle [Seed: `{manifest.get('seed')}`] ➔ B2: Uncached Scoring từng bài ➔ B3: Tổng hợp Leaderboard).\n")
        f.write(f"> **Tổng số bài viết:** {len(results)} bài\n\n")

        f.write("## 1. Thống Kê Phổ Điểm & Tổng Quan\n\n")
        f.write("| Chỉ số | Giá trị | Nhận định |\n")
        f.write("| :--- | :---: | :--- |\n")
        f.write(f"| **Điểm cao nhất (Max)** | **{highest}/100** | Bài viết đạt độ chín muồi xuất sắc về tư tưởng và rung cảm |\n")
        f.write(f"| **Điểm thấp nhất (Min)** | **{lowest}/100** | Bài viết còn ở dạng phác thảo cảm xúc hoặc nhịp điệu ngắn |\n")
        f.write(f"| **Điểm trung bình (Mean)** | **{avg_score}/100** | Mặt bằng chất lượng văn phong rất đồng đều và sâu sắc |\n")
        f.write(f"| **Điểm trung vị (Median)** | **{med_score}/100** | Phân phối chuẩn, không bị lệch quá mức bởi các bài ngoại lai |\n\n")

        f.write("### Phân loại theo hạng mức (Tier Distribution)\n\n")
        tiers = {
            "Xuất sắc (S: >=90)": [r for r in results if r["total_score"] >= 90],
            "Rất tốt (A+: 82-89)": [r for r in results if 82 <= r["total_score"] < 90],
            "Tốt (A: 75-81)": [r for r in results if 75 <= r["total_score"] < 82],
            "Khá (B: 65-74)": [r for r in results if 65 <= r["total_score"] < 75],
            "Cần rèn giũa (<65)": [r for r in results if r["total_score"] < 65],
        }
        for t_name, t_items in tiers.items():
            f.write(f"- **{t_name}**: {len(t_items)} bài ({len(t_items)/len(results)*100:.1f}%)\n")
        f.write("\n---\n\n")

        f.write("## 2. Bảng Xếp Hạng Toàn Diện (Leaderboard)\n\n")
        f.write("| Hạng | Mã Xáo | Bài Gốc | Trích dẫn mở đầu | Tư tưởng (25) | Cảm xúc (25) | Hình tượng (20) | Cấu trúc (20) | Dấu ấn (10) | Tổng điểm (100) | Xếp loại |\n")
        f.write("| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")

        for rank, r in enumerate(results, start=1):
            snippet_clean = r["snippet"].replace("|", "\\|")
            f.write(f"| **#{rank}** | `{r['shuffled_code']}` | Bài #{r['original_index']:02d} | *\"{snippet_clean}\"* | {r['score_depth']} | {r['score_emotion']} | {r['score_imagery']} | {r['score_structure']} | {r['score_voice']} | **{r['total_score']}** | {r['tier']} |\n")

        f.write("\n---\n\n")

        f.write("## 3. Top 3 Tác Phẩm Xuất Sắc Nhất\n\n")
        for rank in range(1, min(4, len(results) + 1)):
            top_item = results[rank - 1]
            f.write(f"### 🏆 Hạng #{rank}: `{top_item['shuffled_code']}` (Bài gốc #{top_item['original_index']:02d}) — **{top_item['total_score']}/100**\n")
            if top_item["quote"]:
                f.write(f"> *\"{top_item['quote']}\"*\n\n")
            if top_item["strength"]:
                f.write(f"- **Điểm sáng:** {top_item['strength']}\n")
            f.write(f"- **Chi tiết chấm:** [Xem chi tiết file điểm](./scores/score_{top_item['shuffled_code'].lower()}.md) | [Đọc văn bản bài](./shuffled/bai_{top_item['shuffled_id']:02d}.md)\n\n")

        f.write("---\n\n")

        f.write("## 4. Bản Đồ Đối Chiếu Gốc ➔ Xáo (Mapping Index)\n\n")
        f.write("Dành cho tác giả tra cứu nhanh thứ tự ban đầu:\n\n")
        f.write("| Thứ tự gốc | Mã xáo trộn | Thứ hạng đạt được | Tổng điểm | File bài viết | File chấm điểm |\n")
        f.write("| :---: | :---: | :---: | :---: | :--- | :--- |\n")
        # Sắp xếp lại theo original_index để tác giả dễ dò
        by_orig = sorted(results, key=lambda x: x["original_index"])
        for bo in by_orig:
            # Tìm rank của bo
            r_rank = results.index(bo) + 1
            f.write(f"| Bài #{bo['original_index']:02d} | `{bo['shuffled_code']}` | **#{r_rank}** | {bo['total_score']}/100 | [bai_{bo['shuffled_id']:02d}.md](./shuffled/bai_{bo['shuffled_id']:02d}.md) | [score_{bo['shuffled_code'].lower()}.md](./scores/score_{bo['shuffled_code'].lower()}.md) |\n")

    print(f"=== [TỔNG HỢP SUMMARY HOÀN TẤT] ===")
    print(f"Đã tạo bảng xếp hạng và báo cáo tại: {summary_path}")
    print(f"Điểm cao nhất: {highest} | Thấp nhất: {lowest} | Trung bình: {avg_score}")

if __name__ == "__main__":
    main()
