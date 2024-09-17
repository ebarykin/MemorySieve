import random
import requests
import httpx
from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup
from datetime import date
from django.db.models import QuerySet, Max
from django.db import transaction
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from slugify import slugify

from vocab.models import Word, PubDict, PersDict, History, WordPronunciation, UniqueEngWord, WordPict, UsageExample
from typing import Optional, Tuple, Union, Dict
from urllib.parse import urlencode, urlparse

from vocab.services import dict_services


def check_duplicate(dict_name: str, eng_word_from_form: str, word: Word, user=None) -> Tuple[bool, str]:
    if word.u_eng_word.u_eng_word != eng_word_from_form:
        dict_ = dict_services.get_dict_instance(dict_name, user)
        duplicate_found, message = dict_.check_word_existence(eng_word_from_form)
        if duplicate_found:
            return True, message
    return False, ''


def save_word_from_form(word_form_cl_data: Dict[str, str], usage_form_cl_data: Dict[str, str], dict_: Union[PubDict, PersDict]) -> Tuple[bool, str]:
    dict_type = dict_._meta.model_name
    eng_word_from_form = word_form_cl_data["u_eng_word"]

    word_exist, message = dict_.check_word_existence(eng_word_from_form)
    if word_exist:
        return False, message

    unique_word, created = UniqueEngWord.objects.get_or_create(u_eng_word=eng_word_from_form)
    try:
        with transaction.atomic():
            word_instance = Word.objects.create(
                u_eng_word=unique_word,
                rus_word=word_form_cl_data.get("rus_word", ""),
                synonym=word_form_cl_data.get("synonym", ""),
                hint=word_form_cl_data.get("hint", ""),
                part_of_speech=word_form_cl_data.get("part_of_speech", "")
            )
            UsageExample.objects.create(
                word=word_instance,
                eng_text=usage_form_cl_data.get("eng_text", ""),
                rus_text=usage_form_cl_data.get("rus_text", "")
            )
            dict_.words.add(word_instance)

    except Exception as e:
        message = f"Ошибка при сохранении {eng_word_from_form}. Попробуйте снова. {e}"
        return False, message

    if dict_type == 'persdict':
        word_url = reverse('card', args=['personal', eng_word_from_form])
        return True, f"Слово {eng_word_from_form} успешно создано в вашем персональном словаре. " \
                     f"Карточка слова: <a href='{word_url}'>{eng_word_from_form}</a>"
    else:
        word_url = reverse('card', args=[dict_.dict_name, eng_word_from_form])
        return True, f"В словарь {dict_.dict_name} успешно добавлено слово {eng_word_from_form}. " \
                     f"Карточка слова: <a href='{word_url}'>{eng_word_from_form}</a>"


def delete_word(word):
    u_eng_word = word.u_eng_word
    with transaction.atomic():
        word.delete()
        if not Word.objects.filter(u_eng_word=u_eng_word).exists():
            u_eng_word.delete()


def get_word_instance(dict_name: str, u_eng_word: str, user):
    if dict_name == 'personal':
        pers_dict = get_object_or_404(PersDict, user=user)
        word = get_object_or_404(Word, u_eng_word__u_eng_word=u_eng_word, pers_dict=pers_dict)
    else:
        pub_dictionary = get_object_or_404(PubDict, slug=dict_name)
        word = get_object_or_404(pub_dictionary.words.all(), u_eng_word__u_eng_word=u_eng_word)
    return word


def get_word_picture(word: Word) -> Optional[WordPict]:
    """Retrieves the associated WordPict instance for a given Word object. """

    try:
        word.pict = WordPict.objects.filter(word=word).order_by('-id').first()
    except WordPict.DoesNotExist:
        word.pict = None
    return word.pict


def add_dict_name_to_words(user_words: QuerySet) -> QuerySet:
    """ Add 'dict_name' field to each word in the QuerySet. """

    pub_dicts = PubDict.objects.all()
    for word in user_words:
        pub_dict = pub_dicts.filter(words=word).first()
        if pub_dict:
            word.dict_name = pub_dict.slug
        else:
            word.dict_name = 'personal'
    return user_words


def get_last_nok(word: Word, user: User) -> Optional[date]:
    """ Retrieves the date of the last unsuccessful check (ch_result=False) for the given word."""

    last_nok = History.objects.filter(
        word=word,
        user=user,
        ch_result=False
    ).aggregate(
        last_false_date=Max('ch_date')
    )['last_false_date']

    return last_nok


def get_q_ok(word: Word, user: User) -> int:
    """
    Calculates the number of successful checks (ch_result=True) for the given word and user.

    If there's a previous unsuccessful check (ch_result=False), it counts successful checks
    that occurred after that date; otherwise, it counts all successful checks.
    last_nok = get_last_nok(word, user)
    """

    last_nok = get_last_nok(word, user)
    if last_nok:           # Если есть проверка со статусом False, то считаем кол-во True после этой даты
        count_after_false = History.objects.filter(
            word=word,
            user=user,
            ch_result=True,
            ch_date__gt=last_nok
        ).count()
    else:                 # Если нет проверок со статусом False, то считаем просто количество проверок со статусом True
        count_after_false = History.objects.filter(
            word=word,
            user=user,
            ch_result=True
        ).count()
    return int(count_after_false)


