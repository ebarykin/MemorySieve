from unittest.mock import patch
from unittest import TestCase
from django.contrib.auth.models import User
from vocab.services.dict_services import URLService


class GetOxfDateTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username='test_user', password='test_password')

    @patch('vocab.services.requests.get')
    def test_successful_response(self, mock_requests):
        mock_response = mock_requests.return_value
        mock_response.status_code = 200
        mock_response.content = b'<div class="sound audio_play_button pron-uk icon-audio" data-src-mp3="http://example.com/audio.mp3"></div>'

        word = 'test'
        result = URLService.get_oxf_data(word)
        audio_url = result['audio_url']

        self.assertIsNotNone(audio_url)
        self.assertEqual(audio_url, 'http://example.com/audio.mp3')

    def tearDown(self):
        self.user.delete()