import os
import shutil
import urllib.request

import yaml
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
import cv2
import logging
from tqdm import tqdm
import random
from PIL import Image, ImageDraw, ImageFont


from utils.paths import DATA_DIR
import re


def ensure_model_downloaded(model_name: str):
    model_path = DATA_DIR / "models" / (model_name + '.pt')

    if not model_path.exists():
        print(f"Скачиваем модель {model_name}...")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/ultralytics/assets/releases/latest/download/{model_name}.pt"
        urllib.request.urlretrieve(url, model_path)

    return str(model_path)


def decode_unicode_escape(text):
    """Преобразует '\u043A\u043B\u044E\u0447' в 'ключ'"""
    return re.sub(r'\\u([\da-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)


def setup_logging(log_file=DATA_DIR / 'dataset_preparation.log'):
    """Настройка логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler()
        ]
    )


def prepare_yolo_dataset(
        json_path,
        images_source_dir,
        dir_names,
        output_base_dir="data",
        class_names=None,
        train_ratio=0.8,
        seed=42,
        default_img_ext=".jpg",
        copy_files=True,
        test=False
):
    """
    Полностью подготавливает датасет для YOLO из JSON-аннотаций.

    Параметры:
        json_path (str): Путь к JSON-файлу с метками.
        images_source_dir (str): Папка с исходными изображениями.
        output_base_dir (str): Базовая папка для выходных данных (по умолчанию 'data').
        class_names (list): Список классов (например, ['cat', 'dog']). Если None, будет извлечен из JSON.
        train_ratio (float): Доля данных для обучения (0.8 = 80% train, 20% valid).
        seed (int): Random seed для воспроизводимости.
        default_img_ext (str): Расширение изображений по умолчанию.
        copy_files (bool): Копировать файлы (True) или создавать симлинки (False).
    """
    setup_logging()
    random.seed(seed)

    # Создаем структуру папок
    dirs = {
        'train_images': os.path.join(output_base_dir, 'train', 'images'),
        'train_labels': os.path.join(output_base_dir, 'train', 'labels'),
        'val_images': os.path.join(output_base_dir, 'val', 'images'),
        'val_labels': os.path.join(output_base_dir, 'val', 'labels'),
        'test_images': os.path.join(output_base_dir, 'test', 'images'),
        'test_labels': os.path.join(output_base_dir, 'test', 'labels'),
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    # Загружаем JSON-данные
    with open(json_path) as f:
        data = json.load(f)

    output_dir = DATA_DIR / "annotated_dataset"

    # Собираем все изображения
    all_images = []
    for dir_name in dir_names:
        try:
            real_dir_name = str(output_dir / dir_name)
            images = data[real_dir_name]
            for img_name in images.keys():
                img_name_ext = img_name if '.' in img_name else img_name + default_img_ext
                img_path = os.path.join(images_source_dir, dir_name, img_name_ext)
                if os.path.exists(img_path):
                    all_images.append((img_path, real_dir_name, img_name))
                else:
                    logging.warning(f"Изображение не найдено: {img_path}")
        except Exception as e:
            logging.error(f"Ошибка при загрузке папки {dir_name}: {str(e)}")

    # Разделяем на train/val
    if not test:
        train_images, val_images = train_test_split(
            all_images, train_size=train_ratio, random_state=seed
        )
    else:
        test_images = all_images

    # Функция для обработки и копирования файлов
    def process_batch(batch, target_img_dir, target_label_dir):
        for img_path, folder_name, img_name in tqdm(batch, desc="Обработка"):
            try:
                # Обработка изображения
                img_name_ext = img_name if '.' in img_name else img_name + default_img_ext
                target_img_path = os.path.join(target_img_dir, img_name_ext)

                if copy_files:
                    shutil.copy2(img_path, target_img_path)
                else:
                    os.symlink(os.path.abspath(img_path), target_img_path)

                # Обработка меток
                labels = data[folder_name][img_name]
                txt_filename = Path(img_name).stem + ".txt"
                txt_path = os.path.join(target_label_dir, txt_filename)

                img = cv2.imread(img_path)
                if img is None:
                    raise ValueError(f"Не удалось загрузить изображение: {img_path}")
                h, w = img.shape[:2]

                with open(txt_path, 'w') as f:
                    for label in labels:
                        x1, y1, x2, y2 = label['coords']
                        class_name = label['text']
                        ratio = label.get('ratio', 1.0)

                        # Проверка класса
                        if class_names and class_name not in class_names:
                            # Игнорируем остальные классы
                            continue

                        # Конвертация в YOLO-формат
                        x1, y1, x2, y2 = [x / ratio for x in [x1, y1, x2, y2]]
                        # x1, y1, x2, y2 = min(x1, w), min(y1, h), min(x2, w), min(y2, h)
                        center_x = max(min(((x1 + x2) / 2) / w, 1.0), 0.0)
                        center_y = max(min(((y1 + y2) / 2) / h, 1.0), 0.0)
                        width = max(min((x2 - x1) / w, 1.0), 0.0)
                        height = max(min((y2 - y1) / h, 1.0), 0.0)

                        class_id = class_names.index(class_name) if class_names else 0
                        f.write(f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}\n")

            except Exception as e:
                logging.error(f"Ошибка при обработке {img_path}: {str(e)}")

    # Обрабатываем train/val/test
    if not test:
        process_batch(train_images, dirs['train_images'], dirs['train_labels'])
        process_batch(val_images, dirs['val_images'], dirs['val_labels'])
    else:
        process_batch(test_images, dirs['test_images'], dirs['test_labels'])

    # Автоматическое определение классов, если не заданы
    if class_names is None:
        class_names = sorted(list(set(
            label['text']
            for folder_data in data.values()
            for img_labels in folder_data.values()
            for label in img_labels
        )))
        logging.info(f"Автоопределенные классы: {class_names}")

    # Создаем / Обновляем data.yaml
    if not test:
        yaml_content = {
            'train': os.path.abspath(os.path.join(output_base_dir, 'train', 'images')),
            'val': os.path.abspath(os.path.join(output_base_dir, 'val', 'images')),
            'nc': len(class_names),
            'names': class_names
        }

        yaml_path = os.path.join(output_base_dir, 'data.yaml')
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f, sort_keys=False)

        logging.info(f"Датасет успешно подготовлен в {output_base_dir}")
        logging.info(f"Train images: {len(train_images)}, Val images: {len(val_images)}")

        logging.info(f"YAML config создан: {yaml_path}")
    else:
        yaml_path = os.path.join(output_base_dir, 'data.yaml')

        with open(yaml_path, 'r') as f:
            yaml_content = yaml.safe_load(f)

        yaml_content['test'] = os.path.abspath(os.path.join(output_base_dir, 'test', 'images'))

        yaml_path = os.path.join(output_base_dir, 'data.yaml')
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_content, f, sort_keys=False)

        logging.info(f"Датасет успешно подготовлен в {output_base_dir}")
        logging.info(f"Test images: {len(test_images)}")

        logging.info(f"YAML config обновлен: {yaml_path}")


def visualize_yolo_labels(image_path, label_path, class_names, output_dir="debug"):
    os.makedirs(output_dir, exist_ok=True)

    # Загружаем изображение
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # Пытаемся использовать системный шрифт с поддержкой кириллицы
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Читаем метки
    with open(label_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Рисуем каждый bbox
    for line in lines:
        parts = line.strip().split()
        if len(parts) != 5:
            continue

        class_id, cx, cy, bw, bh = map(float, parts)
        class_id = int(class_id)
        w, h = image.size

        # Конвертация координат
        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)

        # Рисуем прямоугольник
        draw.rectangle([x1, y1, x2, y2], outline="green", width=2)

        # Получаем название класса с декодированием Unicode
        class_name = decode_unicode_escape(class_names[class_id])

        # Добавляем текст
        draw.text((x1, y1 - 25), class_name, fill="green", font=font)

    # Сохраняем результат
    output_path = os.path.join(output_dir, os.path.basename(image_path))
    image.save(output_path)
    print(f"Результат сохранён в: {output_path}")
