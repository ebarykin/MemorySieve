from datetime import timedelta
from unittest import TestCase

from django.utils.text import slugify
from datetime import datetime

from vocab.models import History, PubDict, Word
from vocab.services.dict_services import MyDictService

from django.contrib.auth.models import User
from django.utils import timezone


class GetStrikeTest(TestCase):
    """
    Правильный порядок:
    X X _ X _ _ X _ _ _ X _ _ _ _ X _ _ _ _ _ X

    """
    def setUp(self):
        self.user = User.objects.create_user(username='test_user', password='test_password')
        current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.dictionary = PubDict.objects.create(dict_name='test', slug=f'test_{slugify(current_time)}')
        self.word = Word.objects.create(eng_word='red', rus_word='красный')
        self.dictionary.words.add(self.word)
        self.active_dicts = [self.dictionary]


    #
    # def setUp_q_Nok_dif0(self):
    #     today_date = timezone.now().date()
    #     History.objects.create(ch_result=True, user=self.user, ch_date=today_date, word=self.word)
    #
    # def test_q_Nok_dif0(self):
    #     self.setUp_q_Nok_dif0()
    #     result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
    #     self.assertEqual(len(result), 0)
    #
    # # def setUp_q_Ok_dif1(self):
    # #     today_date = timezone.now().date()
    # #     q_ok_dates = [today_date - timedelta(days=x) for x in [1]]
    # #     for date in q_ok_dates:
    # #         # print(f"date: {date}")
    # #         History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)
    #


    def setUp_q_Nok_dif1(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [0]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Ok_dif1(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [1]]
        for date in q_ok_dates:
            # print(f"date: {date}")
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Nok_dif2(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [7, 1]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Ok_dif2(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [7, 2]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Nok_dif3(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [14, 7, 2]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Ok_dif3(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [14, 7, 3]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Nok_dif4(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [10, 9, 7, 3]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Ok_dif4(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [10, 9, 7, 4]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Nok_dif6(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [21, 20, 18, 15, 5]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def setUp_q_Ok_dif6(self):
        today_date = timezone.now().date()
        q_ok_dates = [today_date - timedelta(days=x) for x in [21, 20, 18, 15, 6]]
        for date in q_ok_dates:
            History.objects.create(ch_result=True, user=self.user, ch_date=date, word=self.word)

    def test_q_Nok_dif1(self):
        self.setUp_q_Nok_dif1()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 0)

    def test_q_Ok_dif1(self):
        self.setUp_q_Ok_dif1()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 1)

    def test_q_Nok_dif2(self):
        self.setUp_q_Nok_dif2()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 0)

    def test_q_Ok_dif2(self):
        self.setUp_q_Ok_dif2()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 1)

    def test_q_Nok_dif3(self):
        self.setUp_q_Nok_dif3()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 0)

    def test_q_Ok_dif3(self):
        self.setUp_q_Ok_dif3()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 1)

    def test_q_Nok_dif4(self):
        self.setUp_q_Nok_dif4()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 0)

    def test_q_Ok_dif4(self):
        self.setUp_q_Ok_dif4()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 1)

    def test_q_Nok_dif6(self):
        self.setUp_q_Nok_dif4()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 0)

    def test_q_Ok_dif6(self):
        self.setUp_q_Ok_dif4()
        result = MyDictService.get_user_active_hist_cond_words2(self.user, self.active_dicts)
        self.assertEqual(len(result), 1)

    def tearDown(self):
        self.user.delete()
        self.word.delete()
        History.objects.filter(user=self.user).delete()
        self.dictionary.delete()

        # PubDict.objects.all().delete()
        # Word.objects.all().delete()
        # History.objects.all().delete()
        # User.objects.all().delete()