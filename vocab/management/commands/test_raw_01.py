from django.db import connection
from django.core.management.base import BaseCommand


from vocab.models import History
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test raw query'

    def handle(self, *args, **kwargs):
        user_id = 3
        ch_date = '2024-03-10'
        history_records = History.objects.raw(
            # "SELECT * FROM vocab_history WHERE user_id = user_id"


        )

        for record in history_records:
            print(f"User: {record.user_id}, Word: {record.word_id}, Date: {record.ch_date}, Result: {record.ch_result}")