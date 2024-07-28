from datetime import datetime, timezone
import discord
from dateutil import tz
import pickle as pkl
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random


def load(filename):
    with open(filename, "rb") as f:
        return pkl.load(f)


def save(obj, filename):
    with open(filename, "wb") as f:
        pkl.dump(obj, f)


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


def utc_to_ist(utc_dt):
    from_zone = tz.tzutc()
    to_zone = tz.gettz("Asia/Kolkata")

    utc_dt = utc_dt.replace(tzinfo=from_zone)
    cc = utc_dt.astimezone(to_zone)

    return cc


def download_and_return_image(url, filename="emojiSuggestion.png") -> discord.File:
    im = Image.open(requests.get(url, stream=True).raw).convert('RGBA')
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

def write_text_on_image(image_path, text, font_list, color_list, start_location=(100, 100)):
    """
    Writes text on an image with a specified font and color at a given location.

    Parameters:
    - image_path: Path to the image file.
    - text: Text to write on the image.
    - font_list: List of font file paths.
    - color_list: List of color names or RGB tuples.
    - start_location: Tuple specifying the (x, y) start location for the text.
    """
    # Open the target image
    image = Image.open(image_path)
    image_width, image_height = image.size
    draw = ImageDraw.Draw(image)

    # Randomly pick a font and size
    font_path = random.choice(font_list)
    font_size = 80  # Starting font size, adjust as needed
    font = ImageFont.truetype(font_path, font_size)

    # Randomly pick a color for non-underscore characters
    color = random.choice(color_list)
    underscore_color = 'black'

    # Split text into words and underscores
    def custom_wrap(text, width):
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            if '_' in word:
                if current_line:
                    lines.append(current_line)
                    current_line = ""
                lines.append(word)
            else:
                if len(current_line + word) < width:
                    current_line += word + " "
                else:
                    lines.append(current_line)
                    current_line = word + " "
        if current_line:
            lines.append(current_line)
        return lines

    # Wrap text to fit image width
    max_lines = 3  # Adjust the number of lines as needed
    wrapped_text = custom_wrap(text, image_width // font_size)
    para = '\n'.join(wrapped_text)

    # Calculate the best font size to fit the specified number of lines
    while True:
        lines = custom_wrap(text, image_width // font_size)
        if len(lines) <= max_lines:
            break
        font_size -= 1  # Decrease font size and try again
        font = ImageFont.truetype(font_path, font_size)

    # Calculate line spacing and draw the text
    current_h, current_w = start_location
    line_spacing = 20  # Additional spacing between lines
    for line in lines:
        # Use getbbox to calculate text width and height
        bbox = draw.textbbox((0, 0), line, font=font)
        if bbox:  # Ensure bbox is not None
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x_position = (image_width - text_width) / 2  # This centers the text horizontally
            for char in line:
                char_bbox = draw.textbbox((0, 0), char, font=font)
                char_width = char_bbox[2] - char_bbox[0]
                char_height = char_bbox[3] - char_bbox[1]
                draw.text((text_x_position, current_h), char, font=font, fill=underscore_color if char == '_' else color)
                text_x_position += char_width
            # Adjust line spacing for lines with only underscores
            if set(line.strip()) == {'_'}:
                current_h += text_height + line_spacing * 2
            else:
                current_h += text_height + line_spacing  # Increase distance between lines

    # Save or display the image with compression
    #image.save("test.png", format='JPEG', optimize=True, quality=20)
    with BytesIO() as output:
        image.save(output, format='JPEG', optimize=True, quality=20)
        output.seek(0)
        return discord.File(output, filename='boll.jpg')
