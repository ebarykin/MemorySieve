import random
from django.contrib.auth.models import User
from django.db.models import QuerySet, F
from django.core.cache import cache
from vocab.models import PersDict, Word, PubDict, Profile, History, Reward
from typing import List, Union, Optional, Iterable
from vocab.services import dict_services
from datetime import datetime


class UserService:
    def __init__(self, user: User, selected_dict_names: Optional[List[str]] = None):
        self.user = user
        self.profile = Profile.objects.get(user=user)
        self.selected_dict_names = (selected_dict_names if selected_dict_names else self.profile.selected_dict_names)

    def get_user_opted_dicts(self) -> QuerySet[PubDict]:
        """ Получить все подключенные словари пользователя. """

        user_opted_dicts = self.profile.public_dicts.all().order_by('dict_name')
        return user_opted_dicts

    def get_user_random_word(self) -> Optional[Word]:
        """ Выбрать случайное слово из активных словарей пользователя. """

        active_dicts = get_user_dict_obj_list(self.selected_dict_names, self.user)
        words = dict_services.MyDictService.get_user_active_hist_cond_words2(self.user, active_dicts)
        random_word = take_random_word_from_list(self.user, words)
        return random_word

    def get_all_user_words(self) -> Optional[QuerySet]:
        """ Get all words from the user's personal and opted public dictionaries. """

        pers_dict, _ = PersDict.objects.get_or_create(user=self.user)
        personal_words = pers_dict.words.all()
        public_dicts = self.profile.public_dicts.all()
        public_words = Word.objects.filter(words__in=public_dicts)
        words = public_words | personal_words
        return words

    def has_entry_today(self, word: Word) -> bool:
        """ """

        today = datetime.today()
        entry_exist = History.objects.filter(word=word, user=self.user, ch_date=today).exists()
        return entry_exist

    def user_active_words_cache_update(self) -> None:
        """ """

        cache_key = f'user_active_words_{self.user.id}'
        words = cache.get(cache_key)
        words.pop()
        cache.set(cache_key, words, timeout=3600)

    def log_user_entry(self, word: Word, result: bool) -> None:
        """ """

        today = datetime.today()
        history_entry = History(user=self.user, word=word, ch_date=today, ch_result=result)
        history_entry.save()

    def update_coins(self, amount: int) -> None:
        """ """

        self.profile.coins = F('coins') + amount
        self.profile.save(update_fields=['coins'])

    def update_treasure(self, amount: int) -> None:
        """ """

        self.profile.treasure = F('treasure') + amount
        self.profile.save(update_fields=['treasure'])

    def reset_treasure(self) -> None:
        """ """

        self.profile.treasure = 0
        self.profile.save()

    def update_selected_dict_names(self, selected_dict_names: List[str]) -> None:
        """ Обновить активные словари пользователя в экземпляре класса и сохранить в модель."""

        self.selected_dict_names = selected_dict_names
        self.profile.selected_dict_names = selected_dict_names
        self.profile.save()

    def check_if_rewarded(self):

        reward_id = self.profile.reward_id

        return reward_id


def take_random_word_from_list(user: User, words: List[Word]) -> Optional[Word]:
    """ Выбрать случайное слово из списка и обновить список в кэше пользователя. """

    if words:
        rand_idx = random.randint(0, len(words) - 1)
        words[rand_idx], words[-1] = words[-1], words[rand_idx]
        rand_word = words[-1]
        cache_key = f'user_active_words_{user.id}'
        cache.set(cache_key, words, timeout=3600)
        return rand_word
    return None


def get_user_dict_obj_list(active_dicts: list[str], user: User) -> list[Union[PubDict, PersDict]]:
    """ Получить список объектов словарей (PubDict, PersDict) пользователя. """

    dicts = []
    for dict_name in active_dicts:
        if dict_name != 'personal':
            dict_instance = PubDict.objects.get(dict_name=dict_name)
        else:
            dict_instance, _ = PersDict.objects.get_or_create(user=user)
        dicts.append(dict_instance)
    return dicts


def get_user_pub_dicts(user: User) -> QuerySet[PubDict]:
    profile = Profile.objects.get(user=user)
    user_pub_dicts = profile.public_dicts.all()
    return user_pub_dicts


def get_user_pers_dict(user: User) -> PersDict:
    user_pers_dict, created = PersDict.objects.get_or_create(user=user)
    return user_pers_dict


def get_user_words_by_lvl(user: User, lvl: int) -> List[Word]:
    user_pub_dicts = get_user_pub_dicts(user)
    user_pers_dict = get_user_pers_dict(user)
    words_by_lvl = []

    def get_words_by_lvl(dicts: Union[QuerySet[PersDict, PubDict], Iterable[Union[PersDict, PubDict]]]) -> None:
        for dictionary in dicts:
            q_ok_set = dict_services.MyDictService.get_q_ok_set(user, dictionary)
            for item in q_ok_set:
                print(item, item.q_ok, type(item.q_ok))
            if lvl == 7:
                words_by_lvl.extend(q_ok_set.filter(q_ok__gte=lvl))
            else:
                words_by_lvl.extend(q_ok_set.filter(q_ok=lvl))

    get_words_by_lvl(user_pub_dicts)
    get_words_by_lvl((user_pers_dict,))

    return words_by_lvl


def get_random_reward():
    reward = Reward.objects.order_by('?').first()
    reward.path = Reward.get_file_path(reward)
    return reward


def get_reward_by_id(reward_id):
    reward = Reward.objects.get(id=reward_id)
    reward.path = Reward.get_file_path(reward)
    return reward
