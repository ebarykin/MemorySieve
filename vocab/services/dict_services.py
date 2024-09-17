from datetime import date, timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, ExpressionWrapper, Count, Subquery, OuterRef, F, Case, When, Max, \
    IntegerField, DateField, DurationField, QuerySet
from django.contrib.auth.models import User
from vocab.models import PersDict, Word, PubDict
from typing import Union, Optional


def get_dict_instance(dict_name: str, user=None) -> Union[PubDict, PersDict]:
    if dict_name == 'personal':  # PERSONAL DICTIONARY
        dict_ = get_object_or_404(PersDict, user=user)
        dict_.dict_name = 'personal'
        dict_.slug = 'personal'
    else:                       # PUBLIC DICTIONARY
        dict_ = get_object_or_404(PubDict, slug=dict_name)

    return dict_


class MyDictService:
    @staticmethod
    def get_last_false_set(user: User, dictionary: Union[PubDict, PersDict]) -> Optional[QuerySet]:
        """

        :param user:
        :param dictionary:
        :return: Queryset слов в который есть Nok в истории проверки
        """
        last_false_set = dictionary.words.filter(
            history__ch_result=False,
            history__user=user,
        ).annotate(
            last_false_date=Max('history__ch_date', filter=Q(history__ch_result=False))
        )
        return last_false_set

    @staticmethod
    def get_q_ok_set(user: User, dictionary: Union[PubDict, PersDict]) -> Optional[QuerySet]:
        """

        :param user:
        :param dictionary:
        :return: Queryset в котором аннотировано поля:
            "q_ok" - кол-во крайних успешных повторений.
            "last_date" - дата последнего повторения (если повторения не было, то 01.01.2024)
            "dif" - разница в днях между текущей датой и last_date
        """
        words = dictionary.words.all()

        last_false_set = MyDictService.get_last_false_set(user, dictionary)
        today = timezone.now().date()
        q_ok_set = words.annotate(
            q_ok=Case(
                When(
                    pk__in=Subquery(last_false_set.values('pk')),
                    then=Count(
                        'history__ch_date',
                        filter=(
                                Q(history__user=user) &
                                Q(history__ch_result=True) &
                                Q(history__ch_date__gt=Subquery(
                                    last_false_set.filter(pk=OuterRef('pk')).values('last_false_date')))
                        )
                    )
                ),
                default=Count('history__ch_date', filter=(
                        Q(history__user=user) &
                        Q(history__ch_result=True)
                )
                              ),
                output_field=IntegerField()
            ),
            last_date=Max(Case(
                When(
                    history__user=user,
                    then='history__ch_date'
                ),
                default=date(2024, 1, 1),
                output_field=DateField()
            )),
            dif=ExpressionWrapper(today - F('last_date'), output_field=DurationField())
        )
        return q_ok_set

    @staticmethod
    def get_user_active_hist_cond_words2(user, active_dicts):
        """

        :param user:
        :param active_dicts:
        :return: list Words
        """
        if active_dicts is None:
            return Word.objects.none()
        words = []

        for dictionary in active_dicts:
            q_ok_set = MyDictService.get_q_ok_set(user, dictionary)
            selected_words = q_ok_set.filter(
                Q(q_ok=0, dif__gte=0 * timedelta(days=1)) |
                Q(q_ok=1, dif__gte=F('q_ok') * timedelta(days=1)) |
                Q(q_ok=2, dif__gt=F('q_ok') * timedelta(days=1) - 1) |
                Q(q_ok=3, dif__gt=F('q_ok') * timedelta(days=1) - 1) |
                Q(q_ok=4, dif__gt=F('q_ok') * timedelta(days=1) - 1) |
                Q(q_ok=5, dif__gt=F('q_ok') * timedelta(days=1) - 1) |
                Q(q_ok=6, dif__gt=F('q_ok') * timedelta(days=1) - 1) |
                Q(q_ok__gte=7, dif__gt=timedelta(days=1) * 21)
            )

            words.extend(selected_words)
        return words
