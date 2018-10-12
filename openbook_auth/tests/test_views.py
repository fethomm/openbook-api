# Create your tests here.
import tempfile

from PIL import Image
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from openbook_auth.models import User, UserProfile

import logging
import json

logger = logging.getLogger(__name__)


class RegistrationAPITests(APITestCase):
    """
    RegistrationAPI
    """

    def test_invalid_username(self):
        """
        should return 400 if the username is not valid
        """
        url = self._get_url()
        invalid_usernames = ('lifenautjoe!', 'lifenautjo@', 'lifenautpoe🔒', 'lifenaut-joe', '字kasmndikasm')
        for username in invalid_usernames:
            data = {
                'username': username,
                'name': 'Miguel',
                'email': 'user@mail.com',
                'password': 'secretPassword123',
                'birth_date': '27-1-1996'
            }
            response = self.client.post(url, data, format='multipart')
            parsed_response = json.loads(response.content)
            self.assertIn('username', parsed_response)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_name(self):
        """
        should return 400 if the name is not valid
        """
        url = self._get_url()
        invalid_names = ('Joel!', 'Joel_', 'Joel@', 'Joel ✨', 'Joel 字', 'Joel -!')
        for name in invalid_names:
            data = {
                'username': 'lifenautjoe',
                'name': name,
                'email': 'user@mail.com',
                'password': 'secretPassword123',
                'birth_date': '27-1-1996'
            }
            response = self.client.post(url, data, format='multipart')
            parsed_response = json.loads(response.content)
            self.assertIn('name', parsed_response)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_username_required(self):
        """
        should return 400 if the username is not present
        """
        url = self._get_url()
        data = {'name': 'Joel', 'email': 'user@mail.com', 'password': 'secretPassword123', 'birth_date': '27-1-1996'}
        response = self.client.post(url, data, format='multipart')
        parsed_response = json.loads(response.content)
        self.assertIn('username', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_name_required(self):
        """
        should return 400 if the name is not present
        """
        url = self._get_url()
        data = {'username': 'lifenautjoe', 'email': 'user@mail.com', 'password': 'secretPassword123',
                'birth_date': '27-1-1996'}
        response = self.client.post(url, data, format='multipart')
        parsed_response = json.loads(response.content)
        self.assertIn('name', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_required(self):
        """
        should return 400 if the email is not present
        """
        url = self._get_url()
        data = {'username': 'lifenautjoe', 'name': 'Joel Hernandez', 'password': 'secretPassword123',
                'birth_date': '27-1-1996'}
        response = self.client.post(url, data, format='multipart')
        parsed_response = json.loads(response.content)
        self.assertIn('email', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_birth_date_required(self):
        """
        should return 400 if the birth_date is not present
        """
        url = self._get_url()
        data = {'username': 'lifenautjoe', 'name': 'Joel Hernandez', 'email': 'user@mail.com',
                'password': 'secretPassword123'}
        response = self.client.post(url, data, format='multipart')
        parsed_response = json.loads(response.content)
        self.assertIn('birth_date', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_username_taken(self):
        """
        should return 400 if username is taken.
        """
        url = self._get_url()
        username = 'lifenautjoe'
        first_request_data = {'username': username, 'name': 'Joel Hernandez', 'email': 'user@mail.com',
                              'password': 'secretPassword123', 'birth_date': '27-1-1996'}
        self.client.post(url, first_request_data, format='multipart')
        second_request_data = {'username': username, 'name': 'Juan Taramera', 'email': 'juan@mail.com',
                               'password': 'woahpassword123', 'birth_date': '27-1-1996'}
        response = self.client.post(url, second_request_data, format='multipart')

        parsed_response = json.loads(response.content)

        self.assertIn('username', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_taken(self):
        """
        should return 400 if email is taken.
        """
        url = self._get_url()
        email = 'joel@open-book.org'
        first_request_data = {'username': 'lifenautjoe1', 'name': 'Joel Hernandez', 'email': email,
                              'password': 'secretPassword123', 'birth_date': '27-1-1996'}
        self.client.post(url, first_request_data, format='multipart')
        second_request_data = {'username': 'lifenautjoe2', 'name': 'Juan Taramera', 'email': email,
                               'password': 'woahpassword123', 'birth_date': '27-1-1996'}
        response = self.client.post(url, second_request_data, format='multipart')
        parsed_response = json.loads(response.content)

        self.assertIn('email', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_created(self):
        """
        should create a User model instance
        """
        url = self._get_url()
        username = 'potato123'
        first_request_data = {'username': username, 'name': 'Joel Hernandez', 'email': 'test@email.com',
                              'password': 'secretPassword123', 'birth_date': '27-1-1996'}
        response = self.client.post(url, first_request_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.filter(username=username).exists(), True)

    def test_user_profile_is_created(self):
        """
        should create a UserProfile instance and associate it to the User instance
        """
        url = self._get_url()
        username = 'vegueta968'
        request_data = {'username': username, 'name': 'Joel Hernandez', 'email': 'test@email.com',
                        'password': 'secretPassword123', 'birth_date': '27-1-1996'}
        response = self.client.post(url, request_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserProfile.objects.count(), 1)
        user = User.objects.get(username=username)
        self.assertTrue(hasattr(user, 'profile'))

    def test_user_avatar(self):
        """
        Should accept an avatar file and store it on the UserProfile
        """
        image = Image.new('RGB', (100, 100))
        tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg')
        image.save(tmp_file)
        username = 'testusername'
        request_data = {'username': username, 'name': 'Joel Hernandez', 'email': 'test@email.com',
                        'password': 'secretPassword123', 'birth_date': '27-1-1996', 'avatar': tmp_file}
        url = self._get_url()
        self.client.post(url, request_data, format='multipart')
        user = User.objects.get(username=username)
        self.assertTrue(hasattr(user.profile, 'avatar'))

    def test_user_status(self):
        """
        Should return 201 when the user was created successfully
        """
        users_data = (
            {
                'username': 'a_valid_username', 'name': 'Joel Hernandez', 'email': 'hi@ohmy.com',
                'password': 'askdnaoisd!', 'birth_date': '27-1-1991'
            },
            {
                'username': 'terry_crews', 'name': 'Terry Crews', 'email': 'terry@oldsp.ie',
                'password': 'secretPassword123', 'birth_date': '27-1-1996'
            },
            {
                'username': 'mike_chowder___', 'name': 'Mike Johnson', 'email': 'mike@chowchow.com',
                'password': 'OhGoDwEnEEdFixTurES!', 'birth_date': '27-01-1991'
            }
        )
        url = self._get_url()
        for user_data_item in users_data:
            response = self.client.post(url, user_data_item, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def _get_url(self):
        return reverse('register-user')


class UsernameCheckAPITests(APITestCase):
    """
    UsernameCheckAPI
    """

    def test_username_not_taken(self):
        """
        should return status 202 if username is not taken.
        """
        username = 'lifenautjoe'
        request_data = {'username': username}
        url = self._get_url()
        response = self.client.post(url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_username_taken(self):
        """
        should return status 400 if the username is taken
        """
        username = 'lifenautjoe'
        User.objects.create_user(username=username, password='SuChSeCuRiTyWow!', email='lifenautjoe@mail.com')
        request_data = {'username': username}
        url = self._get_url()
        response = self.client.post(url, request_data, format='json')

        parsed_response = json.loads(response.content)

        self.assertIn('username', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_username(self):
        """
        should return 400 if the username is not a valid one
        """
        url = self._get_url()
        usernames = ('lifenau!', 'p-o-t-a-t-o', '.a!', 'dexter@', '🤷‍♂️')
        for username in usernames:
            data = {
                'username': username
            }
            response = self.client.post(url, data, format='json')
            parsed_response = json.loads(response.content)
            self.assertIn('username', parsed_response)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_username(self):
        """
        should return 202 if the username is a valid username
        """
        url = self._get_url()
        usernames = ('lifenautjoe', 'shantanu_123', 'm4k3l0v3n0tw4r', 'o_0')
        for username in usernames:
            data = {
                'username': username
            }
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def _get_url(self):
        return reverse('username-check')


class EmailCheckAPITests(APITestCase):
    """
    EmailCheckAPI
    """

    def test_email_not_taken(self):
        """
        should return status 202 if email is not taken.
        """
        email = 'joel@open-book.org'
        request_data = {'email': email}
        url = self._get_url()
        response = self.client.post(url, request_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_email_taken(self):
        """
        should return status 400 if the email is taken
        """
        email = 'joel@open-book.org'
        User.objects.create_user(email=email, password='SuChSeCuRiTyWow!', username='lifenautjoe')
        request_data = {'email': email}
        url = self._get_url()
        response = self.client.post(url, request_data, format='json')

        parsed_response = json.loads(response.content)

        self.assertIn('email', parsed_response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email(self):
        """
        should return 400 if the email is not a valid one
        """
        url = self._get_url()
        emails = ('not-a-valid-email.com', 'fake-email.com', 'joel hernandez', 'omelette@dufromage', 'test_data!asd')
        for email in emails:
            data = {
                'email': email
            }
            response = self.client.post(url, data, format='json')
            parsed_response = json.loads(response.content)
            self.assertIn('email', parsed_response)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_email(self):
        """
        should return 202 if the email is a valid email
        """
        url = self._get_url()
        emails = ('joel@open-book.org', 'gerald@rivia.com', 'obi@wan.com', 'c3po@robot.me')
        for email in emails:
            data = {
                'email': email
            }
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def _get_url(self):
        return reverse('email-check')
