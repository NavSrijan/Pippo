from datetime import datetime, timezone
from pathlib import Path
import discord
from zoneinfo import ZoneInfo
import pickle as pkl
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import re


def load(filename):
    with open(filename, "rb") as f:
        return pkl.load(f)


def save(obj, filename):
    with open(filename, "wb") as f:
        pkl.dump(obj, f)


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


def utc_to_ist(utc_dt):
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(ZoneInfo("Asia/Kolkata"))


def download_and_return_image(url, filename="emojiSuggestion.png") -> discord.File:
    response = requests.get(url, stream=True, timeout=10)
    response.raise_for_status()
    im = Image.open(response.raw).convert('RGBA')
    with BytesIO() as image_binary:
        im.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename=filename)
    return file

class MorseCode():

    def __init__(self):
        self.data = {
            'a': '.-',
            'b': '-...',
            'c': '-.-.',
            'd': '-..',
            'e': '.',
            'f': '..-.',
            'g': '--.',
            'h': '....',
            'i': '..',
            'j': '.---',
            'k': '-.-',
            'l': '.-..',
            'm': '--',
            'n': '-.',
            'o': '---',
            'p': '.--.',
            'q': '--.-',
            'r': '.-.',
            's': '...',
            't': '-',
            'u': '..-',
            'v': '...-',
            'w': '.--',
            'x': '-..-',
            'y': '-.--',
            'z': '--..',
            ' ': '/',
            '0': '-----',
            '1': '.----',
            '2': '..---',
            '3': '...--',
            '4': '....-',
            '5': '.....',
            '6': '-....',
            '7': '--...',
            '8': '---..',
            '9': '----.',
            '.': '.-.-.-',
            ',': '--..--',
            ':': '---...',
            '?': '..--..',
            "'": '.----.',
            '/': '-..-.',
            '(': '-.--.',
            ')': '-.--.-',
            '"': '.-..-.',
            '': ''
        }

    def encrypt(self, text):
        ll = list(text.lower())
        final = ""
        for i in ll:
            try:
                final += self.data[i] + " "
            except:
                final += " "
        return final

    def decrypt(self, text):
        ll = text.lower().split("/")
        for i, j in enumerate(ll):
            ll[i] = j.split(" ")
        final = ""
        data = dict((v,k) for k,v in self.data.items())
        for i in ll:
            word = ""
            for j in i:
                try:
                    word+= data[j]
                except:
                    word+= " "
            final+=word+" "
        return final

