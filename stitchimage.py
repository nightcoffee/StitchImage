# -*- coding: utf-8 -*-
import os
import sys
import shutil
import configparser
import traceback
import io
import platform
import ctypes.wintypes
import multiprocessing
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont, ImageCms
from functools import cmp_to_key
import operator
import argparse
import random


def get_hist(img, font):
    _, _, _, font_height = font.getbbox('1234567890', anchor='lt')
    grey_img = img.convert('L')
    grey_img_hist = grey_img.histogram()
    hist_max = max(grey_img_hist)
    hist_img = Image.new("RGB", (256 + 20, 128 + 25 + font_height), (255, 255, 255))
    drawing = ImageDraw.Draw(hist_img)
    for i, v in enumerate(grey_img_hist):
        drawing.line((i + 10, 127 + 10, i + 10, 127 - 128.0 * v / hist_max + 10), fill=(0, 0, 0))  # Draw histogram
        if i == 32 or i == 64 or i == 96 or i == 128 or i == 160 or i == 192 or i == 224:
            drawing.line((i + 10, 127 + 10, i + 10, 10), fill=(224, 224, 224))  # Draw grid on white background
            drawing.line((i + 10, 127 + 10, i + 10, 127 - 128.0 * v / hist_max + 10),
                         fill=(64, 64, 64))  # Draw grid on Black background

    drawing.line((0 + 10, 128 + 10, 0 + 10, 128 + 10 + 3), fill=(0, 0, 0))
    drawing.line((64 + 10, 128 + 10, 64 + 10, 128 + 10 + 3), fill=(0, 0, 0))
    drawing.line((128 + 10, 128 + 10, 128 + 10, 128 + 10 + 3), fill=(0, 0, 0))
    drawing.line((192 + 10, 128 + 10, 192 + 10, 128 + 10 + 3), fill=(0, 0, 0))
    drawing.line((255 + 10, 128 + 10, 255 + 10, 128 + 10 + 3), fill=(0, 0, 0))

    drawing.text((0 + 10, 128 + 10 + 10), "0", font=font, fill=(0, 0, 0), anchor='lt')  # Bottom of histogram
    drawing.text((64 + 10, 128 + 10 + 10), "64", font=font, fill=(0, 0, 0), anchor='mt')
    drawing.text((128 + 10, 128 + 10 + 10), "128", font=font, fill=(0, 0, 0), anchor='mt')
    drawing.text((192 + 10, 128 + 10 + 10), "192", font=font, fill=(0, 0, 0), anchor='mt')
    drawing.text((255 + 10, 128 + 10 + 10), "255", font=font, fill=(0, 0, 0), anchor='rt')
    return hist_img


