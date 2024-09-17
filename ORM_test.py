import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sieve.settings")
django.setup()

from vocab.services.dict_services import MyDictService
from vocab.models import Profile
from django.contrib.auth import get_user_model
from django.db.models import Count, Case, When

user = get_user_model().objects.get(username='Dasha')
profile = Profile.objects.get(user=user)
print(profile)
# dictionary = PubDict.objects.filter(dict_name='colors')
# dicts = profile.public_dicts.all()
dicts = profile.public_dicts.all()
for dictionary in dicts:
    dictionary.q_ok_set = MyDictService.get_q_ok_set(user, dictionary)
    for word in dictionary.q_ok_set:
        print(f"word:{word}, q_ok: {word.q_ok}")
    counts_by_level = {
        '1': Count(Case(When(q_ok=1, then=1))),
        '2': Count(Case(When(q_ok=2, then=1))),
        '3': Count(Case(When(q_ok=3, then=1))),
        '4': Count(Case(When(q_ok=4, then=1))),
        '5': Count(Case(When(q_ok=5, then=1))),
        '6': Count(Case(When(q_ok=6, then=1))),
        '7': Count(Case(When(q_ok__gte=7, then=1))),
    }

    levels = dictionary.q_ok_set.aggregate(**counts_by_level)
    print(f"levels: {levels}")





# words = dictionary.all()
# words = MyDictService.get_all_user_words(user)

# last_false_set = words.filter(history__ch_result=False)
#
# last_false_set = words.filter(history__ch_result=False).annotate(
#     last_false_date=Max('history__ch_date', filter=Q(history__ch_result=False))
# )
#
#
# print(last_false_set)
#
#
# q_ok_set = words.annotate(
#     q_ok=Case(
#         When(
#             pk__in=Subquery(last_false_set.values('pk')),
#             then=Count(
#                 'history__ch_date',
#                 filter=(
#                         Q(history__ch_result=True) &
#                         Q(history__ch_date__gt=Subquery(
#                             last_false_set.filter(pk=OuterRef('pk')).values('last_false_date')))
#                 )
#             )
#         ),
#         default=Count('history__ch_date', filter=Q(history__ch_result=True)),
#         output_field=IntegerField()
#     )
# )
#
# for word in q_ok_set:
#     print(f"word: {word, word.q_ok}")
#
# counts_by_level = {
#     '1': Count(Case(When(q_ok=1, then=1))),
#     '2': Count(Case(When(q_ok=2, then=1))),
#     '3': Count(Case(When(q_ok=3, then=1))),
#     '4': Count(Case(When(q_ok=4, then=1))),
#     '5': Count(Case(When(q_ok=5, then=1))),
#     '6': Count(Case(When(q_ok=6, then=1))),
#     '7': Count(Case(When(q_ok__gte=7, then=1))),
# }
#
# levels = q_ok_set.aggregate(**counts_by_level)
# print(levels)
#
# for level in levels:
#     print(f'level: {level, levels[level]}')
#
#
#
#


















# last_false_set = dictionary.words.filter(
#     history__ch_result=False
# ).annotate(
#     last_false_date=Max('history__ch_date', filter=Q(history__ch_result=False))
# )

# q_ok_set = dictionary.words.annotate(
#     q_ok=Case(
#         When(
#             pk__in=Subquery(last_false_set.values('pk')),
#             then=Count(
#                 'history__ch_date',
#                 filter=(
#                         Q(history__ch_result=True) &
#                         Q(history__ch_date__gt=Subquery(
#                             last_false_set.filter(pk=OuterRef('pk')).values('last_false_date')))
#                 )
#             )
#         ),
#         default=Count('history__ch_date', filter=Q(history__ch_result=True)),
#         output_field=IntegerField()
#     )
# )
#
#
# for el in q_ok_set:
#     print(f"element : {el.eng_word}, q_ok :{el.q_ok}")
#
# q_ok_set = q_ok_set.annotate(
#     dif=(date.today() - Max('history__ch_date', filter=Q(history__ch_result=True), default=date(2012, 12, 18)))
# ).filter(
#     Q(q_ok=0, dif__gt=timedelta(1) * F('q_ok') * 1) |
#     Q(q_ok=1, dif__gt=timedelta(1) * F('q_ok') * 1) |
#     Q(q_ok=2, dif__gt=timedelta(1) * F('q_ok') - 1) |
#     Q(q_ok=3, dif__gt=timedelta(1) * F('q_ok') - 1) |
#     Q(q_ok=4, dif__gt=timedelta(1) * F('q_ok') - 1) |
#     Q(q_ok__gt=4, dif__gt=timedelta(1) * F('q_ok') + 3)
# )  # Альтернативный вариант с Q
#
#
# print(words_)
# for el_lf in last_false_set:
#     print(f"last_false_set : {el_lf.eng_word} - {el_lf.last_false_date}")
#
# for el in q_ok_set:
#     print(f"element : {el.eng_word}, q_ok :{el.q_ok}, dif:{el.dif}")

