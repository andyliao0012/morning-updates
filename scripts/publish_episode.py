#!/usr/bin/env python3
"""Add an episode to a show's podcast feed and rebuild the site.

Usage:
    python3 scripts/publish_episode.py --show tech-unzip --date 2026-11-27 \
        --title "Thu 27 Nov · Headline one, headline two" \
        --summary "One or two sentences about the episode." \
        --mp3 "/tmp/ep/Tech Unzip - Thu 27 Nov 2026.mp3" \
        [--link https://claude.ai/artifact/...#tab]

Then commit and push. Rebuild only (no new episode): --rebuild
Keeps the newest KEEP episodes per show; older MP3s are removed from the site.
"""
import argparse
import datetime as dt
import email.utils
import html
import json
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://andyliao0012.github.io/morning-updates"
KEEP = 20

SHOWS = {
    "tech-unzip": {
        "title": "Tech Unzip",
        "author": "Andy Liao",
        "description": (
            "A 30-minute daily tech briefing for your walk, commute or school run. "
            "Hosts Ryan and Heart cover the day's biggest stories in AI, big data, chips, e-commerce and product design, "
            "then unzip them: what to remember, how it changes society and work, and one concept explained simply. "
            "New every weekday, never repeating what you've already heard."),
        "category": "Technology",
    },
    "eclectic-learning": {
        "title": "Eclectic Learning",
        "author": "Andy Liao",
        "description": (
            "A 30-minute daily dose of 雜學 — learning broadly across unrelated fields. "
            "Hosts Ryan and Heart explore three fresh ideas from design, psychology, science, history, culture and more, "
            "each with a line to remember and a dot to connect. New every weekday."),
        "category": "Education",
    },
}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def duration(path):
    try:
        return int(float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])))
    except ValueError:
        return 0