class HintService:
    @staticmethod
    def frst_30(eng_word):
        k = len(eng_word) // 3
        hint_variant = []
        for letter in eng_word[:k]:
            hint_variant.append(letter + " ")

        for i in range(len(eng_word) - k):
            hint_variant.append("_ ")
        hint_variant = ''.join(hint_variant)
        return hint_variant

    @staticmethod
    def rnd_30(eng_word):
        # reservoir sampling, в учебных целях
        k = len(eng_word) // 3
        inp = [x for x in range(len(eng_word))]
        out = [x for x in range(k)]
        for j in range(k, len(eng_word)):
            index = random.randint(0, j)
            if index < k:
                out[index] = inp[j]

        hint_variant = ['_ ' for _ in range(len(eng_word))]
        for i in out:
            hint_variant[i] = eng_word[i] + " "
        hint_variant = ''.join(hint_variant)
        return hint_variant

    @staticmethod
    def all_cap(eng_word):
        hint_variant = eng_word.upper()
        return hint_variant

    @staticmethod
    def get_hint(eng_word, hint_type):
        hint_functions = {
            'frst_30': HintService.frst_30,
            'rnd_30': HintService.rnd_30,
            'all_cap': HintService.all_cap,
        }
        hint_function = hint_functions.get(hint_type, HintService.rnd_30)
        hint_variant = hint_function(eng_word)

        return hint_variant


class URLService:
    @staticmethod
    def get_oxf_url(eng_word):
        """ get url of word definition """
        baseurl = 'https://www.oxfordlearnersdictionaries.com/definition/english/'
        eng_word.lower()
        print(eng_word, eng_word.lower())
        return baseurl + slugify(eng_word)


    @staticmethod
    def get_oxf_data(u_eng_word):
        url = URLService.get_oxf_url(u_eng_word)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers)
            oxf_data = {'url': url}
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                phons_br_found = soup.find('div', class_='phons_br')
                if phons_br_found:
                    audio_br = soup.find('div', class_='sound audio_play_button pron-uk icon-audio')['data-src-mp3']
                    audio_us = soup.find('div', class_='sound audio_play_button pron-us icon-audio')['data-src-mp3']
                    oxf_data['audio_url_br'] = audio_br if audio_br else None
                    oxf_data['audio_url_us'] = audio_us if audio_us else None

                    # скрапим транскрипцию
                    phons_br_element = soup.find('div', class_='phons_br')
                    phons_n_am_element = soup.find('div', class_='phons_n_am')
                    oxf_data['phons_br'] = phons_br_element.text if phons_br_element else None
                    oxf_data['phons_us'] = phons_n_am_element.text if phons_n_am_element else None

            else:
                print("Ошибка:", response.status_code)

            return oxf_data
        except requests.exceptions.RequestException as e:
            print("Error fetching data from Oxford Learner's Dictionaries:", e)
            return {'error': e}

    @staticmethod
    async def save_oxf_data_to_db(u_eng_word, oxf_data):

        async def download_audio(url):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
            }

            async with httpx.AsyncClient(headers=headers) as client:
                try:
                    response = await client.get(url)
                    response.raise_for_status()  # Проверка на успешный статус
                    if response.status_code == 200:
                        file_name = urlparse(url).path.split('/')[-1]
                        return ContentFile(response.content, file_name)
                except httpx.HTTPStatusError as exc:
                    print(f"HTTP error occurred: {exc.response.status_code} - {exc.request.url}")
                except httpx.RequestError as exc:
                    print(f"An error occurred while requesting {exc.request.url}: {exc}")
            return None

        # Проверяем, что все необходимые данные не пустые
        if all([oxf_data.get('audio_url_br'), oxf_data.get('audio_url_us'),
                oxf_data.get('phons_br'), oxf_data.get('phons_us')]):

            if oxf_data['audio_url_br'] and oxf_data['phons_br']:  # Обработка британского произношения
                audio_file_br = await download_audio(oxf_data['audio_url_br'])
                await sync_to_async(WordPronunciation.objects.update_or_create)(
                    unique_word=u_eng_word,
                    accent='UK',
                    defaults={
                        'audio_file': audio_file_br,
                        'transcription': oxf_data['phons_br']
                    }
                )

            if oxf_data['audio_url_us'] and oxf_data['phons_us']:  # Обработка американского произношения
                audio_file_us = await download_audio(oxf_data['audio_url_us'])
                await sync_to_async(WordPronunciation.objects.update_or_create)(
                    unique_word=u_eng_word,
                    accent='US',
                    defaults={
                        'audio_file': audio_file_us,
                        'transcription': oxf_data['phons_us']
                    }
                )


class WordController:
    def __init__(self, hint, audio_url):
        self.hint_service = hint
        self.url_service = audio_url

    def get_hint(self, word, hint_type):
        return self.hint_service.get_hint(word, hint_type)

    def get_oxf_data(self, word):
        return self.url_service.get_oxf_data(word)


# Использование в представлениях или других частях приложения:
hint_service = HintService()
oxf_service = URLService()
word_controller = WordController(hint_service, oxf_service)