def write_text_on_image(image_path, text, font_list=None, color_list=None, start_location=None, underscore_color=None):
    """Add a legible, high-contrast movie mask below the untouched game art."""
    with Image.open(image_path) as source:
        artwork = source.convert("RGB")
    artwork.thumbnail((1200, 800), Image.Resampling.LANCZOS)
    width, height = artwork.size
    panel_height = max(184, width // 6)
    canvas = Image.new("RGB", (width, height + panel_height), (255, 249, 235))
    canvas.paste(artwork, (0, 0))

    panel_margin = max(20, width // 40)
    panel = (panel_margin, height + 12, width - panel_margin, height + panel_height - 12)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(panel, radius=max(16, width // 48), fill=(27, 37, 58), outline=(232, 183, 91), width=3)

    font_candidates = [
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        str(Path(__file__).resolve().parent / "darling_coffee.ttf"),
    ]
    font_path = next((candidate for candidate in font_candidates if Path(candidate).is_file()), None)
    text = " ".join(str(text or "").replace("\u200e", "").split())
    max_width = width - 2 * panel_margin - 36
    max_text_height = panel_height - 42

    def load_font(size):
        try:
            return ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except OSError:
            return ImageFont.load_default()

    def wrap(font):
        words = text.split()
        lines = []
        line = ""
        for word in words:
            if draw.textbbox((0, 0), word, font=font)[2] > max_width:
                if line:
                    lines.append(line)
                    line = ""
                fragment = ""
                for char in word:
                    candidate = fragment + char
                    if fragment and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
                        lines.append(fragment)
                        fragment = char
                    else:
                        fragment = candidate
                if fragment:
                    lines.append(fragment)
                continue
            candidate = f"{line} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                line = candidate
            elif line:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    font = None
    lines = []
    line_height = 0
    for size in range(max(30, min(62, width // 18)), 23, -2):
        candidate_font = load_font(size)
        candidate_lines = wrap(candidate_font)
        candidate_height = draw.textbbox((0, 0), "Ag", font=candidate_font)[3] + 8
        if len(candidate_lines) <= 3 and candidate_height * len(candidate_lines) <= max_text_height:
            font, lines, line_height = candidate_font, candidate_lines, candidate_height
            break
    if font is None:
        font = load_font(22)
        lines = wrap(font)[:3]
        line_height = draw.textbbox((0, 0), "Ag", font=font)[3] + 6

    total_height = len(lines) * line_height
    y = height + (panel_height - total_height) // 2
    for line in lines:
        line_width = draw.textbbox((0, 0), line, font=font)[2]
        x = (width - line_width) // 2
        for char in line:
            color = (246, 193, 92) if char == "_" else (255, 248, 231)
            draw.text((x, y), char, font=font, fill=color)
            x += draw.textlength(char, font=font)
        y += line_height

    with BytesIO() as output:
        canvas.save(output, format="JPEG", optimize=True, quality=88)
        output.seek(0)
        return discord.File(output, filename="boll.jpg")


def write_caption_on_image(image_path, title, subtitle="", filename="pippo_art.jpg"):
    """Append a readable caption card without covering the illustration."""
    with Image.open(image_path) as source:
        artwork = source.convert("RGB")
    artwork.thumbnail((1200, 800), Image.Resampling.LANCZOS)
    width, art_height = artwork.size

    font_candidates = [
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        str(Path(__file__).resolve().parent / "darling_coffee.ttf"),
    ]

    def load_font(size):
        for font_path in font_candidates:
            if Path(font_path).is_file():
                try:
                    return ImageFont.truetype(font_path, size=size)
                except OSError:
                    continue
        return ImageFont.load_default()

    title_text = " ".join(str(title or "Pippo").split())[:72]
    subtitle_text = " ".join(str(subtitle or "").split())
    subtitle_text = re.sub(r"<@!?\d+>|<@&\d+>|@everyone|@here", "", subtitle_text, flags=re.IGNORECASE)[:112]
    subtitle_text = re.sub(r"[*_`~#]", "", subtitle_text)
    title_text = "".join(ch for ch in title_text if ord(ch) >= 32 and ord(ch) not in range(0x1F000, 0x1FB00))
    subtitle_text = "".join(ch for ch in subtitle_text if ord(ch) >= 32 and ord(ch) not in range(0x1F000, 0x1FB00))

    canvas_width = width
    text_padding = max(24, width // 24)
    max_text_width = width - 2 * text_padding
    title_size = max(25, min(50, width // 22))
    subtitle_size = max(17, min(26, width // 42))

    def wrap(text, font):
        if not text:
            return []
        lines = []
        current = ""
        for word in text.split():
            if draw_measure(word, font) > max_text_width:
                if current:
                    lines.append(current)
                    current = ""
                fragment = ""
                for char in word:
                    candidate = fragment + char
                    if fragment and draw_measure(candidate, font) > max_text_width:
                        lines.append(fragment)
                        fragment = char
                    else:
                        fragment = candidate
                if fragment:
                    lines.append(fragment)
                continue
            candidate = f"{current} {word}".strip()
            if draw_measure(candidate, font) <= max_text_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # Use a temporary draw object only for font measurement; captions are drawn
    # after the new canvas is created below.
    draw_measure_image = Image.new("RGB", (1, 1))
    measure_draw = ImageDraw.Draw(draw_measure_image)

    def draw_measure(text, font):
        return measure_draw.textbbox((0, 0), text, font=font)[2]

    title_font = load_font(title_size)
    title_lines = wrap(title_text, title_font)
    while len(title_lines) > 2 and title_size > 22:
        title_size -= 2
        title_font = load_font(title_size)
        title_lines = wrap(title_text, title_font)

    subtitle_font = load_font(subtitle_size)
    subtitle_lines = wrap(subtitle_text, subtitle_font)
    while len(subtitle_lines) > 4 and subtitle_size > 15:
        subtitle_size -= 1
        subtitle_font = load_font(subtitle_size)
        subtitle_lines = wrap(subtitle_text, subtitle_font)

    title_line_height = measure_draw.textbbox((0, 0), "Ag", font=title_font)[3] + 4
    subtitle_line_height = measure_draw.textbbox((0, 0), "Ag", font=subtitle_font)[3] + 4
    gap = 8 if subtitle_lines else 0
    vertical_padding = max(24, width // 40)
    panel_height = max(
        112,
        vertical_padding * 2
        + len(title_lines) * title_line_height
        + gap
        + len(subtitle_lines) * subtitle_line_height,
    )
    image = Image.new("RGB", (canvas_width, art_height + panel_height), (255, 249, 235))
    image.paste(artwork, (0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(14, width // 36)
    panel = (margin, art_height + 8, width - margin, art_height + panel_height - 8)
    draw.rounded_rectangle(panel, radius=max(14, width // 64), fill=(24, 17, 49), outline=(232, 183, 91), width=3)
    y = art_height + (panel_height - (len(title_lines) * title_line_height + gap + len(subtitle_lines) * subtitle_line_height)) // 2
    for line in title_lines:
        line_width = draw_measure(line, title_font)
        draw.text(((width - line_width) // 2, y), line, font=title_font, fill=(255, 247, 225))
        y += title_line_height
    y += gap
    for line in subtitle_lines:
        line_width = draw_measure(line, subtitle_font)
        draw.text(((width - line_width) // 2, y), line, font=subtitle_font, fill=(222, 235, 255))
        y += subtitle_line_height

    output = BytesIO()
    image.save(output, format="JPEG", optimize=True, quality=88)
    output.seek(0)
    return discord.File(output, filename=filename)
