#!/usr/bin/env python

import os
import string
import codecs
import barcode
import brotherlabel
import subprocess
from pylibdmtx.pylibdmtx import encode as dmtx_encode
from matplotlib import font_manager
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageOps, ImageFont
from bil_name import gen_device_name

H = 84
y_margin = 2
x_margin = 4

def find_brother():
    result = subprocess.run(['lsusb'], capture_output=True)
    usb_devices = str(result.stdout, 'utf-8').strip().split('\n')
    for device in usb_devices:
        if 'PT-P950NW' in device:
            fields = device.split()
            device_id = fields[fields.index('ID') + 1]
            return device_id
    return None

def print_speck_labels(device_id, device_name, device_type=None):
    device_id_string = device_id
    if device_type is not None:
        device_id_string += f':{device_type}'

    id_name_img = generate_speck_id_name_img(device_id_string, device_name)
    id_img = generate_internal_id_label(device_id)
    barcode_img = generate_dmtx(device_id);

    return print_labels([id_name_img, id_img, barcode_img])

def generate_dmtx(data):
    encoded = dmtx_encode(data.encode('utf8'), size='12x26')
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)

    img = ImageOps.invert(img)

    return img

def generate_barcode(data):
    b64 = codecs.encode(codecs.decode(data, 'hex'), 'base64').decode()
    print(b64)

    # Choose the barcode type (CODE128, EAN, etc.)
    barcode = barcode.get_barcode_class('code128')

    # Create the barcode instance
    barcode_instance = barcode(b64, writer=ImageWriter())

    # Set the height of the barcode
    options = {
            'dpi': 360,
            'module_height': 4,
            'quiet_zone': -1,
            'text_distance':0,
            'write_text': False,
    }

    # Generate the barcode as a Pillow Image
    pil_image = barcode_instance.render(options)
    pil_image = ImageOps.invert(pil_image)
    return pil_image

def generate_speck_id_name_img(device_id, device_name):
    device_id = device_id.upper()
    device_name = device_name.lower().replace('_', ' ')

    font_size = 12
    while(1):
        font = ImageFont.truetype(os.path.expanduser("~/.fonts/Oswald-Regular.ttf"), font_size)
        bbox = font.getbbox(string.ascii_lowercase + string.ascii_uppercase)
        if (bbox[3] - bbox[1] >= 36): break;
        font_size += 1

    bbox = font.getbbox(device_id)
    bbox2 = font.getbbox(device_name)

    if bbox[2] > bbox2[2]:
        L = bbox[2] + x_margin*2
    else:
        L = bbox2[2] + x_margin*2

    id_y = (bbox[3] - bbox[1])/2
    name_y = id_y*3 + y_margin

    image = Image.new("RGB", (L, H), "white")
    draw = ImageDraw.Draw(image)
    id_txt = draw.text((L/2, id_y - y_margin), device_id, anchor='mm', font=font, fill="black")
    name_txt = draw.text((L/2, name_y - y_margin), device_name, anchor='mm', font=font, fill="black")

    return image

def print_br_label(device_id, device_name, eth_mac, wifi_mac):
    img = generate_br_id_name_img(device_id, device_name, eth_mac, wifi_mac)
    barcode_img = generate_dmtx(device_id);

    both_img = Image.new("RGB", (img.width + barcode_img.width, img.height), "white")

    both_img.paste(img, (0, -10))
    both_img.paste(barcode_img, (img.width, 0))

    return print_labels([both_img])

def generate_br_id_name_img(device_id, device_name, eth_mac, wifi_mac):
    device_id = device_id.upper()
    device_name = device_name.lower().replace('_', ' ')
    eth_mac = eth_mac.upper()
    wifi_mac = wifi_mac.upper()

    font_size = 12
    while(1):
        font = ImageFont.truetype(os.path.expanduser("~/.fonts/Oswald-Regular.ttf"), font_size)
        bbox = font.getbbox(string.ascii_lowercase + string.ascii_uppercase)
        if (bbox[3] - bbox[1] >= 36): break;
        font_size += 1

    first_line = f'ID: {device_id}  NAME: {device_name}'
    second_line = f'ETH: {eth_mac}    WIFI: {wifi_mac}'

    bbox = font.getbbox(first_line)
    bbox2 = font.getbbox(second_line)

    if bbox[2] > bbox2[2]:
        L = bbox[2] + x_margin*2
    else:
        L = bbox2[2] + x_margin*2

    first_y = (bbox[3] - bbox[1])/2
    second_y = first_y*3 + y_margin

    image = Image.new("RGB", (L, H), "white")
    draw = ImageDraw.Draw(image)
    id_txt = draw.text((0, first_y - y_margin), first_line, anchor='lt', font=font, fill="black")
    name_txt = draw.text((0, second_y - y_margin), second_line, anchor='lt', font=font, fill="black")

    return image

def generate_internal_id_label(device_id):
    device_id = device_id.upper()
    device_id_frag = device_id[:4]

    font_size = 12
    while(1):
        font = ImageFont.truetype(os.path.expanduser("~/.fonts/Oswald-Regular.ttf"), font_size)
        bbox = font.getbbox(string.ascii_uppercase)
        if (bbox[3] - bbox[1] >= 72): break;
        font_size += 1

    bbox = font.getbbox(device_id_frag)

    L = bbox[2] + x_margin*2
    id_y = (bbox[3] - bbox[1])/2

    image = Image.new("RGB", (L, H), "white")
    draw = ImageDraw.Draw(image)
    id_txt = draw.text((L/2, id_y - y_margin), device_id_frag, anchor='mm', font=font, fill="black")

    return image

def print_labels(labels):
    brother_usb_id = find_brother()
    if brother_usb_id is None:
        return None
    backend = brotherlabel.USBBackend(f"usb://{brother_usb_id}")
    printer = brotherlabel.PTPrinter(backend)
    printer.quality = brotherlabel.Quality.high_quality
    printer.tape = brotherlabel.Tape.TZe6mm
    printer.margin = y_margin

    #for x in labels:
    #    x.show()

    return printer.print(labels)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Blue Iris Labs Speck Label Printer')
    parser.add_argument('device_id', help='device id: 64-bit hexidecimal')
    parser.add_argument('device_name', help='device name: {adjective}_{noun} colloquial name', nargs='?',default=None)
    args = parser.parse_args()

    device_name = args.device_name
    if args.device_name == None:
        device_name = gen_device_name(args.device_id)
    print(device_name)

    print_speck_labels(args.device_id, device_name)

