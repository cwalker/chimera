import re
import os
import shutil
import yaml
from PIL import Image, ImageFont, ImageDraw
from chimera_app.utils import ensure_directory
from chimera_app.utils import file_exists
from chimera_app.utils import ChimeraContext


def sanitize(string):
    if isinstance(string, str):
        retval = string
        for r in ['\n', '\r', '/', '\\', '\0']:
            retval = retval.replace(r, '_')
        retval.replace('"', '')
        return retval
    return string


def load_shortcuts(platform):
    shortcuts = []
    se = ChimeraContext()
    ensure_directory(se.SHORTCUT_DIRS[0])

    shortcuts_file = se.SHORTCUT_DIRS[0] + \
        "/chimera.{platform}.yaml".format(platform=platform)
    if file_exists(shortcuts_file):
        shortcuts = yaml.load(open(shortcuts_file), Loader=yaml.Loader)

    if not shortcuts:
        shortcuts = []

    return shortcuts


def delete_file_link(base_dir, platform, name):
    e = re.escape(name) + r"\.[^.]+$"
    d = os.path.join(base_dir, platform)
    links = []
    if os.path.isdir(d):
        links = [os.path.join(d, l) for l in os.listdir(d) if re.match(e, l)]

    if len(links) < 1:
        return

    for link in links:
        if os.path.islink(link) or os.path.exists(link):
            os.remove(link)


def is_direct(platform, content_type):
    return (platform == "arcade" or platform == "neo-geo") and content_type == "content"


def upsert_file(src_path, base_dir, platform, name, dst_name):
    if not src_path:
        return

    content_type = os.path.basename(base_dir)
    filename = sanitize(dst_name)
    file_dir = "{base_dir}/{platform}/.{name}".format(base_dir=base_dir, platform=platform, name=name)

    # mame ROM files have dependencies on each other, so store them all in a single directory
    if is_direct(platform, content_type):
        file_dir = "{base_dir}/{platform}/.{platform}".format(base_dir=base_dir, platform=platform)

    if not os.path.exists(file_dir):
        os.makedirs(file_dir)

    file_path = "{file_dir}/{filename}".format(file_dir=file_dir, filename=filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    shutil.move(src_path, file_path)

    _, ext = os.path.splitext(filename)
    dst = "{base_dir}/{platform}/{name}{ext}".format(base_dir=base_dir, platform=platform, name=name, ext=ext)

    delete_file_link(base_dir, platform, name)
    os.symlink(file_path, dst)

    # mame requires ROM files to have a specific name, so launch original file directly
    if is_direct(platform, content_type):
        return file_path

    return dst


def strip(string):
    if string.startswith('"') and string.endswith('"'):
        return string[1:-1]
    return string


def delete_file(base_dir, platform, name):
    if is_direct(platform, os.path.basename(base_dir)):
        shortcuts = load_shortcuts(platform)
        matches = [e for e in shortcuts if e['name'] == name and e['cmd'] == platform]
        shortcut = matches[0]
        if 'dir' in shortcut and 'params' in shortcut:
            file_path = os.path.join(strip(shortcut['dir']), strip(shortcut['params']))
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        file_dir = "{base_dir}/{platform}/.{name}".format(base_dir=base_dir, platform=platform, name=name)
        if os.path.exists(file_dir):
            shutil.rmtree(file_dir)

    delete_file_link(base_dir, platform, name)


def generate_banner(text, path):
    # The thumbnail size used by Steam is set
    banner_width = 460
    banner_height = 215
    banner = Image.new('RGB', (banner_width, banner_height), color=(0, 0, 0))

    font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf", 24)

    text_width, text_height = font.getsize(text)

    # Shorten the text if it doesn't fit on the image
    while text_width > banner_width:
        text = text[:-4] + "..."
        text_width, text_height = font.getsize(text)

    text_x = int(banner_width / 2 - text_width / 2)
    text_y = int(banner_height / 2 - text_height / 2)

    title = ImageDraw.Draw(banner)
    title.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

    banner.save(path)