import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs('static/images', exist_ok=True)
os.makedirs('uploads/songs', exist_ok=True)
os.makedirs('uploads/covers', exist_ok=True)
os.makedirs('uploads/profiles', exist_ok=True)

def create_gradient_cover(filename, text, subtitle, start_color, end_color, size=(500, 500)):
    img = Image.new('RGB', size, start_color)
    draw = ImageDraw.Draw(img)
    
    # Gradient background
    for y in range(size[1]):
        r = int(start_color[0] + (end_color[0] - start_color[0]) * (y / size[1]))
        g = int(start_color[1] + (end_color[1] - start_color[1]) * (y / size[1]))
        b = int(start_color[2] + (end_color[2] - start_color[2]) * (y / size[1]))
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    
    # Inner border / glass glow
    draw.rounded_rectangle([20, 20, size[0]-20, size[1]-20], radius=30, outline=(255, 255, 255, 60), width=3)
    
    # Center visual bars (Soundwave)
    center_y = size[1] // 2
    bar_heights = [40, 80, 140, 90, 160, 200, 150, 110, 70, 40]
    bar_width = 16
    spacing = 10
    total_w = len(bar_heights) * bar_width + (len(bar_heights) - 1) * spacing
    start_x = (size[0] - total_w) // 2
    
    for i, h in enumerate(bar_heights):
        x = start_x + i * (bar_width + spacing)
        y0 = center_y - h // 2
        y1 = center_y + h // 2
        draw.rounded_rectangle([x, y0, x + bar_width, y1], radius=8, fill=(255, 255, 255, 220))
        
    img.save(filename, 'PNG')
    print(f"Saved {filename}")

def create_avatar(filename, size=(300, 300)):
    img = Image.new('RGB', size, (18, 9, 14))
    draw = ImageDraw.Draw(img)
    
    # Gradient Circle with Red glow border
    draw.ellipse([20, 20, size[0]-20, size[1]-20], fill=(42, 18, 28), outline=(255, 30, 86), width=4)
    
    # Head & Body avatar silhouette
    head_r = 45
    cx, cy = size[0]//2, size[1]//2 - 20
    draw.ellipse([cx - head_r, cy - head_r, cx + head_r, cy + head_r], fill=(255, 255, 255))
    
    # Body arc
    draw.chord([cx - 80, cy + 30, cx + 80, cy + 170], 0, 360, fill=(255, 30, 86))
    
    img.save(filename, 'PNG')
    print(f"Saved {filename}")

# Create default assets with Red & White Palette
create_gradient_cover('static/images/default_cover.png', 'VIBE VAULT', 'MUSIC', (160, 0, 35), (255, 80, 120))
create_gradient_cover('static/images/default_playlist.png', 'PLAYLIST', 'COLLECTION', (120, 5, 25), (255, 120, 150))
create_avatar('static/images/default_avatar.png')

# Also copy to uploads default references
import shutil
shutil.copy('static/images/default_cover.png', 'uploads/covers/default_cover.png')
shutil.copy('static/images/default_playlist.png', 'uploads/covers/default_playlist.png')
shutil.copy('static/images/default_avatar.png', 'uploads/profiles/default_avatar.png')