def draw_exif(img, width_height, filename, filesize, exifs, xy, font, font_color):
    w, h = width_height
    x, y = xy
    drawing = ImageDraw.Draw(img)
    drawing_text = ""
    drawing_text += "%s, %dx%d, %0.2fMiB" % (filename, w, h, filesize / 1024.0 / 1024.0) + "\n"

    # DateTime
    if exifs is None:
        drawing_text += "EXIF is None" + "\n"
        return
    if 0x0132 in exifs:
        drawing_text += "DateTime: %s" % exifs[0x0132] + "\n"
    else:
        drawing_text += "DateTime: None" + "\n"

    # Exposure info
    expinfo = ''
    if 0x829A in exifs:
        time = ''
        if exifs[0x829A].numerator > exifs[0x829A].denominator:
            if exifs[0x829A].denominator == 0:
                time = str(exifs[0x829A].numerator) + " (Maybe incorrect)"
            else:
                time = str((exifs[0x829A].numerator / exifs[0x829A].denominator))
        else:
            if exifs[0x829A].numerator == 0:
                time = str(exifs[0x829A].denominator) + " (Maybe incorrect)"
            else:
                time = "1/" + '{:.0f}'.format(Decimal(str(exifs[0x829A].denominator / exifs[0x829A].numerator)))
        expinfo += "%s  " % time
    else:
        expinfo += "None  "

    if 0x829D in exifs:
        expinfo += "f/%0.1f  " % (exifs[0x829D].numerator / exifs[0x829D].denominator)
    else:
        expinfo += "None  "

    if 0x8827 in exifs:
        expinfo += "ISO:%d  " % exifs[0x8827]
    else:
        expinfo += "None  "

    drawing_text += expinfo + "\n"

    if 0x010E in exifs:
        exif_end = exifs[0x010E].find('\x00')
        if exif_end == -1:
            info = exifs[0x010E]
        else:
            info = exifs[0x010E][:exif_end]
        if info.strip() != "":
            drawing_text += "ImageDescription: %s" % info + "\n"

    if 0x010F in exifs:
        exif_end = exifs[0x010F].find('\x00')
        if exif_end == -1:
            drawing_text += "Make: %s" % exifs[0x010F] + "\n"
        else:
            drawing_text += "Make: %s" % exifs[0x010F][:exif_end] + "\n"
    else:
        drawing_text += "Make: None" + "\n"

    if 0x0110 in exifs:
        exif_end = exifs[0x0110].find('\x00')
        if exif_end == -1:
            drawing_text += "Model: %s" % exifs[0x0110] + "\n"
        else:
            drawing_text += "Model: %s" % exifs[0x0110][:exif_end] + "\n"
    else:
        drawing_text += "Model: None" + "\n"

    exposureprogram_dict = {0: 'Not defined',
                            1: 'Manual',
                            2: 'Normal program',
                            3: 'Aperture priority',
                            4: 'Shutter priority',
                            5: 'Creative program',
                            6: 'Action program',
                            7: 'Portrait mode',
                            8: 'Landscape mode'}
    if 0x8822 in exifs:
        if exifs[0x8822] in exposureprogram_dict:
            drawing_text += "ExposureProgram: %s" % exposureprogram_dict[exifs[0x8822]] + "\n"
        else:
            drawing_text += "ExposureProgram: Other" + "\n"
    else:
        drawing_text += "ExposureProgram: None" + "\n"

    if 0x9204 in exifs:
        if exifs[0x9204].denominator != 0:
            drawing_text += "ExposureBiasValue: %0.2f EV" % (exifs[0x9204].numerator / exifs[0x9204].denominator) + "\n"

    meteringmode_dict = {0: 'unknown',
                         1: 'Average',
                         2: 'CenterWeightedAverage',
                         3: 'Spot',
                         4: 'MultiSpot',
                         5: 'Pattern',
                         6: 'Partial',
                         255: 'other'}
    if 0x9207 in exifs:
        if exifs[0x9207] in exposureprogram_dict:
            drawing_text += "MeteringMode: %s" % meteringmode_dict[exifs[0x9207]] + "\n"
        else:
            drawing_text += "MeteringMode: reserved" + "\n"
    else:
        drawing_text += "MeteringMode: None" + "\n"

    if 0x9209 in exifs:
        if exifs[0x9209] & 0x01 == 1:
            drawing_text += "Flash: Flash fired" + "\n"
        else:
            drawing_text += "Flash: Flash did not fire" + "\n"

    if 'colorSpace' in exifs:
        color_space = exifs['colorSpace']
        drawing_text += "Color space: %s" % color_space + "\n"

    drawing.multiline_text((x + 1, y + 1), drawing_text, font=font, fill=(0, 0, 0))  # Draw shadow
    drawing.multiline_text((x, y), drawing_text, font=font, fill=font_color)


