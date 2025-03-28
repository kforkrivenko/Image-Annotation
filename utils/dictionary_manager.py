import json
import os
from collections import defaultdict


class DictionaryManager:
    def __init__(self, save_path="annotation_dictionary.json", max_suggestions=10):
        self.save_path = save_path
        self.word_counts = defaultdict(int)
        self.max_suggestions = max_suggestions  # Теперь настраиваемое значение
        self.load()

    def get_all_suggestions(self):
        """Возвращает ВСЕ аннотации, отсортированные по частоте"""
        return sorted(self.word_counts.items(),
                      key=lambda x: (-x[1], x[0]))

    def add_annotation(self, text):
        """Добавляет текст в словарь и увеличивает счётчик"""
        text = text.strip()
        if text:
            self.word_counts[text] += 1
            self.save()

    def get_suggestions(self, prefix="", limit=None):
        """
        Возвращает подсказки с возможностью фильтрации по префиксу
        limit: если None - использует max_suggestions
        """
        limit = limit or self.max_suggestions
        sorted_words = sorted(
            self.word_counts.items(),
            key=lambda x: (-x[1], x[0])  # Сортировка по частоте, затем по алфавиту
        )

        if prefix:
            suggestions = [w for w, cnt in sorted_words if w.lower().startswith(prefix.lower())]
        else:
            suggestions = [w for w, cnt in sorted_words]

        return suggestions[:limit]

    def save(self):
        """Сохраняет словарь на диск"""
        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(dict(self.word_counts), f, indent=2, ensure_ascii=False)

    def load(self):
        """Загружает словарь с диска"""
        if os.path.exists(self.save_path):
            with open(self.save_path, 'r', encoding='utf-8') as f:
                try:
                    self.word_counts.update(json.load(f))
                except json.JSONDecodeError:
                    pass  # Если файл поврежден, начинаем с чистого словаря
