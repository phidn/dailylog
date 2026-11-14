# DailyLog

Kho lưu trữ ghi lại các kỹ năng (skills), quy trình tự động hóa (workflows) và công cụ phục vụ công việc hàng ngày trong hệ sinh thái Antigravity.

## Danh sách Skills

| Mã | Tên Skill | Mô tả | Happy Output |
| :--- | :--- | :--- | :--- |
| **001** | [`001-movie-scene-cutter`](./skills/001-movie-scene-cutter/SKILL.md) | Trích xuất và cắt video hội thoại đắt giá từ link trang xem phim trực tuyến (Motchill, HLS/m3u8). | File `.mp4` bản trọn vẹn cảm xúc (~58s) được nén tối ưu **< 5MB** để tiện chia sẻ/upload. |
| **002** | [`002-post-scorer`](./skills/002-post-scorer/SKILL.md) | Chấm điểm bài viết / tản văn / post không cache: B1 xáo bài ngẫu nhiên (Blind Shuffle), B2 chấm điểm độc lập từng bài theo Rubric 100 điểm. | Bộ file chấm điểm độc lập, file bài viết ẩn danh, bảng xếp hạng Leaderboard & phân tích phổ điểm tại `tmp/yyyymmdd-[name]/...`. |

---

## Cấu trúc thư mục

```
dailylog/
├── .agents/
│   └── skills/
│       ├── 001-movie-scene-cutter -> ../../skills/001-movie-scene-cutter
│       └── 002-post-scorer -> ../../skills/002-post-scorer
├── skills/
│   ├── 001-movie-scene-cutter/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── cut_hls_scene.py
│   │       └── ocr_frames.swift
│   └── 002-post-scorer/
│       ├── SKILL.md
│       └── scripts/
│           ├── shuffle_and_split.py
│           └── compile_summary.py
└── README.md
```
