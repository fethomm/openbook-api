import json

from django.urls import reverse
from faker import Faker
from rest_framework import status
from rest_framework.test import APITestCase

from openbook_common.tests.helpers import make_user, make_authentication_headers_for_user, make_device
from openbook_devices.models import Device

fake = Faker()


class DevicesAPITests(APITestCase):
    """
    DevicesAPI
    """

    def test_can_create_device_without_optional_arguments(self):
        """
        should be able to create a new device and return 200
        """

        user = make_user()
        device_uuid = fake.uuid4()

        request_body = {
            'uuid': device_uuid,
        }

        url = self._get_url()
        headers = make_authentication_headers_for_user(user)
        response = self.client.put(url, request_body, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Device.objects.filter(uuid=device_uuid, owner=user).exists())

    def test_can_create_device_with_all_arguments(self):
        """
        should be able to create a new device and return 200
        """

        user = make_user()
        device_uuid = fake.uuid4()
        device_name = fake.user_name()
        one_signal_player_id = fake.uuid4()
        notifications_enabled = fake.boolean()

        request_body = {
            'uuid': device_uuid,
            'name': device_name,
            'one_signal_player_id': one_signal_player_id,
            'notifications_enabled': notifications_enabled,
        }

        url = self._get_url()
        headers = make_authentication_headers_for_user(user)
        response = self.client.put(url, request_body, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Device.objects.filter(uuid=device_uuid, owner=user, one_signal_player_id=one_signal_player_id,
                                              notifications_enabled=notifications_enabled).exists())

    def test_can_retrieve_devices(self):
        """
        should be able to retrieve all devices and return 200
        """
        user = make_user()

        amount_of_devices = 5
        devices_ids = []

        for i in range(0, amount_of_devices):
            device = make_device(owner=user)
            devices_ids.append(device.pk)

        url = self._get_url()
        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_devices = json.loads(response.content)

        self.assertEqual(len(response_devices), len(devices_ids))

        for response_device in response_devices:
            response_device_id = response_device.get('id')
            self.assertIn(response_device_id, devices_ids)

    def test_can_delete_devices(self):
        """
        should be able to delete all devices and return 200
        """
        user = make_user()

        amount_of_devices = 5
        devices_ids = []

        for i in range(0, amount_of_devices):
            device = make_device(owner=user)
            devices_ids.append(device.pk)

        url = self._get_url()
        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(Device.objects.filter(owner=user).exists())

    def _get_url(self):
        return reverse('devices')


class DeviceItemAPITests(APITestCase):
    """
    DeviceItemAPI
    """

    def test_can_retrieve_own_device(self):
        """
        should be able to retrieve an own device
        """
        user = make_user()

        headers = make_authentication_headers_for_user(user)

        device = make_device(owner=user)
        device_id = device.pk

        url = self._get_url(device_id)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_device = json.loads(response.content)

        self.assertEqual(response_device['id'], device.pk)

    def test_cant_retrieve_foreign_device(self):
        """
        should not be able to retrieve a foreign device
        """
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)

        device = make_device(owner=foreign_user)
        device_id = device.pk

        url = self._get_url(device_id)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_delete_own_device(self):
        """
        should be able to delete an own device and return 200
        """
        user = make_user()

        headers = make_authentication_headers_for_user(user)

        device = make_device(owner=user)
        device_id = device.pk

        url = self._get_url(device_id)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(Device.objects.filter(id=device_id).exists())

    def test_cannot_delete_foreign_device(self):
        """
        should not be able to delete a foreign device and return 200
        """
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)

        device = make_device(owner=foreign_user)
        device_id = device.pk

        url = self._get_url(device_id)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(Device.objects.filter(id=device_id).exists())

    def test_can_update_a_device_name(self):
        """
        should be able to update a device name and return 200
        """

        user = make_user()
        device = make_device(owner=user)

        new_device_name = fake.user_name()

        request_body = {
            'name': new_device_name
        }

        url = self._get_url(device_id=device.pk)
        headers = make_authentication_headers_for_user(user)
        response = self.client.patch(url, request_body, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(Device.objects.filter(pk=device.pk, name=new_device_name).exists())

    def test_can_update_a_device_notifications_enabled(self):
        """
        should be able to update a device notifications enabled and return 200
        """

        user = make_user()
        device = make_device(owner=user)

        new_device_notifications_enabled = fake.boolean()

        request_body = {
            'notifications_enabled': new_device_notifications_enabled
        }

        url = self._get_url(device_id=device.pk)
        headers = make_authentication_headers_for_user(user)
        response = self.client.patch(url, request_body, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            Device.objects.filter(pk=device.pk, notifications_enabled=new_device_notifications_enabled).exists())

    def test_can_update_a_device_one_signal_player_id(self):
        """
        should be able to update a device one_signal_player_id and return 200
        """

        user = make_user()
        device = make_device(owner=user)

        new_device_one_signal_player_id = fake.uuid4()

        request_body = {
            'one_signal_player_id': new_device_one_signal_player_id
        }

        url = self._get_url(device_id=device.pk)
        headers = make_authentication_headers_for_user(user)
        response = self.client.patch(url, request_body, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            Device.objects.filter(pk=device.pk, one_signal_player_id=new_device_one_signal_player_id).exists())

    def test_can_update_a_device_updatable_arguments_at_once(self):
        """
        should be able to update a device updatable_arguments at once and return 200
        """

        user = make_user()
        device = make_device(owner=user)

        new_device_one_signal_player_id = fake.uuid4()
        new_notifications_enabled = fake.boolean()
        new_name = fake.user_name()

        request_body = {
            'name': new_name,
            'one_signal_player_id': new_device_one_signal_player_id,
            'notifications_enabled': new_notifications_enabled
        }

        url = self._get_url(device_id=device.pk)
        headers = make_authentication_headers_for_user(user)
        response = self.client.patch(url, request_body, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(
            Device.objects.filter(pk=device.pk, one_signal_player_id=new_device_one_signal_player_id, name=new_name,
                                  notifications_enabled=new_notifications_enabled).exists())

    def test_cant_update_a_foreign_device(self):
        """
        should not be able to update a foreign device and return 403
        """

        user = make_user()
        foreign_user = make_user()
        device = make_device(owner=foreign_user)

        new_device_one_signal_player_id = fake.uuid4()
        new_notifications_enabled = fake.boolean()
        new_name = fake.user_name()

        request_body = {
            'name': new_name,
            'one_signal_player_id': new_device_one_signal_player_id,
            'notifications_enabled': new_notifications_enabled
        }

        url = self._get_url(device_id=device.pk)
        headers = make_authentication_headers_for_user(user)
        response = self.client.patch(url, request_body, **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertFalse(
            Device.objects.filter(pk=device.pk, one_signal_player_id=new_device_one_signal_player_id, name=new_name,
                                  notifications_enabled=new_notifications_enabled).exists())

    def _get_url(self, device_id):
        return reverse('device', kwargs={
            'device_id': device_id
        })
