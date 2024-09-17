from django.test import TestCase

# Create your tests here.

from django.test import TestCase


class TestSimpleComponent(TestCase):
    def test_basic_sum(self):
        assert 1 + 1 == 2
