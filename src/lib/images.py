from typing import Iterable
from PIL import Image, ImageOps, ImageDraw, ImageFont
import requests
from io import BytesIO

from src.lib.lastfm import RecentlyPlayedSong

def get_disk_mask(
    image_size: tuple[int, int],
    middle_hole_size: int,
    *,
    no_hole : bool = False
) -> Image.Image:
    
    mask = Image.new(mode="L", size=image_size, color=0)
    mask_draw = ImageDraw.Draw(mask, mode="L")

    # This is the containing circle
    mask_draw.ellipse((0, 0) + (image_size[0] - 1, image_size[1]- 1), fill=255)

    # Then we punch out the middle hole
    if not no_hole:
        image_size_halfed = (image_size[0] // 2, image_size[1] // 2)
        middle_hole_size_halfed = middle_hole_size // 2

        hole_coordinates = (
            image_size_halfed[0] - middle_hole_size_halfed, 
            image_size_halfed[1] - middle_hole_size_halfed,
            image_size_halfed[0] + middle_hole_size_halfed, 
            image_size_halfed[1] + middle_hole_size_halfed,
        )

        mask_draw.ellipse(
            hole_coordinates,
            fill = 0
        )

    return mask

def fetch_cover_art(
    cover_art_url: str
) -> Image.Image:
    
    resp = requests.get(cover_art_url)
    
    return Image.open(BytesIO(resp.content))

def generate_disk_frames(
    frame_count : int,
    cover_art_url : str,
    *,
    resize_to : tuple[int, int] = (50, 50),
) -> Iterable[Image.Image]:
    
    album_art = (
        fetch_cover_art(cover_art_url)
            .convert("RGBA")
            .resize(resize_to, resample=Image.Resampling.LANCZOS)
    )

    mask = get_disk_mask(
        image_size = album_art.size,
        middle_hole_size = 10,
    )

    for frame_no in range(frame_count):
        rot_degree = 360 * (frame_no / frame_count)

        rotated_art = album_art.rotate(rot_degree)

        album_ops = ImageOps.fit(rotated_art, mask.size, centering=(0.5, 0.5))

        album_ops.putalpha(mask)

        yield album_ops

def generate_scrolling_text(
    frame_count: int,
    wait_time : int,
    font : ImageFont.ImageFont | ImageFont.FreeTypeFont,
    bbox_width: int,
    text: str,
    text_color: tuple = (255, 255, 255),
    end_wait_frames : int = 0
) -> Iterable[Image.Image]:
    
    measure_image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(measure_image)
    l, t, r, b = measure_draw.textbbox((0, 0), text, font=font)

    full_w = max(1, int(r - l))
    full_h = max(1, int(b - t))

    text_image = Image.new(mode="RGBA", color=(0, 0, 0, 0), size=(full_w, full_h))
    text_image_draw = ImageDraw.Draw(text_image, mode='RGBA')
    text_image_draw.text((-l, -t), text=text, fill=text_color, font=font)

    non_waiting_frames = frame_count - (wait_time + end_wait_frames)

    if non_waiting_frames < 0:
        raise ValueError("Frame count too small for waiting frames")

    for frame_no in range(frame_count):

        crop_section = (0, 0, min(r, bbox_width), b)

        if frame_no > wait_time and frame_no <= (non_waiting_frames + wait_time):
            # Calculate new crop section based on frame number

            distance_to_travel = max(0, full_w - bbox_width)
            distance_per_frame = distance_to_travel / non_waiting_frames

            x_offset = distance_per_frame * (frame_no - wait_time)

            crop_section = (x_offset, 0, min(r, bbox_width + x_offset), b)

        elif frame_no > (non_waiting_frames + wait_time):
            # Calculate crop at end of image

            x_offset = max(0, full_w - bbox_width)
            crop_section = (x_offset, 0, r, b)

        yield text_image.crop(crop_section)

def generate_title_label(
    frame_count: int,
    title: str,
    font : ImageFont.ImageFont | ImageFont.FreeTypeFont,
    color: tuple = (255, 255, 255),
) -> Iterable[Image.Image]:

    measure_image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    measure_draw = ImageDraw.Draw(measure_image)
    left, top, right, bottom = measure_draw.textbbox((0, 0), title, font=font)

    width = max(1, int(right - left))
    height = max(1, int(bottom - top))
    text_image = Image.new(mode="RGBA", color=(0, 0, 0, 0), size=(width, height))

    text_image_draw = ImageDraw.Draw(text_image, mode="RGBA")
    text_image_draw.text((-left, -top), text=title, fill=color, font=font)

    for frame_no in range(frame_count):

        yield text_image

def get_monkey() -> Image.Image:

    monkey_image = Image.open("./src/assets/monkey.png").convert(mode="RGBA")

    r,g,b,a = monkey_image.split()

    new_alpha = a.point(lambda p: 15)

    monkey_image.putalpha(new_alpha)

    return monkey_image
    

def generate_now_playing_image(
    frame_count: int,
    song: RecentlyPlayedSong
) -> list[Image.Image]:
    
    base = Image.new(
        mode="RGBA",
        size=(400, 80),
        color=(20, 20, 20)
    )

    # font = ImageFont.load_default(size=16)

    title_font = ImageFont.truetype("consola.ttf", size=16)
    header_font = ImageFont.truetype("consola.ttf", size=14)
    artist_font = ImageFont.truetype("consola.ttf", size=14)
    jammie_discs_font = ImageFont.truetype("consola.ttf", size=12)

    frames = []

    base_draw = ImageDraw.ImageDraw(base)

    if song.is_now_playing:
        base_draw.text(
            (85, 12), 
            text="CURRENTLY LISTENING TO", 
            fill=(0, 255, 0), 
            font = header_font
        )
    else:
        base_draw.text(
            (85, 12), 
            text="MOST RECENTLY PLAYED SONG", 
            fill=(250, 128, 114), 
            font = header_font
        )


    base_draw.text(
        (85, 52),
        text = song.artist.upper(),
        font=artist_font,
        fill=(180, 180, 180)
    )

    base_draw.text(
        (base.size[0] - 2, 2),
        text="JAMMIE DISCS",
        fill = (80, 80, 80),
        anchor="rt",
        font=jammie_discs_font,
        spacing=4
    )

    monkey = get_monkey()

    base.alpha_composite(monkey, (330, 12))

    for disk_frame, title_label in zip(
        generate_disk_frames(
            frame_count=frame_count, 
            cover_art_url=song.cover_art,
            resize_to=(64, 64)
        ),
        generate_scrolling_text(
            frame_count=frame_count,
            text = song.title,
            font = title_font,
            bbox_width = 300,
            wait_time = 8,
            end_wait_frames = 8
        )
    ):
        base_clone = base.copy()

        base_clone.alpha_composite(disk_frame, (8, 8))
        base_clone.alpha_composite(title_label, (85 , 32))

        frames.append(base_clone)

    return frames