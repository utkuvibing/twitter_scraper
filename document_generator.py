"""
Document Generator - Tweetleri çeşitli formatlarda kaydet
Desteklenen formatlar: .docx, .json, .md
"""

import json
import os
from typing import List, Optional
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE


# Base output dizini
BASE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def get_output_path(
    target_username: str, filename: str, output_dir: Optional[str] = None
) -> str:
    """
    Kullanıcıya özel output klasörü oluştur ve tam yol döndür

    Args:
        target_username: Hedef kullanıcı adı
        filename: Dosya adı
        output_dir: Özel output dizini (None ise default output kullanılır)

    Returns:
        Tam dosya yolu
    """
    # Eğer özel output dizini verildiyse onu kullan, yoksa default
    if output_dir and os.path.isdir(output_dir):
        base_dir = output_dir
    else:
        base_dir = BASE_OUTPUT_DIR

    # Kullanıcıya özel klasör oluştur
    user_output_dir = os.path.join(base_dir, target_username)
    os.makedirs(user_output_dir, exist_ok=True)

    # Sadece dosya adını al (path içeriyorsa)
    filename = os.path.basename(filename)

    return os.path.join(user_output_dir, filename)


def create_word_document(
    tweets: List,
    output_path: str,
    target_username: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Tweetleri Word document olarak kaydet

    Args:
        tweets: Tweet listesi (scraper.Tweet objeleri)
        output_path: Çıktı dosya yolu (.docx)
        target_username: Scrape edilen hesabın kullanıcı adı
        output_dir: Özel output dizini (None ise default output kullanılır)

    Returns:
        Kaydedilen dosya yolu
    """
    doc = Document()

    # Başlık stili
    title = doc.add_heading(f"@{target_username} - Tweet Arşivi", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Meta bilgi
    meta_para = doc.add_paragraph()
    meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_run = meta_para.add_run(
        f"Toplam {len(tweets)} tweet | Oluşturulma: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor(128, 128, 128)

    doc.add_paragraph()  # Boşluk

    # Tweetleri ekle (güncel'den eskiye - zaten bu sırada)
    for i, tweet in enumerate(tweets, 1):
        # Tweet numarası ve tarih
        header_para = doc.add_paragraph()
        header_run = header_para.add_run(f"Tweet #{i}")
        header_run.bold = True
        header_run.font.size = Pt(12)
        header_run.font.color.rgb = RGBColor(29, 155, 240)  # X mavi rengi

        date_run = header_para.add_run(f"  |  {tweet.date_str}")
        date_run.font.size = Pt(10)
        date_run.font.color.rgb = RGBColor(100, 100, 100)

        # Tweet metni
        if tweet.text:
            text_para = doc.add_paragraph()
            text_para.add_run(tweet.text)

        # Medya linkleri
        if tweet.media_urls:
            media_para = doc.add_paragraph()
            media_label = media_para.add_run("Medya: ")
            media_label.bold = True
            media_label.font.size = Pt(9)
            media_label.font.color.rgb = RGBColor(80, 80, 80)

            for j, url in enumerate(tweet.media_urls):
                if j > 0:
                    media_para.add_run(" | ")
                media_link = media_para.add_run(
                    url if len(url) < 80 else url[:77] + "..."
                )
                media_link.font.size = Pt(8)
                media_link.font.color.rgb = RGBColor(100, 100, 100)

        # Tweet URL
        url_para = doc.add_paragraph()
        url_label = url_para.add_run("Link: ")
        url_label.font.size = Pt(9)
        url_label.font.color.rgb = RGBColor(80, 80, 80)
        url_link = url_para.add_run(tweet.tweet_url)
        url_link.font.size = Pt(9)
        url_link.font.color.rgb = RGBColor(29, 155, 240)

        # Ayırıcı çizgi
        separator = doc.add_paragraph()
        sep_run = separator.add_run("─" * 60)
        sep_run.font.size = Pt(8)
        sep_run.font.color.rgb = RGBColor(200, 200, 200)

    # Dosyayı kaydet
    if not output_path.endswith(".docx"):
        output_path += ".docx"

    # Kullanıcıya özel output klasörüne kaydet (seçilen dizini kullan)
    full_path = get_output_path(target_username, output_path, output_dir)
    doc.save(full_path)
    print(f"Document kaydedildi: {full_path}")

    return full_path


def create_simple_document(
    tweets: List,
    output_path: str,
    target_username: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Basit formatta Word document oluştur (sadece metin ve tarih)

    Args:
        tweets: Tweet listesi
        output_path: Çıktı dosya yolu
        target_username: Kullanıcı adı
        output_dir: Özel output dizini (None ise default output kullanılır)

    Returns:
        Dosya yolu
    """
    doc = Document()

    doc.add_heading(f"@{target_username} Tweetleri", 0)
    doc.add_paragraph(f"Toplam: {len(tweets)} tweet")
    doc.add_paragraph()

    for i, tweet in enumerate(tweets, 1):
        para = doc.add_paragraph()
        para.add_run(f"[{i}] {tweet.date_str}\n").bold = True
        para.add_run(tweet.text or "[Metin yok - sadece medya]")
        para.add_run("\n")

    if not output_path.endswith(".docx"):
        output_path += ".docx"

    full_path = get_output_path(target_username, output_path, output_dir)
    doc.save(full_path)
    return full_path


def create_json_document(
    tweets: List,
    output_path: str,
    target_username: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Tweetleri JSON formatında kaydet (MCP-ready)

    Args:
        tweets: Tweet listesi
        output_path: Çıktı dosya yolu
        target_username: Kullanıcı adı
        output_dir: Özel output dizini (None ise default output kullanılır)

    Returns:
        Dosya yolu
    """
    data = {
        "source": "twitter",
        "user": f"@{target_username}",
        "scraped_at": datetime.now().isoformat(),
        "total_tweets": len(tweets),
        "tweets": [],
    }

    for tweet in tweets:
        tweet_data = {
            "id": tweet.id,
            "text": tweet.text,
            "date": tweet.date.isoformat() if tweet.date else None,
            "date_str": tweet.date_str,
            "url": tweet.tweet_url,
            "has_media": len(tweet.media_urls) > 0,
            "media_urls": tweet.media_urls,
            "has_article": getattr(tweet, "has_article", False),
        }
        data["tweets"].append(tweet_data)

    if not output_path.endswith(".json"):
        output_path += ".json"

    full_path = get_output_path(target_username, output_path, output_dir)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"JSON kaydedildi: {full_path}")
    return full_path


def create_markdown_document(
    tweets: List,
    output_path: str,
    target_username: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Tweetleri Markdown formatında kaydet

    Args:
        tweets: Tweet listesi
        output_path: Çıktı dosya yolu
        target_username: Kullanıcı adı
        output_dir: Özel output dizini (None ise default output kullanılır)

    Returns:
        Dosya yolu
    """
    lines = []
    lines.append(f"# @{target_username} - Tweet Arşivi\n")
    lines.append(f"**Toplam:** {len(tweets)} tweet\n")
    lines.append(f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
    lines.append("---\n")

    for i, tweet in enumerate(tweets, 1):
        lines.append(f"## Tweet #{i}\n")
        lines.append(f"**Tarih:** {tweet.date_str}\n")
        if tweet.text:
            lines.append(f"\n{tweet.text}\n")
        if tweet.media_urls:
            lines.append(f"\n**Medya:** {len(tweet.media_urls)} adet\n")
        lines.append(f"\n[Tweet Link]({tweet.tweet_url})\n")
        lines.append("\n---\n")

    if not output_path.endswith(".md"):
        output_path += ".md"

    full_path = get_output_path(target_username, output_path, output_dir)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Markdown kaydedildi: {full_path}")
    return full_path
