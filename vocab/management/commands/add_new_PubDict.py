from django.core.management.base import BaseCommand
from django.apps import apps
import tkinter as tk
from tkinter import filedialog
import json
from django.utils.text import slugify

root = tk.Tk()
root.withdraw()  # Hide the main window

# Ask the user to select a file
file_path = filedialog.askopenfilename(
    title="Select File",
    filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
)

with open(file_path, "r", encoding="utf-8") as file:
    new_words = json.load(file)

# Get the name for the new public dictionary
dict_name = input('Enter the name for the new public dictionary: ')

Word = apps.get_model('vocab', 'Word')
PubDict = apps.get_model('vocab', 'PubDict')
UsageExample = apps.get_model('vocab', 'UsageExample')


class Command(BaseCommand):
    help = 'Add a new public dictionary from a JSON file on disk.'

    def handle(self, *args, **kwargs):
        pub_dict, created = PubDict.objects.get_or_create(dict_name=dict_name, published=True, slug=slugify(dict_name))

        for word in new_words:
            word_obj = Word.objects.create(
                eng_word=word['eng_word'],
                rus_word=word['rus_word'],
                # sample1_eng=word['eng_sample'],
                # sample1_rus=word['rus_sample'],

            )

            UsageExample.objects.create(
                word=word_obj,
                eng_text=word['eng_sample'],
                rus_text=word['rus_sample'],
            )

            pub_dict.words.add(word_obj)

            self.stdout.write(self.style.SUCCESS(
                f"В моделе Word создана запись ({dict_name}): {word['eng_word']} - {word['rus_word']}"))
