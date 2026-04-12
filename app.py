from flask import Flask, request, jsonify
import requests
import base64
import io
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

app = Flask(__name__)

FONT_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
]

def get_font(size):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

def compose_image(photo_b64, main_text, sub_text, logo_b64):
    img_data = base64.b64decode(photo_b64)
    img = Image.open(io.BytesIO(img_data)).convert('RGB')
    w, h = img.size
    target_w, target_h = 1080, 1350
    aspect = target_w / target_h
    if w/h > aspect:
        new_w = int(h * aspect)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / aspect)
        top = int((h - new_h) * 0.2)
        img = img.crop((0, top, w, top + new_h))
    img = img.resize((target_w, target_h), Image.LANCZOS)

    overlay = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    fade_start = int(target_h * 0.58)
    fade_zone = target_h - fade_start
    for i in range(fade_zone):
        alpha = int((i/fade_zone)**1.2 * 135)
        d.rectangle([(0, fade_start+i),(target_w, fade_start+i+1)], fill=(0,0,0,alpha))

    final = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(final)

    if logo_b64:
        logo_data = base64.b64decode(logo_b64)
        logo = Image.open(io.BytesIO(logo_data)).convert('RGBA')
        lw = 130
        lh = int(logo.height * (lw/logo.width))
        logo = logo.resize((lw, lh), Image.LANCZOS)
        r,g,b,a = logo.split()
        a = a.point(lambda x: int(x*0.82))
        logo = Image.merge('RGBA', (r,g,b,a))
        final.paste(logo, (50, 50), logo)

    y_start = int(target_h * 0.70)

    font_main = get_font(52)
    bbox = draw.textbbox((0,0), main_text, font=font_main)
    tw = bbox[2] - bbox[0]
    x = (target_w - tw) // 2
    shadow_img = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
    sd = ImageDraw.Draw(shadow_img)
    sd.text((x, y_start), main_text, font=font_main, fill=(0,0,0,160))
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(3))
    final = Image.alpha_composite(final.convert('RGBA'), shadow_img).convert('RGB')
    draw = ImageDraw.Draw(final)
    draw.text((x, y_start), main_text, font=font_main, fill=(255,255,255))

    if sub_text:
        font_sub = get_font(28)
        bbox2 = draw.textbbox((0,0), sub_text, font=font_sub)
        tw2 = bbox2[2] - bbox2[0]
        x2 = (target_w - tw2) // 2
        y2 = y_start + 72
        shadow_img2 = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
        sd2 = ImageDraw.Draw(shadow_img2)
        sd2.text((x2, y2), sub_text, font=font_sub, fill=(0,0,0,120))
        shadow_img2 = shadow_img2.filter(ImageFilter.GaussianBlur(2))
        final = Image.alpha_composite(final.convert('RGBA'), shadow_img2).convert('RGB')
        draw = ImageDraw.Draw(final)
        draw.text((x2, y2), sub_text, font=font_sub, fill=(235,230,220))

    output = io.BytesIO()
    final.save(output, format='JPEG', quality=97)
    output.seek(0)
    return base64.b64encode(output.read()).decode('utf-8')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'wearth-compositor'})

@app.route('/compose', methods=['POST'])
def compose():
    try:
        data = request.json
        photo_b64 = data.get('photo_base64')
        main_text = data.get('main_text', '')
        sub_text = data.get('sub_text', '')
        logo_b64 = data.get('logo_base64', '')
        if not photo_b64:
            return jsonify({'error': 'photo_base64 required'}), 400
        result_b64 = compose_image(photo_b64, main_text, sub_text, logo_b64)
        return jsonify({'image_base64': result_b64, 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