def merge_imgs(input_imgs_filename, output_filename, mode, max_height, crop_size, divider_width, divider_color, font_color, show_histogram, show_file_info, font_path):
    small_font = ImageFont.truetype(font_path, 12)
    mid_font = ImageFont.truetype(font_path, 16)
    preprocessed_imgs = []  # Rotated, Color transformed images
    original_imgs_exif = []
    scaled_imgs = []
    output_width = (len(input_imgs_filename) - 1) * divider_width  # Init with image count * divider width
    for img_filename in input_imgs_filename:
        # Process every image (such as rotate, scale, crop and color transform)
        try:
            tmp_img = Image.open(img_filename)
            tmp_img.load()
        except IOError as e:
            tmp_img = Image.new("RGB", (500, 500), divider_color)
            tmp_drawing = ImageDraw.Draw(tmp_img)
            tmp_drawing.text((200, 350), "IO error", font=mid_font, fill=font_color)
        if tmp_img.format == "JPEG" or tmp_img.format == "MPO":
            exif = tmp_img.getexif()
            if 'icc_profile' in tmp_img.info:
                # Detect ICC profile
                icc = io.BytesIO()
                icc.write(tmp_img.info['icc_profile'])
                icc.seek(0)
                icc_profile = ImageCms.getOpenProfile(icc)
                exif['colorSpace'] = ImageCms.getProfileDescription(icc_profile)
                ImageCms.profileToProfile(tmp_img, icc_profile, ImageCms.createProfile("sRGB"), inPlace=1)
                icc.close()
            original_imgs_exif.append(exif)
            # Rotate image
            rotate_dict = {3: Image.ROTATE_180, 6: Image.ROTATE_270, 8: Image.ROTATE_90}
            if exif is not None and 0x0112 in exif:
                if exif[0x0112] in rotate_dict:
                    tmp_img = tmp_img.transpose(rotate_dict[exif[0x0112]])
            # tmp_img = ImageOps.exif_transpose(tmp_img) # Bug? cause TypeError: '<' not supported between instances of 'str' and 'int'
        else:
            original_imgs_exif.append(None)
        preprocessed_w, preprocessed_h = tmp_img.size
        preprocessed_imgs.append(tmp_img)

        if mode == 0:  # Scale mode
            scaled_h = preprocessed_h
            scaled_w = preprocessed_w
            if scaled_h > max_height:
                scale_ratio = max_height / scaled_h
                scaled_h = int(max_height)
                scaled_w = int(scaled_w * scale_ratio)
                scaled_img = tmp_img.resize((scaled_w, scaled_h), Image.LANCZOS)
            else:
                scaled_img = tmp_img.copy()
            scaled_imgs.append(scaled_img)
            output_width += scaled_w
        elif mode == 1:  # Crop mode
            scaled_img = tmp_img.crop(
                (int(preprocessed_w / 2 - crop_size / 2), int(preprocessed_h / 2 - crop_size / 2),
                 int(preprocessed_w / 2 + crop_size / 2), int(preprocessed_h / 2 + crop_size / 2)))
            scaled_imgs.append(scaled_img)
            output_width += int(crop_size)

    if mode == 0:  # Scale mode
        output_img = Image.new("RGB", (output_width, int(max_height)), divider_color)
    elif mode == 1:  # Crop mode
        output_img = Image.new("RGB", (output_width, int(crop_size)), divider_color)
    last_x = 0
    for i in range(0, len(input_imgs_filename)):
        last_y = 10
        if show_histogram:
            hist_img = get_hist(preprocessed_imgs[i], small_font)
            scaled_imgs[i].paste(hist_img, (10, last_y))
            _, hist_height = hist_img.size
            last_y += hist_height + 10
        if show_file_info:
            draw_exif(scaled_imgs[i],
                      preprocessed_imgs[i].size,
                      os.path.basename(input_imgs_filename[i]),  # File name
                      os.path.getsize(input_imgs_filename[i]),  # File size
                      original_imgs_exif[i],  # EXIF
                      (10, last_y),
                      mid_font,
                      font_color)
        output_img.paste(scaled_imgs[i], (last_x, 0))
        x, y = scaled_imgs[i].size
        last_x += x
        last_x += divider_width
    output_img.save(output_filename, quality=95, optimize=True, subsampling=0)


def get_image_list(directory_path):
    total_images = {}
    directorys = os.listdir(directory_path)
    for directory in directorys:
        if not directory.startswith('.') and os.path.isdir(os.path.join(directory_path, directory)):
            total_images[directory] = []

    extension_filter = ('.jpg', '.jpeg', '.bmp', '.png')
    for model, model_images in total_images.items():
        images = os.listdir(os.path.join(directory_path, model))
        for image in images:
            _, extension = os.path.splitext(image)
            if extension and extension.lower() in extension_filter:
                # Final images
                model_images.append(image)

    return total_images


