#!/usr/bin/env python3
"""
cut_hls_scene.py - Selective HLS Segment Downloader and Video Cutter

Downloads only the necessary .ts segments from an HLS (.m3u8) playlist
covering the requested time range, merges them, and cuts an optimized MP4
video under a specified target file size (default: < 5MB).
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

def parse_time(t_str):
    """Parse MM:SS or seconds float/int."""
    if ':' in str(t_str):
        parts = str(t_str).split(':')
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return float(t_str)

def get_ffmpeg():
    """Locate ffmpeg or use static_ffmpeg."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return 'ffmpeg'
    except Exception:
        pass
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        return 'ffmpeg'
    except Exception:
        pass
    for path in ['/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/usr/bin/ffmpeg']:
        if os.path.exists(path):
            return path
    raise RuntimeError("FFmpeg not found. Please install ffmpeg or static-ffmpeg.")

def fetch_m3u8_segments(m3u8_url, headers):
    """Fetch m3u8 playlist and resolve segments with time offsets."""
    req = urllib.request.Request(m3u8_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        lines = r.read().decode('utf-8', errors='ignore').splitlines()

    # Check if master playlist
    sub_playlists = [line.strip() for line in lines if line.strip() and not line.startswith('#') and line.endswith('.m3u8')]
    if sub_playlists:
        # Pick the highest quality stream (usually the first or last)
        from urllib.parse import urljoin
        best_playlist = urljoin(m3u8_url, sub_playlists[-1])
        print(f"Master playlist detected. Following: {best_playlist}")
        return fetch_m3u8_segments(best_playlist, headers)

    from urllib.parse import urljoin
    total_time = 0.0
    segments = []
    current_duration = 0.0

    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:'):
            match = re.search(r'#EXTINF:([\d\.]+)', line)
            if match:
                current_duration = float(match.group(1))
        elif line and not line.startswith('#'):
            start_t = total_time
            end_t = total_time + current_duration
            seg_full_url = urljoin(m3u8_url, line)
            segments.append({
                'start': start_t,
                'end': end_t,
                'duration': current_duration,
                'url': seg_full_url
            })
            total_time = end_t

    return segments

def main():
    parser = argparse.ArgumentParser(description="Cut a scene from an HLS stream.")
    parser.add_argument("--m3u8", required=True, help="URL to the m3u8 playlist")
    parser.add_argument("--start", required=True, help="Start time in seconds or MM:SS")
    parser.add_argument("--end", help="End time in seconds or MM:SS")
    parser.add_argument("--duration", help="Duration in seconds")
    parser.add_argument("--output", required=True, help="Path to output .mp4 file")
    parser.add_argument("--max-mb", type=float, default=4.8, help="Max file size in MB (default: 4.8MB)")
    parser.add_argument("--scale", default="1280:720", help="Resolution scaling (e.g. 1280:720 or 1920:1080)")

    args = parser.parse_args()

    start_sec = parse_time(args.start)
    if args.end:
        end_sec = parse_time(args.end)
        clip_duration = end_sec - start_sec
    elif args.duration:
        clip_duration = float(args.duration)
        end_sec = start_sec + clip_duration
    else:
        raise ValueError("Must specify either --end or --duration")

    if clip_duration <= 0:
        raise ValueError("Invalid duration or end time must be greater than start time.")

    ffmpeg_bin = get_ffmpeg()

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    print(f"Fetching playlist: {args.m3u8}...")
    segments = fetch_m3u8_segments(args.m3u8, headers)
    if not segments:
        print("No segments found in m3u8 playlist.", file=sys.stderr)
        sys.exit(1)

    print(f"Total video length: {segments[-1]['end']/60:.2f} mins ({segments[-1]['end']:.1f}s)")
    print(f"Requested cut range: {start_sec:.1f}s -> {end_sec:.1f}s ({clip_duration:.1f}s)")

    # Add a 5s safety margin around the cut range
    margin = 5.0
    fetch_start = max(0.0, start_sec - margin)
    fetch_end = end_sec + margin

    matched_segs = [s for s in segments if s['end'] >= fetch_start and s['start'] <= fetch_end]
    if not matched_segs:
        print("No segments found for the requested time range.", file=sys.stderr)
        sys.exit(1)

    print(f"Downloading {len(matched_segs)} segments ({matched_segs[0]['start']:.1f}s to {matched_segs[-1]['end']:.1f}s)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_ts_path = os.path.join(tmpdir, "raw_merged.ts")
        with open(raw_ts_path, 'wb') as outfile:
            for i, seg in enumerate(matched_segs):
                req = urllib.request.Request(seg['url'], headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    outfile.write(resp.read())

        # Exact offset within the downloaded concatenated file
        first_seg_start = matched_segs[0]['start']
        rel_start = max(0.0, start_sec - first_seg_start)

        # Calculate bitrate for target file size
        # target_bits = max_mb * 8 * 1024 * 1024
        # total_bitrate = target_bits / clip_duration
        target_kbits = args.max_mb * 8 * 1024
        total_kbps = target_kbits / clip_duration
        audio_kbps = 128
        video_kbps = max(250, int(total_kbps - audio_kbps))

        print(f"Encoding output: relative start {rel_start:.2f}s, duration {clip_duration:.2f}s, target video bitrate ~{video_kbps}kbps...")

        cmd = [
            ffmpeg_bin, '-y',
            '-ss', str(rel_start),
            '-i', raw_ts_path,
            '-t', str(clip_duration),
            '-vf', f'scale={args.scale}',
            '-c:v', 'libx264',
            '-b:v', f'{video_kbps}k',
            '-maxrate', f'{int(video_kbps * 1.3)}k',
            '-bufsize', f'{int(video_kbps * 2)}k',
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', f'{audio_kbps}k',
            args.output
        ]

        subprocess.run(cmd, check=True)

        final_size_mb = os.path.getsize(args.output) / (1024 * 1024)
        print(f"Successfully generated: {args.output} ({final_size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
