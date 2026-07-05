#!/usr/bin/env python3
"""
Thumbnail Generator for the social media agent.
Creates YouTube video thumbnails using Pillow (PIL) only.
"""

import sys
import os
import argparse
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHANNELS

def generate_thumbnail(channel, title, output_path):
    """
    Generate a YouTube thumbnail (1280x720) for the given channel and title.
    """
    width, height = 1280, 720
    
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    color_schemes = {
        'soccer': {
            'top': (34, 139, 34),
            'bottom': (0, 100, 0),
            'title_color': (255, 255, 255),
            'channel_color': (255, 215, 0),
            'accent_color': (255, 255, 255)
        },
        'christian': {
            'top': (255, 215, 0),
            'bottom': (138, 43, 226),
            'title_color': (255, 255, 255),
            'channel_color': (255, 255, 255),
            'accent_color': (255, 255, 255)
        },
        'trading': {
            'top': (0, 0, 139),
            'bottom': (0, 0, 0),
            'title_color': (255, 255, 255),
            'channel_color': (255, 255, 255),
            'accent_color': (255, 255, 0)
        }
    }
    
    colors = color_schemes.get(channel, color_schemes['soccer'])
    
    for y in range(height):
        ratio = y / height
        r = int(colors['top'][0] + (colors['bottom'][0] - colors['top'][0]) * ratio)
        g = int(colors['top'][1] + (colors['bottom'][1] - colors['top'][1]) * ratio)
        b = int(colors['top'][2] + (colors['bottom'][2] - colors['top'][2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    font_title = ImageFont.load_default()
    font_channel = ImageFont.load_default()
    
    def draw_bold_text(text, position, font, fill_color, offset=2):
        x, y = position
        for dx in range(-offset, offset+1):
            for dy in range(-offset, offset+1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
        draw.text((x, y), text, font=font, fill=fill_color)
    
    if channel == 'soccer':
        ball_center = (width // 2, height // 2)
        ball_radius = 80
        draw.ellipse([
            ball_center[0] - ball_radius,
            ball_center[1] - ball_radius,
            ball_center[0] + ball_radius,
            ball_center[1] + ball_radius
        ], outline=colors['accent_color'], width=4)
        draw.ellipse([
            ball_center[0] - ball_radius//2,
            ball_center[1] - ball_radius//2,
            ball_center[0] + ball_radius//2,
            ball_center[1] + ball_radius//2
        ], outline=colors['accent_color'], width=2)
        draw.ellipse([
            ball_center[0] - 10,
            ball_center[1] - 10,
            ball_center[0] + 10,
            ball_center[1] + 10
        ], fill=colors['accent_color'])
        for i in range(5):
            angle = i * 2 * 3.14159 / 5
            x1 = ball_center[0] + int(ball_radius * 0.6 * 3.14159 * i / 5)
            y1 = ball_center[1] + int(ball_radius * 0.6 * 3.14159 * i / 5)
            x2 = ball_center[0] + int(ball_radius * 0.8 * 3.14159 * (i+1) / 5)
            y2 = ball_center[1] + int(ball_radius * 0.8 * 3.14159 * (i+1) / 5)
            draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0), width=2)
            
    elif channel == 'christian':
        cross_center = (width // 2, height // 2)
        for i in range(8):
            angle = i * 2 * 3.14159 / 8
            length = 60
            x1 = cross_center[0] + int(length * 0.3 * 3.14159 * i / 8)
            y1 = cross_center[1] + int(length * 0.3 * 3.14159 * i / 8)
            x2 = cross_center[0] + int(length * 3.14159 * i / 8)
            y2 = cross_center[1] + int(length * 3.14159 * i / 8)
            draw.line([(x1, y1), (x2, y2)], fill=colors['accent_color'], width=3)
        bar_width = 20
        bar_height = 80
        draw.rectangle([
            cross_center[0] - bar_width//2,
            cross_center[1] - bar_height//2,
            cross_center[0] + bar_width//2,
            cross_center[1] + bar_height//2
        ], fill=colors['accent_color'])
        draw.rectangle([
            cross_center[0] - bar_height//2,
            cross_center[1] - bar_width//2,
            cross_center[0] + bar_height//2,
            cross_center[1] + bar_width//2
        ], fill=colors['accent_color'])
            
    elif channel == 'trading':
        axis_y = height - 100
        axis_x0 = 200
        axis_x1 = width - 200
        draw.line([(axis_x0, axis_y), (axis_x1, axis_y)], fill=colors['accent_color'], width=2)
        points = []
        for i in range(10):
            x = axis_x0 + i * 20
            y = axis_y - i * 15 - (i % 3) * 5
            points.append((x, y))
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=colors['accent_color'], width=3)
        for point in points:
            draw.ellipse([
                point[0] - 3, point[1] - 3,
                point[0] + 3, point[1] + 3
            ], fill=colors['accent_color'])
    
    title_y = height // 4
    channel_y = height * 3 // 4
    
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw_bold_text(title, (title_x, title_y), font_title, colors['title_color'])
    
    channel_name = CHANNELS[channel].name
    channel_bbox = draw.textbbox((0, 0), channel_name, font=font_channel)
    channel_width = channel_bbox[2] - channel_bbox[0]
    channel_x = (width - channel_width) // 2
    draw_bold_text(channel_name, (channel_x, channel_y), font_channel, colors['channel_color'])
    
    img.save(output_path, 'JPEG', quality=85)
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Generate YouTube thumbnail for social media')
    parser.add_argument('--channel', required=True, choices=['soccer', 'christian', 'trading'],
                        help='Channel name')
    parser.add_argument('--title', required=True, help='Video title')
    parser.add_argument('--output', required=True, help='Output file path')
    
    args = parser.parse_args()
    
    try:
        generate_thumbnail(args.channel, args.title, args.output)
        print(f"Thumbnail generated: {args.output}")
        if os.path.exists(args.output):
            size = os.path.getsize(args.output)
            print(f"File size: {size} bytes ({size / 1024 / 1024:.2f} MB)")
            if size > 2 * 1024 * 1024:
                print("WARNING: File size exceeds 2MB limit", file=sys.stderr)
        else:
            print("ERROR: File was not created", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
