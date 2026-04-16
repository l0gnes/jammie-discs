from os import PathLike
from typing import Iterable
from PIL import Image, ImageOps, ImageDraw, ImageFont
import requests
from io import BytesIO

from src.lib.lastfm import RecentlyPlayedSong
from src.lib.themes import Theme as JammieTheme

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
    left, top, right, bottom = measure_draw.textbbox((0, 0), text, font=font)

    full_w = max(1, int(right - left))
    full_h = max(1, int(bottom - top))

    text_image = Image.new(mode="RGBA", color=(0, 0, 0, 0), size=(full_w, full_h))
    text_image_draw = ImageDraw.Draw(text_image, mode='RGBA')
    text_image_draw.text((-left, -top), text=text, fill=text_color, font=font)

    non_waiting_frames = frame_count - (wait_time + end_wait_frames)

    if non_waiting_frames < 0:
        raise ValueError("Frame count too small for waiting frames")

    for frame_no in range(frame_count):

        crop_section = (0, 0, min(full_w, bbox_width), full_h)

        if frame_no > wait_time and frame_no <= (non_waiting_frames + wait_time):
            # Calculate new crop section based on frame number

            distance_to_travel = max(0, full_w - bbox_width)
            distance_per_frame = distance_to_travel / non_waiting_frames

            x_offset = distance_per_frame * (frame_no - wait_time)

            crop_section = (
                int(round(x_offset)),
                0,
                int(round(min(full_w, bbox_width + x_offset))),
                full_h
            )

        elif frame_no > (non_waiting_frames + wait_time):
            # Calculate crop at end of image

            x_offset = max(0, full_w - bbox_width)
            crop_section = (int(round(x_offset)), 0, full_w, full_h)

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

def get_watermark(watermark_fp : str | PathLike) -> Image.Image:

    monkey_image = Image.open(watermark_fp).convert(mode="RGBA")

    r,g,b,a = monkey_image.split()

    new_alpha = a.point(lambda p: 15)

    monkey_image.putalpha(new_alpha)

    return monkey_image
    

def generate_now_playing_image(
    frame_count: int,
    song: RecentlyPlayedSong,
    theme: JammieTheme,
    *,
    debug_layer : bool = False
) -> list[Image.Image]:
    
    IMAGE_WIDTH = 400
    IMAGE_HEIGHT = 80

    base = Image.new(
        mode="RGBA",
        size=(IMAGE_WIDTH, IMAGE_HEIGHT),
        color=theme["background_fill"] or (0, 0, 0, 1)
    )

    TITLE_FONT_SIZE = 16
    HEADER_FONT_SIZE = 14
    ARTIST_FONT_SIZE = 14
    WATERMARK_TEXT_FONT_SIZE = 12

    SONG_TITLE_BOUNDING_BOX_WIDTH = 300

    title_font = ImageFont.truetype("./src/assets/consola.ttf", size=TITLE_FONT_SIZE)
    header_font = ImageFont.truetype("./src/assets/consola.ttf", size=HEADER_FONT_SIZE)
    artist_font = ImageFont.truetype("./src/assets/consola.ttf", size=ARTIST_FONT_SIZE)
    jammie_discs_font = ImageFont.truetype("./src/assets/consola.ttf", size=WATERMARK_TEXT_FONT_SIZE)

    GAP_MAIN_TEXT : int = 5
    LEFTMOST_SIDE_MAIN_TEXT : int = 85

    def get_line_height(font: ImageFont.ImageFont | ImageFont.FreeTypeFont) -> int:
        if isinstance(font, ImageFont.FreeTypeFont):
            ascent, descent = font.getmetrics()
            return max(1, int(ascent + descent))

        # Fallback for non-FreeType fonts.
        left, top, right, bottom = font.getbbox("Ag")
        return max(1, int(bottom - top))

    header_line_height = get_line_height(header_font)
    title_line_height = get_line_height(title_font)
    artist_line_height = get_line_height(artist_font)

    full_height_of_maintext = (
        header_line_height + title_line_height + artist_line_height + (GAP_MAIN_TEXT * 2)
    )
    remaining_height_maintext = IMAGE_HEIGHT - full_height_of_maintext
    starting_offset_for_maintext = round(remaining_height_maintext / 2)

    title_text_y = starting_offset_for_maintext + header_line_height + GAP_MAIN_TEXT
    artist_text_y = title_text_y + title_line_height + GAP_MAIN_TEXT

    frames = []

    base_draw = ImageDraw.ImageDraw(base)

    if song.is_now_playing:
        base_draw.text(
            (LEFTMOST_SIDE_MAIN_TEXT, starting_offset_for_maintext), 
            text="CURRENTLY LISTENING TO", 
            fill= theme["now_playing_text"], 
            font = header_font,
            anchor="lt",
        )
    else:
        base_draw.text(
            (LEFTMOST_SIDE_MAIN_TEXT, starting_offset_for_maintext), 
            text="MOST RECENTLY PLAYED SONG", 
            fill= theme["last_played_text"], 
            font = header_font,
            anchor="lt",
        )

    base_draw.text(
        (
            LEFTMOST_SIDE_MAIN_TEXT,
            artist_text_y
        ),
        text = song.artist.upper(),
        font=artist_font,
        fill= theme["artist_name_text"],
        anchor="lt",
    )

    base_draw.text(
        (base.size[0] - 2, 2),
        text="JAMMIE DISCS",
        fill = theme["jammie_discs_text"],
        font=jammie_discs_font,
        spacing=4,
        anchor="rt",
    )

    if theme["watermark_fp"]:
        monkey = get_watermark(
            watermark_fp = theme["watermark_fp"]
        )

        base.alpha_composite(monkey, (330, 12))

    if debug_layer:
        # Line at mid part
        base_draw.line((0, round(IMAGE_HEIGHT / 2), IMAGE_WIDTH, round(IMAGE_HEIGHT / 2)), fill=(255, 0, 0), width=1)

        # Line at leftmost
        base_draw.line((LEFTMOST_SIDE_MAIN_TEXT, 0, LEFTMOST_SIDE_MAIN_TEXT, IMAGE_HEIGHT), fill=(0, 255, 0), width=1)

        # Lines enclosing main text
        base_draw.line((LEFTMOST_SIDE_MAIN_TEXT, starting_offset_for_maintext, IMAGE_WIDTH, starting_offset_for_maintext), fill=(0, 0, 255), width=1)
        maintext_bottom = (starting_offset_for_maintext + (2 * GAP_MAIN_TEXT) + header_line_height + title_line_height + artist_line_height)
        base_draw.line((LEFTMOST_SIDE_MAIN_TEXT, maintext_bottom, IMAGE_WIDTH, maintext_bottom), fill=(0, 0, 255), width=1)

        # Line for where title bounding box ends
        bbox_with_offset = LEFTMOST_SIDE_MAIN_TEXT + SONG_TITLE_BOUNDING_BOX_WIDTH
        base_draw.line((bbox_with_offset, 0, bbox_with_offset, IMAGE_HEIGHT), fill=(225, 255, 0), width=1)

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
            bbox_width = SONG_TITLE_BOUNDING_BOX_WIDTH,
            wait_time = 8,
            end_wait_frames = 8,
            text_color = theme["song_title_text"] # type: ignore
        )
    ):
        base_clone = base.copy()

        base_clone.alpha_composite(disk_frame, (8, 8))
        base_clone.alpha_composite(title_label, (LEFTMOST_SIDE_MAIN_TEXT , title_text_y))

        frames.append(base_clone)

    return frames