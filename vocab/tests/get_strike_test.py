from datetime import timedelta
from unittest import TestCase, main
from unittest.mock import Mock
from vocab.models import History
from vocab.context_processors import get_strike
from django.contrib.auth.models import User
from django.utils import timezone


class GetStrikeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user', password='test_password')

    def setUp_one_day_NOK(self):
        self.history1 = History.objects.create(ch_result=True, user=self.user, ch_date='2022-01-01', word_id=1)

    def setUp_one_day_OK(self):
        today_date = timezone.now().date()
        self.history1 = History.objects.create(ch_result=True, user=self.user, ch_date=today_date, word_id=1)

    def setUp_two_consecutive_days_NOK(self):
        self.history1 = History.objects.create(ch_result=True, user=self.user, ch_date='2022-01-01', word_id=1)
        self.history2 = History.objects.create(ch_result=True, user=self.user, ch_date='2022-01-02', word_id=1)

    def setUp_two_consecutive_days_OK(self):
        today_date = timezone.now().date()
        yesterday_date = today_date - timedelta(days=1)
        self.history1 = History.objects.create(ch_result=True, user=self.user, ch_date=yesterday_date, word_id=1)
        self.history2 = History.objects.create(ch_result=True, user=self.user, ch_date=today_date, word_id=1)

    def setUp_two_consecutive_days_OK2(self):
        today_date = timezone.now().date()
        yesterday_date = today_date - timedelta(days=1)
        self.history0 = History.objects.create(ch_result=True, user=self.user, ch_date='2022-01-01', word_id=1)
        self.history1 = History.objects.create(ch_result=True, user=self.user, ch_date=yesterday_date, word_id=1)
        self.history2 = History.objects.create(ch_result=True, user=self.user, ch_date=today_date, word_id=1)

    def setUp_two_consecutive_days_OK3(self):
        today_date = timezone.now().date()
        yesterday_date = today_date - timedelta(days=1)
        self.history0 = History.objects.create(ch_result=True, user=self.user, ch_date='2022-01-01', word_id=1)
        self.history1 = History.objects.create(ch_result=False, user=self.user, ch_date=yesterday_date, word_id=1)
        self.history2 = History.objects.create(ch_result=True, user=self.user, ch_date=today_date, word_id=1)

    def test_strike_calculation_one_day_NOK(self):
        self.setUp_one_day_NOK()
        request = Mock(user=self.user, session={})
        result = get_strike(request)
        self.assertEqual(result['strike'], [0, False])

    def test_strike_calculation_one_day_OK(self):
        self.setUp_one_day_OK()
        request = Mock(user=self.user, session={})
        result = get_strike(request)
        self.assertEqual(result['strike'], [1, True])

    def test_strike_no_history(self):
        request = Mock(user=self.user, session={})
        result = get_strike(request)
        self.assertEqual(result['strike'], [0, False])

    def test_strike_calculation_two_consecutive_days_NOK(self):
        self.setUp_two_consecutive_days_NOK()
        request = Mock(user=self.user, session={})
        result = get_strike(request)
        self.assertEqual(result['strike'], [0, False])

    def test_strike_calculation_two_consecutive_days_OK(self):
        self.setUp_two_consecutive_days_OK()
        request = Mock(user=self.user, session={})
        result = get_strike(request)
        self.assertEqual(result['strike'], [2, True])

    def test_strike_calculation_two_consecutive_days_OK2(self):
        self.setUp_two_consecutive_days_OK2()
        request = Mock(user=self.user, session={})
        result = get_strike(request)
        self.assertEqual(result['strike'], [2, True])

    def test_strike_calculation_two_consecutive_days_OK3(self):
        self.setUp_two_consecutive_days_OK3()
        request = Mock(user=self.user, session={})
        result = get_strike(request)
        self.assertEqual(result['strike'], [1, True])

    def tearDown(self):
        self.user.delete()

#
# if __name__ == '__main__':
#     main()
