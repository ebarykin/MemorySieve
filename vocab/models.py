from typing import Tuple
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import UniqueConstraint
from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from slugify import slugify
import os


def default_selected_dict_names():
    return ['personal']


class Profile(models.Model):
    HINT_CHOICES = [
        ('frst_30', 'Первые 30 % букв'),
        ('rnd_30', '30 % букв в произвольном порядке'),
        ('all_cap', 'Слово целиком. Большие буквы.'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(upload_to='users/%Y/%m/%d/', blank=True)
    interests = models.TextField('interests', blank=True)
    public_dicts = models.ManyToManyField('vocab.PubDict', related_name='pub_dicts', blank=True)
    selected_dict_names = models.JSONField(default=default_selected_dict_names)
    coins = models.IntegerField(blank=True, null=True, default=0)
    treasure = models.IntegerField(blank=True, null=True, default=0)
    reward_id = models.IntegerField(blank=True, null=True, default=0)
    hint_type = models.CharField('hint_type', max_length=50, choices=HINT_CHOICES, blank=True)
    objects = models.Manager()

    def __str__(self):
        return f'Profile of {self.user}'


class UniqueEngWord(models.Model):
    u_eng_word = models.CharField('English', max_length=50, unique=True, db_index=True)

    def __str__(self):
        return self.u_eng_word


class Word(models.Model):
    PART_OF_SPEECH = [
        ('noun', 'noun'),
        ('verb', 'verb'),
        ('adjective', 'adjective'),
        ('adverb', 'adverb'),
        ('preposition', 'preposition'),
        ('phrasal verb', 'phrasal verb'),
        ('conjunction', 'conjunction'),
        ('interjection', 'interjection'),
        ('article', 'article'),
    ]

    eng_word = models.CharField('English', max_length=50, db_index=True)
    u_eng_word = models.ForeignKey(UniqueEngWord, on_delete=models.CASCADE, related_name='words')

    rus_word = models.CharField('Russian', max_length=50, blank=True)
    part_of_speech = models.CharField('Часть речи', max_length=50, choices=PART_OF_SPEECH, blank=True)
    synonym = models.CharField('Синоним', max_length=50, blank=True, default='')
    hint = models.TextField('Подсказка', blank=True)
    pers_dict = models.ForeignKey('PersDict', on_delete=models.CASCADE, null=True, blank=True, related_name='words')

    objects = models.Manager()

    def __str__(self):
        return self.eng_word

    def get_absolute_url(self):
        """
        Generates the absolute URL for this object, considering its associated PubDict.

        Returns:
            str: The absolute URL.
        """

        dictionary = PubDict.objects.filter(words=self.pk).first()
        if dictionary:
            dictionary_name = dictionary.slug
        else:
            dictionary_name = 'personal'
        return reverse('card', args=[dictionary_name, self.u_eng_word])


class UsageExample(models.Model):
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='usage_examples')
    eng_text = models.TextField('English example', blank=True)
    rus_text = models.TextField('Русский пример', blank=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateField(default=timezone.now)


class PersDict(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    objects = models.Manager()

    def check_word_existence(self, eng_word_from_form: str) -> Tuple[bool, str]:
        word_exists = self.words.filter(u_eng_word__u_eng_word=eng_word_from_form).exists()
        if word_exists:
            word_url = reverse('card', args=['personal', eng_word_from_form])
            message = (
                f"В вашем персональном словаре уже есть слово {eng_word_from_form}. "
                f"Карточка слова: <a href='{word_url}'>{eng_word_from_form}</a>"
            )
            return True, message
        return False, ""


class RussianAutoSlugField(models.SlugField):
    def __init__(self, populate_from=None, *args, **kwargs):
        self.populate_from = populate_from
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if not value:
            if self.populate_from:
                value = getattr(model_instance, self.populate_from)
                if value:
                    # Используем python-slugify для обработки русских символов
                    slug_value = slugify(value)
                    setattr(model_instance, self.attname, slug_value)
        return super().pre_save(model_instance, add)


class PubDict(models.Model):
    LVL = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('All level', 'All level')]

    dict_name = models.CharField('Name', max_length=50, db_index=True, unique=True)
    description = models.TextField('Description', blank=True)
    slug = RussianAutoSlugField(populate_from='dict_name')
    level = models.CharField('Level', max_length=20, choices=LVL, blank=True)
    published = models.BooleanField(default=False)
    picture = models.ImageField(upload_to='dictionary_images/', blank=True, null=True)
    words = models.ManyToManyField(Word, related_name='words')
    history = models.ManyToManyField('History', related_name='pub_dicts', blank=True)
    objects = models.Manager()

    def __str__(self):
        return self.dict_name

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Извлекаем пользователя из переданных аргументов
        print(f"user - editor: {user}")
        if user and not User.objects.filter(groups__name='Editors', id=user.id).exists():
            raise PermissionDenied("У вас нет прав на изменение этой модели")

        super(PubDict, self).save(*args, **kwargs)

    def check_word_existence(self, eng_word_from_form: str) -> Tuple[bool, str]:
        word_exists = self.words.filter(u_eng_word__u_eng_word=eng_word_from_form).exists()
        if word_exists:
            word_url = reverse('card', args=[self.slug, eng_word_from_form])
            message = (
                f"В словаре {self.dict_name} уже есть слово {eng_word_from_form}. "
                f"Карточка слова: <a href='{word_url}'>{eng_word_from_form}</a>"
            )
            return True, message
        return False, ""


class History(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    ch_date = models.DateField()
    ch_result = models.BooleanField()
    objects = models.Manager()

    def __str__(self):
        return str(self.word) + str(self.ch_date)


class WordPict(models.Model):
    word = models.ForeignKey(Word, on_delete=models.CASCADE)
    picture = models.ImageField(upload_to='word_images/', blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.word}"


class WordPronunciation(models.Model):
    ACCENT_CHOICES = [
        ('US', 'American'),
        ('UK', 'British'),
    ]

    unique_word = models.ForeignKey(UniqueEngWord, on_delete=models.CASCADE, related_name='pronunciations', default='2')
    accent = models.CharField(max_length=2, choices=ACCENT_CHOICES)
    audio_file = models.FileField(upload_to='word_pronunciations/')
    transcription = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['unique_word', 'accent'], name='unique_word_accent')
        ]

    def __str__(self):
        return f'{self.unique_word} ({self.get_accent_display()})'


class Reward(models.Model):
    img_path = models.CharField(max_length=255)
    earned_coins = models.IntegerField(default=0, verbose_name='Количество монет')
    message = models.CharField(max_length=255, verbose_name='Сообщение')

    def get_file_path(self):
        return os.path.join(settings.BASE_DIR, 'static', self.img_path)

    @property
    def formatted_message(self):
        return self.message.format(coins=self.earned_coins)