def hms(sec):
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def load(show):
    p = os.path.join(ROOT, show, "episodes.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


def save(show, eps):
    json.dump(eps, open(os.path.join(ROOT, show, "episodes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def pubdate(date_str):
    d = dt.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=7, minute=0, tzinfo=dt.timezone(dt.timedelta(hours=8)))
    return email.utils.format_datetime(d)


def build_feed(show, eps):
    s = SHOWS[show]
    e = html.escape
    items = []
    for ep in eps:
        url = f"{BASE}/{show}/episodes/{ep['file']}"
        link = ep.get("link") or f"{BASE}/"
        items.append(f"""    <item>
      <title>{e(ep['title'])}</title>
      <description>{e(ep['summary'])}</description>
      <itunes:summary>{e(ep['summary'])}</itunes:summary>
      <link>{e(link)}</link>
      <guid isPermaLink="false">{show}-{ep['date']}{ep.get('suffix', '')}</guid>
      <pubDate>{pubdate(ep['date'])}</pubDate>
      <enclosure url="{e(url)}" length="{ep['bytes']}" type="audio/mpeg"/>
      <itunes:duration>{hms(ep['seconds'])}</itunes:duration>
      <itunes:episodeType>{ep.get('type', 'full')}</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{e(s['title'])}</title>
    <link>{BASE}/</link>
    <atom:link href="{BASE}/{show}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>en-us</language>
    <description>{e(s['description'])}</description>
    <itunes:summary>{e(s['description'])}</itunes:summary>
    <itunes:author>{e(s['author'])}</itunes:author>
    <itunes:owner><itunes:name>{e(s['author'])}</itunes:name></itunes:owner>
    <itunes:image href="{BASE}/{show}/cover.jpg"/>
    <image><url>{BASE}/{show}/cover.jpg</url><title>{e(s['title'])}</title><link>{BASE}/</link></image>
    <itunes:category text="{s['category']}"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{chr(10).join(items)}
  </channel>
</rss>
"""
    open(os.path.join(ROOT, show, "feed.xml"), "w", encoding="utf-8").write(feed)


def build_index():
    e = html.escape
    blocks = []
    for show, s in SHOWS.items():
        eps = load(show)
        feed = f"{BASE}/{show}/feed.xml"
        rows = "\n".join(
            f'<li><div class="t">{e(ep["title"])}</div>'
            f'<audio controls preload="none" src="{show}/episodes/{e(ep["file"])}"></audio>'
            f'<div class="m">{e(ep["summary"])}</div></li>' for ep in eps) or "<li>First episode coming soon.</li>"
        blocks.append(f"""<section>
<img src="{show}/cover.jpg" alt="{e(s['title'])} cover" class="cover">
<h2>{e(s['title'])}</h2>
<p>{e(s['description'])}</p>
<p class="feed"><b>Subscribe:</b> copy this feed link into your podcast app
(Apple Podcasts: Library → ⋯ → Follow a Show by URL · Pocket Casts / Overcast: Add by URL)</p>
<p><code>{feed}</code> <button onclick="navigator.clipboard.writeText('{feed}');this.textContent='Copied'">Copy</button></p>
<h3>Latest episodes</h3>
<ul>{rows}</ul>
</section>""")
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Morning Updates — Tech Unzip &amp; Eclectic Learning</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Inter",Segoe UI,sans-serif;max-width:760px;margin:0 auto;padding:24px 18px 60px;color:#1d1d1f;background:#faf8f5;line-height:1.5}}
h1{{font-size:28px;margin:8px 0 4px}} .lead{{color:#555;margin-bottom:28px}}
section{{background:#fff;border-radius:16px;padding:20px;margin:22px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.cover{{width:120px;height:120px;border-radius:12px;float:right;margin:0 0 10px 14px}}
h2{{margin:4px 0 6px}} code{{font-size:13px;background:#f1eee9;padding:4px 6px;border-radius:6px;word-break:break-all}}
button{{border:0;background:#1d1d1f;color:#fff;border-radius:8px;padding:5px 10px;font-size:13px}}
ul{{list-style:none;padding:0}} li{{border-top:1px solid #eee;padding:12px 0}} .t{{font-weight:600}}
.m{{color:#666;font-size:14px}} audio{{width:100%;margin:6px 0}} .feed{{font-size:14px;color:#444}}
</style></head><body>
<h1>Morning Updates</h1>
<p class="lead">Two free daily shows to listen to on the move — on the way to work, school, or back from drop-off. New episodes every weekday morning (Taipei time).</p>
{''.join(blocks)}
<p style="color:#888;font-size:13px">Episodes are written and voiced with AI from public reporting, in our own words. Always check important facts with the original sources.</p>
</body></html>
"""
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", choices=SHOWS)
    ap.add_argument("--date")
    ap.add_argument("--title")
    ap.add_argument("--summary", default="")
    ap.add_argument("--mp3")
    ap.add_argument("--link")
    ap.add_argument("--type", default="full", choices=["full", "trailer", "bonus"])
    ap.add_argument("--suffix", default="", help="extra id when two episodes share a date")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()

    if not a.rebuild:
        show = a.show
        os.makedirs(os.path.join(ROOT, show, "episodes"), exist_ok=True)
        fname = f"{a.date}{a.suffix}.mp3"
        dst = os.path.join(ROOT, show, "episodes", fname)
        shutil.copyfile(a.mp3, dst)
        eps = [x for x in load(show) if x["file"] != fname]
        eps.append({"date": a.date, "suffix": a.suffix, "file": fname, "title": a.title, "summary": a.summary,
                    "link": a.link, "type": a.type, "bytes": os.path.getsize(dst), "seconds": duration(dst)})
        eps.sort(key=lambda x: (x["date"], x.get("suffix", "")), reverse=True)
        for old in eps[KEEP:]:
            p = os.path.join(ROOT, show, "episodes", old["file"])
            if os.path.exists(p):
                os.remove(p)
        save(show, eps[:KEEP])

    for show in SHOWS:
        os.makedirs(os.path.join(ROOT, show), exist_ok=True)
        build_feed(show, load(show))
    build_index()
    print("ok")


if __name__ == "__main__":
    main()
