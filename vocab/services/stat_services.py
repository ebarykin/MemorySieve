import datetime
from typing import Tuple, Dict, Any, List, Iterable, Union, Optional
from django.db.models.query import QuerySet
from django.contrib.auth.models import User
from django.db.models import F, Count, Case, When
from vocab.models import History, PersDict, PubDict, Profile
from .plot_helpers import CalendarPlot
from vocab.services import user_services, dict_services


def get_user_statistics(user) -> Dict[str, Any]:
    """ Получить статистику по данным пользователя"""
    print('0')
    words_stat = get_user_words_stat(user)
    print('1')
    pers_words_qty, pub_words_qty = get_user_words_qnt(user)
    total_words_qty = pers_words_qty + pub_words_qty
    data_points = create_data_points(words_stat)
    words_learned = words_stat['7']
    max_strike = 0 #get_user_max_strike(user)
    active_days_count = History.objects.filter(user=user).values('ch_date').distinct().count()
    calendar_img = CalendarPlot().create_plot(user)

    return {
        'words_stat': words_stat,
        'pers_words_qty': pers_words_qty,
        'pub_words_qty': pub_words_qty,
        'total_words_qty': total_words_qty,
        'data_points': data_points,
        'words_learned': words_learned,
        'max_strike': max_strike,
        'active_days_count': active_days_count,
        'calendar_img': calendar_img,
    }


def get_user_words_stat(user: User) -> Dict[str, int]:
    """ Получить словарь с количеством слов пользователя по каждому уровню """

    user_pub_dicts = user_services.get_user_pub_dicts(user)
    user_pers_dict = user_services.get_user_pers_dict(user)

    user_words_stat = {}

    def get_dicts_stat(dicts: Union[QuerySet, Iterable[Union[PersDict, PubDict]]]) -> Optional[None]:
        for dictionary in dicts:
            dictionary.q_ok_set = dict_services.MyDictService.get_q_ok_set(user, dictionary)
            counts_by_level = {
                '0': Count(Case(When(q_ok=0, then=1))),
                '1': Count(Case(When(q_ok=1, then=1))),
                '2': Count(Case(When(q_ok=2, then=1))),
                '3': Count(Case(When(q_ok=3, then=1))),
                '4': Count(Case(When(q_ok=4, then=1))),
                '5': Count(Case(When(q_ok=5, then=1))),
                '6': Count(Case(When(q_ok=6, then=1))),
                '7': Count(Case(When(q_ok__gte=7, then=1))),
            }

            levels = dictionary.q_ok_set.aggregate(**counts_by_level)
            for level, count in levels.items():
                user_words_stat[level] = user_words_stat.get(level, 0) + count

    get_dicts_stat(user_pub_dicts)
    get_dicts_stat((user_pers_dict,))

    return user_words_stat


def create_data_points(words_stat: Dict[str, int]) -> List[Dict[str, Any]]:
    """Подготовка данных для Doughnut Chart"""

    data_points = []
    for lvl, count in words_stat.items():
        if count:
            data_points.append({"label": 'Уровень ' + lvl, "y": count})
    return data_points


def get_user_words_qnt(user: User) -> Tuple[int, int]:
    """ Получить количество слов в словарях (PubDicts, Personal) пользователя"""

    profile = Profile.objects.get(user=user)
    dicts = profile.public_dicts.all()
    all_pub_words_query = PubDict.objects.filter(pk__in=[pub_dict.pk for pub_dict in dicts]).values('words')
    unique_pub_words_query = all_pub_words_query.distinct()
    pub_words_qty = unique_pub_words_query.count()
    pers_words_qty = PersDict.objects.filter(user=user).aggregate(total_words=Count('words'))['total_words']
    return pers_words_qty, pub_words_qty


def get_user_max_strike(user: User) -> int:
    from django.db.models import Max, OuterRef, Subquery
    from datetime import timedelta

    # Создаем подзапрос для получения предыдущей даты для каждой записи пользователя
    subquery = History.objects.filter(
        user=OuterRef('user'), ch_date__lt=OuterRef('ch_date')
    ).order_by('-ch_date').values('ch_date')[:1]

    # Формируем основной запрос, который найдет максимальную последовательность дат для каждого пользователя
    max_sequence_length = History.objects.annotate(
        prev_date=Subquery(subquery)
    ).annotate(
        date_diff=F('ch_date') - F('prev_date')
    ).filter(
        prev_date__isnull=False, date_diff__gt=timedelta(days=1)
    ).values(
        'user'
    ).annotate(
        max_sequence_length=Max('date_diff')
    ).values_list(
        'user', 'max_sequence_length'
    )

    return max_sequence_length
