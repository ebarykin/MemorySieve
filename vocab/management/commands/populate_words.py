from django.core.management.base import BaseCommand
from django.apps import apps

Word = apps.get_model('vocab', 'Word')
MyDict = apps.get_model('vocab', 'MyDict')


class Command(BaseCommand):
    help = 'Populate Word model with data from MyDict'

    def handle(self, *args, **kwargs):
        a = Word.objects.all()
        self.stdout.write(self.style.SUCCESS(f"Модель Word: {a} "))

        my_dicts = MyDict.objects.all()  # Получите ваши данные из MyDict

        for my_dict in my_dicts:
            Word.objects.create(
                eng_word=my_dict.eng_word,
                rus_word=my_dict.rus_word,
                sample1_eng=my_dict.sample1_eng,
                sample1_rus=my_dict.sample1_rus,

            )
            self.stdout.write(self.style.SUCCESS(f"В моделе Word: {my_dict.eng_word}"))