def load_config(config_path):
    config_section = 'CONFIG'
    conf = configparser.ConfigParser()
    print("Config: {path}".format(path=config_path))
    conf.read(config_path)
    mode = conf.getint(config_section, 'Mode', fallback=0)
    max_height = conf.getint(config_section, 'MaxHeight', fallback=1080)
    crop_size = conf.getint(config_section, 'CropSize', fallback=800)
    divider_width = conf.getint(config_section, 'DividerWidth', fallback=3)
    divider_r = conf.getint(config_section, 'DividerR', fallback=0)
    divider_g = conf.getint(config_section, 'DividerG', fallback=0)
    divider_b = conf.getint(config_section, 'DividerB', fallback=0)
    font_r = conf.getint(config_section, 'FontR', fallback=0)
    font_g = conf.getint(config_section, 'FontG', fallback=255)
    font_b = conf.getint(config_section, 'FontB', fallback=0)
    show_histogram = conf.getboolean(config_section, 'ShowHistogram', fallback=True)
    show_file_info = conf.getboolean(config_section, 'ShowFileInfo', fallback=True)
    shuffle_mode = conf.getboolean(config_section, 'ShuffleMode', fallback=False)
    if shuffle_mode:
        # Hide info
        show_histogram = False
        show_file_info = False
    return mode, max_height, crop_size, divider_width, (divider_r, divider_g, divider_b), (font_r, font_g, font_b), show_histogram, show_file_info, shuffle_mode


def get_compare_string_func():
    def compare_string_general(first_str, second_str):
        r = operator.gt(first_str, second_str)
        if r:
            return 1
        else:
            return -1

    # Use windows compare function to keep same order in explorer
    @ctypes.WINFUNCTYPE(ctypes.wintypes.DWORD, ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPCWSTR)
    def compare_string_windows(first_str, second_str):
        return shlwapi.StrCmpLogicalW(first_str,
                                      second_str)

    system = platform.system()
    if system == "Windows":
        shlwapi = ctypes.windll.LoadLibrary("Shlwapi")
        compare_string = compare_string_windows
    else:
        compare_string = compare_string_general
    return compare_string


def main():
    app_version = 27
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    args = parser.parse_args()

    bundle_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    print('Version: {version}'.format(version=app_version))

    mode, max_height, crop_size, divider_width, divider_color, font_color, show_histogram, show_file_info, shuffle_mode = load_config(os.path.join(bundle_dir, 'conf.ini'))
    # font_path = os.path.join(bundle_dir, "simhei.ttf")
    font_path = os.path.join(bundle_dir, "SourceHanSansHWSC-Regular.otf")
    compare_string_func = get_compare_string_func()

    result_path = os.path.join(args.directory, 'Results')
    if os.path.exists(result_path):
        print("Deleting result directory...")
        shutil.rmtree(result_path)

    imgs = get_image_list(args.directory)
    last_count = -1
    for model in imgs:
        img_count = len(imgs[model])
        print('{model} : {count}'.format(model=model, count=len(imgs[model])))
        if last_count != -1 and last_count != img_count:
            print('Please check your images.')
            os.system('pause')
            exit()
        last_count = img_count
        imgs[model] = sorted(imgs[model], key=cmp_to_key(compare_string_func))

    os.mkdir(result_path)
    models = list(imgs.keys())
    models = sorted(models, key=cmp_to_key(compare_string_func))
    params = []

    for index in range(0, last_count):
        if shuffle_mode:
            random.shuffle(models)
        input_imgs = []
        for model in models:
            input_imgs.append(os.path.join(args.directory, model, imgs[model][index]))
        output_filename = '{filename}-{index}.jpg'.format(filename='-'.join(models), index=index+1)
        output_filename = os.path.join(result_path, output_filename)
        params.append((input_imgs,
                       output_filename,
                       mode,
                       max_height,
                       crop_size,
                       divider_width,
                       divider_color,
                       font_color,
                       show_histogram,
                       show_file_info,
                       font_path))

    with multiprocessing.Pool() as pool:
        result = pool.starmap(merge_imgs, params)
    print('Done!')
    os.system('pause')


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
