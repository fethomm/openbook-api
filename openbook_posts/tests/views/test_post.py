# Create your tests here.
import json
import tempfile
from os import access, F_OK

from PIL import Image
from django.urls import reverse
from faker import Faker
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.images import ImageFile
from django.core.files import File

import logging
import random

from openbook_common.tests.helpers import make_authentication_headers_for_user, make_fake_post_text, \
    make_fake_post_comment_text, make_user, make_circle, make_emoji, make_emoji_group, make_reactions_emoji_group, \
    make_community, make_private_community
from openbook_communities.models import Community
from openbook_notifications.models import PostCommentNotification, PostReactionNotification, Notification
from openbook_posts.models import Post, PostComment, PostReaction

logger = logging.getLogger(__name__)
fake = Faker()


class PostItemAPITests(APITestCase):
    """
    PostItemAPI
    """

    fixtures = [
        'openbook_circles/fixtures/circles.json'
    ]

    def test_can_retrieve_own_post(self):
        """
        should be able to retrieve own post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_post = json.loads(response.content)

        self.assertEqual(response_post['id'], post.pk)

    def test_can_retrieve_foreign_user_public_post(self):
        """
        should be able to retrieve a foreign user public post and return 200
        """
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)
        post = foreign_user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_post = json.loads(response.content)

        self.assertEqual(response_post['id'], post.pk)

    def test_can_retrieve_connected_user_encircled_post(self):
        """
        should be able to retrieve a connected user encircled post and return 200
        """
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)

        circle = make_circle(creator=foreign_user)
        post = foreign_user.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        user.connect_with_user_with_id(foreign_user.pk)
        foreign_user.confirm_connection_with_user_with_id(user.pk, circles_ids=[circle.pk])

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_post = json.loads(response.content)

        self.assertEqual(response_post['id'], post.pk)

    def test_can_retrieve_public_community_not_member_of_post(self):
        """
        should be able to retrieve a public community not member of post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        post = community_owner.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        response_post = json.loads(response.content)

        self.assertEqual(response_post['id'], post.pk)

    def test_can_retrieve_public_community_member_of_post(self):
        """
        should be able to retrieve a public community member of post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        post = community_owner.create_community_post(text=make_fake_post_text(), community_name=community.name)

        user.join_community_with_name(community_name=community.name)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_post = json.loads(response.content)

        self.assertEqual(response_post['id'], post.pk)

    def test_cant_retrieve_community_banned_from_post(self):
        """
        should not be able to retrieve a community banned from post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        post = community_owner.create_community_post(text=make_fake_post_text(), community_name=community.name)

        user.join_community_with_name(community_name=community.name)
        user.comment_post(post, text=make_fake_post_comment_text())

        community_owner.ban_user_with_username_from_community_with_name(username=user.username,
                                                                        community_name=community.name)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cant_retrieve_private_community_not_member_of_post(self):
        """
        should not be able to retrieve a private community not member of post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner, type=Community.COMMUNITY_TYPE_PRIVATE)

        post = community_owner.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_retrieve_private_community_member_of_post(self):
        """
        should be able to retrieve a private community member of post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner, type=Community.COMMUNITY_TYPE_PRIVATE)

        post = community_owner.create_community_post(text=make_fake_post_text(), community_name=community.name)

        community_owner.invite_user_with_username_to_community_with_name(username=user.username,
                                                                         community_name=community.name)
        user.join_community_with_name(community_name=community.name)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_post = json.loads(response.content)

        self.assertEqual(response_post['id'], post.pk)

    def test_cant_retrieve_user_encircled_post(self):
        """
        should not be able to retrieve a user encircled post and return 400
        """
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)

        circle = make_circle(creator=foreign_user)
        post = foreign_user.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cant_retrieve_blocked_user_post(self):
        """
        should not be able to retrieve a post from a blocked user and return 400
        """
        user = make_user()
        user_to_block = make_user()

        headers = make_authentication_headers_for_user(user)

        post = user_to_block.create_public_post(text=make_fake_post_text())

        user.block_user_with_id(user_id=user_to_block.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_cant_retrieve_blocking_user_post(self):
        """
        should not be able to retrieve a post from a blocking user and return 400
        """
        user = make_user()
        user_to_block = make_user()

        headers = make_authentication_headers_for_user(user)

        post = user_to_block.create_public_post(text=make_fake_post_text())

        user_to_block.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_cant_retrieve_blocked_user_community_post(self):
        """
        should not be able to retrieve a community post from a blocked user and return 400
        """
        user = make_user()

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user_to_block = make_user()

        headers = make_authentication_headers_for_user(user)

        user_to_block.join_community_with_name(community_name=community.name)

        post = user_to_block.create_community_post(text=make_fake_post_text(), community_name=community.name)

        user.block_user_with_id(user_id=user_to_block.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_cant_retrieve_blocking_user_community_post(self):
        """
        should not be able to retrieve a community post from a blocking user and return 400
        """
        user = make_user()

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user_to_block = make_user()

        headers = make_authentication_headers_for_user(user)

        user_to_block.join_community_with_name(community_name=community.name)

        post = user_to_block.create_community_post(text=make_fake_post_text(), community_name=community.name)

        user_to_block.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_can_retrieve_blocked_community_staff_post(self):
        """
        should be able to retrieve a the post of a blocked community staff member and return 200
        """
        user = make_user()
        community_owner = make_user()
        community = make_community(creator=community_owner)

        headers = make_authentication_headers_for_user(user)

        post = community_owner.create_community_post(text=make_fake_post_text(), community_name=community.name)

        user.block_user_with_id(user_id=community_owner.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        response_post = json.loads(response.content)
        self.assertEqual(response_post['id'], post.pk)

    def test_can_retrieve_blocking_community_staff_post(self):
        """
        should be able to retrieve a the post of a blocking community staff member and return 200
        """
        user = make_user()
        community_owner = make_user()
        community = make_community(creator=community_owner)

        headers = make_authentication_headers_for_user(user)

        post = community_owner.create_community_post(text=make_fake_post_text(), community_name=community.name)

        community_owner.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        response_post = json.loads(response.content)
        self.assertEqual(response_post['id'], post.pk)

    def test_can_delete_own_post(self):
        """
        should be able to delete own post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Post.objects.filter(pk=post.pk).count() == 0)

    def test_delete_image_post(self):
        """
        should be able to delete image post and file return True
        """
        user = make_user()

        image = Image.new('RGB', (100, 100))
        tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg')
        image.save(tmp_file)
        tmp_file.seek(0)
        image = ImageFile(tmp_file)

        post = user.create_public_post(text=make_fake_post_text(), image=image)
        file = post.image.image.file

        user.delete_post_with_id(post.id)

        self.assertFalse(access(file.name, F_OK))

    def test_delete_video_post(self):
        """
        should be able to delete video post and file return True
        """
        user = make_user()

        video = b"video_file_content"
        tmp_file = tempfile.NamedTemporaryFile(suffix='.mp4')
        tmp_file.write(video)
        tmp_file.seek(0)
        video = File(tmp_file)

        post = user.create_public_post(text=make_fake_post_text(), video=video)
        file = post.video.video.file

        user.delete_post_with_id(post.id)

        self.assertFalse(access(file.name, F_OK))

    def test_can_delete_post_of_community_if_mod(self):
        """
        should be able to delete a community post if moderator and return 200
        """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_moderator_with_username_to_community_with_name(username=user.username,
                                                                             community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Post.objects.filter(pk=post.pk).count() == 0)

    def test_can_delete_post_of_community_if_admin(self):
        """
        should be able to delete a community post if administrator and return 200
        """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_administrator_with_username_to_community_with_name(username=user.username,
                                                                                 community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Post.objects.filter(pk=post.pk).count() == 0)

    def test_logs_community_post_deleted_by_non_creator(self):
        """
        should create a log when a community post was deleted by an admin/moderator
        """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_administrator_with_username_to_community_with_name(username=user.username,
                                                                                 community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        self.client.delete(url, **headers)

        self.assertTrue(community.logs.filter(action_type='RP',
                                              source_user=user,
                                              target_user=community_post_creator).exists())

    def test_cannot_delete_foreign_post(self):
        """
        should not be able to delete a foreign post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        foreign_user = make_user()
        post = foreign_user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Post.objects.filter(pk=post.pk).count() == 1)

    def test_can_edit_own_post(self):
        """
        should be able to edit own  post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)
        edited_text = make_fake_post_text()
        data = {
            'text': edited_text
        }

        response = self.client.patch(url, data, **headers)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.text, edited_text)
        self.assertTrue(post.is_edited)

    def test_canot_edit_to_remove_text_from_own_text_only_post(self):
        """
        should not be able to edit to remove the text of an own post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        initial_text = make_fake_post_text()
        post = user.create_public_post(text=initial_text)

        url = self._get_url(post)
        data = {
            'text': ''
        }

        response = self.client.patch(url, data, **headers)

        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertEqual(post.text, initial_text)
        self.assertFalse(post.is_edited)

    def test_can_edit_own_community_post(self):
        """
        should be able to edit own community post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(community_post)
        edited_text = make_fake_post_text()
        data = {
            'text': edited_text
        }

        response = self.client.patch(url, data, **headers)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        community_post.refresh_from_db()
        self.assertEqual(community_post.text, edited_text)
        self.assertTrue(community_post.is_edited)

    def test_can_edit_own_community_post_which_is_closed(self):
        """
        should be able to edit own closed community post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        community_post.is_closed = True
        community_post.save()

        url = self._get_url(community_post)
        edited_text = make_fake_post_text()
        data = {
            'text': edited_text
        }

        response = self.client.patch(url, data, **headers)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        community_post.refresh_from_db()
        self.assertEqual(community_post.text, edited_text)
        self.assertTrue(community_post.is_edited)

    def test_cannot_edit_foreign_post(self):
        """
        should not be able to edit foreign post
        """
        user = make_user()
        foreign_user = make_user()
        headers = make_authentication_headers_for_user(user)
        original_text = make_fake_post_text()
        post = foreign_user.create_public_post(text=original_text)

        url = self._get_url(post)
        edited_text = make_fake_post_text()
        data = {
            'text': edited_text
        }

        response = self.client.patch(url, data, **headers)

        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertEqual(post.text, original_text)
        self.assertFalse(post.is_edited)

    def _get_url(self, post):
        return reverse('post', kwargs={
            'post_uuid': post.uuid
        })


class MutePostAPITests(APITestCase):
    """
    MutePostAPI
    """

    fixtures = [
        'openbook_circles/fixtures/circles.json'
    ]

    def test_can_mute_own_post(self):
        """
        should be able to mute own post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def test_cant_mute_own_post_if_already_muted(self):
        """
        should not be able to mute own post if already muted and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        user.mute_post_with_id(post.pk)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def test_can_mute_foreign_post_if_public_post(self):
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)
        post = foreign_user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def test_cannot_mute_foreign_post_if_encircled_post(self):
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)

        circle = make_circle(creator=foreign_user)

        post = foreign_user.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(user.has_muted_post_with_id(post.pk))

    def test_can_mute_foreign_post_if_part_of_encircled_post(self):
        user = make_user()
        foreign_user = make_user()

        headers = make_authentication_headers_for_user(user)

        circle = make_circle(creator=foreign_user)

        post = foreign_user.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        foreign_user.connect_with_user_with_id(user_id=user.pk, circles_ids=[circle.pk])
        user.confirm_connection_with_user_with_id(user_id=foreign_user.pk)

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def test_can_mute_community_post_if_public(self):
        user = make_user()

        foreign_user = make_user()
        community = make_community(creator=foreign_user)

        headers = make_authentication_headers_for_user(user)
        post = foreign_user.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def test_cannot_mute_closed_community_post(self):
        """
        should not be able to mute closed post if not admin/mod or post creator in community
        """
        user = make_user()

        foreign_user = make_user()
        community = make_community(creator=foreign_user)
        user.join_community_with_name(community_name=community.name)

        headers = make_authentication_headers_for_user(user)
        post = foreign_user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(user.has_muted_post_with_id(post.pk))

    def test_can_mute_closed_community_post_if_creator(self):
        """
        should be able to mute closed post if post creator in community
        """
        user = make_user()

        foreign_user = make_user()
        community = make_community(creator=foreign_user)
        user.join_community_with_name(community_name=community.name)

        headers = make_authentication_headers_for_user(user)
        post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def test_can_mute_closed_community_post_administrator(self):
        """
        should be able to mute closed post if administrator in community
        """
        user = make_user()

        admin = make_user()
        community = make_community(creator=admin)
        user.join_community_with_name(community_name=community.name)

        headers = make_authentication_headers_for_user(admin)
        post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(admin.has_muted_post_with_id(post.pk))

    def test_can_mute_closed_community_post_if_moderator(self):
        """
        should be able to mute closed post if moderator in community
        """
        user = make_user()

        admin = make_user()
        moderator = make_user()
        community = make_community(creator=admin)
        user.join_community_with_name(community_name=community.name)
        moderator.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=moderator.username, community_name=community.name)

        headers = make_authentication_headers_for_user(moderator)
        post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(moderator.has_muted_post_with_id(post.pk))

    def test_cant_mute_community_post_if_private_and_not_member(self):
        user = make_user()

        foreign_user = make_user()
        community = make_community(creator=foreign_user, type='T')

        headers = make_authentication_headers_for_user(user)
        post = foreign_user.create_community_post(text=make_fake_post_text(), community_name=community.name)

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(user.has_muted_post_with_id(post.pk))

    def test_can_mute_community_post_if_private_and_member(self):
        user = make_user()

        foreign_user = make_user()
        community = make_community(creator=foreign_user, type='T')

        headers = make_authentication_headers_for_user(user)
        post = foreign_user.create_community_post(text=make_fake_post_text(), community_name=community.name)

        foreign_user.invite_user_with_username_to_community_with_name(username=user.username,
                                                                      community_name=community.name)

        user.join_community_with_name(community_name=community.name)

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def _get_url(self, post):
        return reverse('mute-post', kwargs={
            'post_uuid': post.uuid
        })


class UnmutePostAPITests(APITestCase):
    """
    UnmutePostAPI
    """

    fixtures = [
        'openbook_circles/fixtures/circles.json'
    ]

    def test_can_unmute_own_post(self):
        """
        should be able to unmute own post and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        user.mute_post_with_id(post.pk)

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(user.has_muted_post_with_id(post.pk))

    def test_cant_unmute_own_post_if_already_unmuted(self):
        """
        should not be able to unmute own post if already unmuted and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(user.has_muted_post_with_id(post.pk))

    def test_cannot_unmute_closed_community_post(self):
        """
        should not be able to unmute closed post if not admin/mod or post creator in community
        """
        user = make_user()

        foreign_user = make_user()
        community = make_community(creator=foreign_user)
        user.join_community_with_name(community_name=community.name)

        headers = make_authentication_headers_for_user(user)
        post = foreign_user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        user.mute_post_with_id(post.pk)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(user.has_muted_post_with_id(post.pk))

    def test_can_unmute_closed_community_post_if_creator(self):
        """
        should be able to unmute closed post if post creator in community
        """
        user = make_user()

        foreign_user = make_user()
        community = make_community(creator=foreign_user)
        user.join_community_with_name(community_name=community.name)

        headers = make_authentication_headers_for_user(user)
        post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        user.mute_post_with_id(post.pk)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(user.has_muted_post_with_id(post.pk))

    def test_can_unmute_closed_community_post_administrator(self):
        """
        should be able to unmute closed post if administrator in community
        """
        user = make_user()

        admin = make_user()
        community = make_community(creator=admin)
        user.join_community_with_name(community_name=community.name)

        headers = make_authentication_headers_for_user(admin)
        post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        admin.mute_post_with_id(post.pk)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(admin.has_muted_post_with_id(post.pk))

    def test_can_unmute_closed_community_post_if_moderator(self):
        """
        should be able to unmute closed post if moderator in community
        """
        user = make_user()

        admin = make_user()
        moderator = make_user()
        community = make_community(creator=admin)
        user.join_community_with_name(community_name=community.name)
        moderator.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=moderator.username, community_name=community.name)

        headers = make_authentication_headers_for_user(moderator)
        post = user.create_community_post(text=make_fake_post_text(), community_name=community.name)
        moderator.mute_post_with_id(post.pk)
        post.is_closed = True
        post.save()

        url = self._get_url(post)

        response = self.client.post(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(moderator.has_muted_post_with_id(post.pk))

    def _get_url(self, post):
        return reverse('unmute-post', kwargs={
            'post_uuid': post.uuid
        })


class PostCommentsAPITests(APITestCase):
    """
    PostCommentsAPI
    """

    fixtures = [
        'openbook_circles/fixtures/circles.json'
    ]

    def test_can_retrieve_comments_from_public_community_post(self):
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        post_creator = make_user()
        community = make_community(creator=post_creator)
        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            commenter.join_community_with_name(community_name=community.name)
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_can_retrieve_comments_from_closed_public_community_post_if_creator(self):
        """
        should be able to retrieve comments for closed posts if creator
        """

        post_creator = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(post_creator)
        community = make_community(creator=admin)
        post_creator.join_community_with_name(community_name=community.name)
        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            commenter.join_community_with_name(community_name=community.name)
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)
        # now close the post
        post.is_closed = True
        post.save()
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_can_retrieve_comments_from_closed_public_community_post_if_administrator(self):
        """
        should be able to retrieve comments for closed posts if administrator
        """

        post_creator = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(admin)
        community = make_community(creator=admin)
        post_creator.join_community_with_name(community_name=community.name)
        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            commenter.join_community_with_name(community_name=community.name)
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)
        # now close the post
        post.is_closed = True
        post.save()
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_can_retrieve_comments_from_closed_public_community_post_if_moderator(self):
        """
        should be able to retrieve comments for closed posts if moderator
        """

        post_creator = make_user()
        admin = make_user()
        moderator = make_user()
        headers = make_authentication_headers_for_user(moderator)
        community = make_community(creator=admin)

        moderator.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=moderator.username, community_name=community.name)

        post_creator.join_community_with_name(community_name=community.name)
        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            commenter.join_community_with_name(community_name=community.name)
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)
        # now close the post
        post.is_closed = True
        post.save()
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_cant_retrieve_comments_from_private_community_post(self):
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        post_creator = make_user()
        community = make_private_community(creator=post_creator)
        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            post_creator.invite_user_with_username_to_community_with_name(username=commenter.username,
                                                                          community_name=community.name)
            commenter.join_community_with_name(community_name=community.name)
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_retrieve_comments_from_private_community_part_of_post(self):
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        post_creator = make_user()
        community = make_private_community(creator=post_creator)
        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        post_creator.invite_user_with_username_to_community_with_name(username=user.username,
                                                                      community_name=community.name)
        user.join_community_with_name(community_name=community.name)

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            post_creator.invite_user_with_username_to_community_with_name(username=commenter.username,
                                                                          community_name=community.name)
            commenter.join_community_with_name(community_name=community.name)
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_can_retrieve_comments_from_public_post(self):
        """
         should be able to retrieve the comments from an own public post and return 200
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        post_creator = make_user()
        post = post_creator.create_public_post(text=make_fake_post_text())

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_can_retrieve_comments_from_own_public_post(self):
        """
         should be able to retrieve the comments from an own public post and return 200
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_can_retrieve_comments_from_own_encircled_post(self):
        """
         should be able to retrieve the comments from an own encircled post and return 200
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        circle = make_circle(creator=user)
        post = user.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            commenter.connect_with_user_with_id(user.pk)
            user.confirm_connection_with_user_with_id(user_id=commenter.pk, circles_ids=[circle.pk])
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_can_retrieve_comments_from_encircled_post_part_of(self):
        """
         should be able to retrieve the comments from an encircled post part of and return 200
         """
        post_creator = make_user()
        circle = make_circle(creator=post_creator)
        user = make_user()

        user.connect_with_user_with_id(post_creator.pk)
        post_creator.confirm_connection_with_user_with_id(user_id=user.pk, circles_ids=[circle.pk])

        post = post_creator.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        amount_of_comments = 5
        comments_ids = []

        for i in range(0, amount_of_comments):
            commenter = make_user()
            commenter.connect_with_user_with_id(post_creator.pk)
            post_creator.confirm_connection_with_user_with_id(user_id=commenter.pk, circles_ids=[circle.pk])
            post_comment = commenter.comment_post(post=post, text=make_fake_post_text())
            comments_ids.append(post_comment.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), amount_of_comments)

        for response_comment in response_comments:
            response_comment_id = response_comment.get('id')
            self.assertIn(response_comment_id, comments_ids)

    def test_cannot_retrieve_comments_from_encircled_post_not_part_of(self):
        """
         should not be able to retrieve the comments from an encircled post not part of and return 200
         """
        post_creator = make_user()
        circle = make_circle(creator=post_creator)
        user = make_user()

        post = post_creator.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        amount_of_comments = 5

        for i in range(0, amount_of_comments):
            commenter = make_user()
            commenter.connect_with_user_with_id(post_creator.pk)
            post_creator.confirm_connection_with_user_with_id(user_id=commenter.pk, circles_ids=[circle.pk])

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_retrieve_comments_from_blocked_user(self):
        """
         should not be able to retrieve the comments from a blocked user
         """
        user = make_user()

        post_creator = make_user()
        blocked_user = make_user()

        post = post_creator.create_public_post(text=make_fake_post_text())

        blocked_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=blocked_user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), 0)

    def test_cannot_retrieve_comments_from_blocking_user(self):
        """
         should not be able to retrieve the comments from a blocking user
         """
        user = make_user()

        post_creator = make_user()
        blocking_user = make_user()

        post = post_creator.create_public_post(text=make_fake_post_text())

        blocking_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        blocking_user.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), 0)

    def test_cannot_retrieve_comments_from_blocked_user_in_a_community(self):
        """
         should not be able to retrieve the comments from a blocked user in a community
         """
        user = make_user()

        post_creator = make_user()
        community = make_community(creator=post_creator)

        blocked_user = make_user()

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        blocked_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=blocked_user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), 0)

    def test_cannot_retrieve_comments_from_blocking_user_in_a_community(self):
        """
         should not be able to retrieve the comments from a blocking user in a community
         """
        user = make_user()

        post_creator = make_user()
        community = make_community(creator=post_creator)

        blocking_user = make_user()

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        blocking_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        blocking_user.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_comments = json.loads(response.content)

        self.assertEqual(len(response_comments), 0)

    def test_can_retrieve_comments_from_blocked_user_in_a_community_if_staff(self):
        """
         should be able to retrieve the comments from a blocked user in a community if staff member
         """
        user = make_user()
        community = make_community(creator=user)
        post_creator = make_user()
        blocked_user = make_user()

        post_creator.join_community_with_name(community_name=community.name)

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        post_comment = blocked_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=blocked_user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_comments = json.loads(response.content)

        self.assertEqual(1, len(response_comments))

        self.assertEqual(response_comments[0]['id'], post_comment.pk)

    def test_can_retrieve_comments_from_blocking_user_in_a_community_if_staff(self):
        """
         should be able to retrieve the comments from a blocking user in a community if staff member
         """
        user = make_user()
        community = make_community(creator=user)
        post_creator = make_user()
        blocking_user = make_user()

        post_creator.join_community_with_name(community_name=community.name)

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        post_comment = blocking_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        blocking_user.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_comments = json.loads(response.content)

        self.assertEqual(1, len(response_comments))

        self.assertEqual(response_comments[0]['id'], post_comment.pk)

    def test_can_comment_in_own_post(self):
        """
         should be able to comment in own post and return 201
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).count() == 1)

    def test_cannot_comment_in_foreign_post(self):
        """
         should not be able to comment in a foreign encircled post and return 400
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        foreign_user = make_user()
        circle = make_circle(creator=foreign_user)
        post = foreign_user.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).count() == 0)

    def test_can_comment_in_connected_user_public_post(self):
        """
         should be able to comment in the public post of a connected user post and return 201
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_connect = make_user()

        user.connect_with_user_with_id(user_to_connect.pk)

        connected_user_post = user_to_connect.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(connected_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=connected_user_post.pk, text=post_comment_text).count() == 1)

    def test_cannot_comment_in_blocked_user_post(self):
        """
          should not be able to comment in a blocked user post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_block = make_user()

        user.follow_user_with_id(user_to_block.pk)

        post = user_to_block.create_public_post(text=make_fake_post_text())

        user.block_user_with_id(user_id=user_to_block.pk)

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_cannot_comment_in_blocking_user_post(self):
        """
          should not be able to comment in a blocking user post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_block = make_user()

        user.follow_user_with_id(user_to_block.pk)

        post = user_to_block.create_public_post(text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user_to_block.block_user_with_id(user_id=user.pk)

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_cannot_comment_in_blocked_user_community_post(self):
        """
          should not be able to comment in a blocked user community post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user_to_block = make_user()

        user_to_block.join_community_with_name(community_name=community.name)

        post = user_to_block.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=user_to_block.pk)

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_cannot_comment_in_blocking_user_community_post(self):
        """
          should not be able to comment in a blocking user community post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user_to_block = make_user()

        user_to_block.join_community_with_name(community_name=community.name)

        post = user_to_block.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user_to_block.block_user_with_id(user_id=user.pk)

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_can_comment_in_blocked_community_staff_member_post(self):
        """
          should be able to comment in a blocked community staff member post and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        post = community_owner.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=community_owner.pk)

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).count() == 1)

    def test_can_comment_in_blocking_community_staff_member_post(self):
        """
          should be able to comment in a blocking community staff member post and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        post = community_owner.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=community_owner.pk)

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).count() == 1)

    def test_owner_cannot_comment_in_community_post_with_disabled_comments(self):
        """
         should not be able to comment in the community post with comments disabled even if owner of post
         """
        user = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(user)

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_foreign_user_cannot_comment_in_community_post_with_disabled_comments(self):
        """
         should not be able to comment in the community post with comments disabled even if foreign user
         """
        user = make_user()
        foreign_user = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(foreign_user)

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        foreign_user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_administrator_can_comment_in_community_post_with_disabled_comments(self):
        """
         should be able to comment in the community post with comments disabled if administrator
         """
        user = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(admin)

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)
        parsed_response = json.loads(response.content)

        response_id = parsed_response['id']
        post_comment = PostComment.objects.get(post_id=post.pk, text=post_comment_text, commenter=admin)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())
        self.assertEqual(response_id, post_comment.id)

    def test_moderator_can_comment_in_community_post_with_disabled_comments(self):
        """
         should be able to comment in the community post with comments disabled if moderator
         """
        user = make_user()
        admin = make_user()
        moderator = make_user()

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        moderator.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=moderator.username,
                                                                 community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(moderator)
        response = self.client.put(url, data, **headers)
        parsed_response = json.loads(response.content)

        response_id = parsed_response['id']
        post_comment = PostComment.objects.get(post_id=post.pk, text=post_comment_text, commenter=moderator)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())
        self.assertEqual(response_id, post_comment.id)

    def test_owner_can_comment_on_closed_community_post(self):
        """
         should be able to comment in the community post which is closed
         """
        user = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(user)

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.is_closed = True
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_foreign_user_cannot_comment_on_closed_community_post(self):
        """
         should not be able to comment in the community post that is closed
         """
        user = make_user()
        foreign_user = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(foreign_user)

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        foreign_user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.is_closed = True
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())

    def test_moderator_can_comment_on_closed_community_post(self):
        """
         should be able to comment on the community post which is closed if moderator
         """
        user = make_user()
        admin = make_user()
        moderator = make_user()

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        moderator.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=moderator.username, community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(moderator)
        response = self.client.put(url, data, **headers)
        parsed_response = json.loads(response.content)

        response_id = parsed_response['id']
        post_comment = PostComment.objects.get(post_id=post.pk, text=post_comment_text, commenter=moderator)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())
        self.assertEqual(response_id, post_comment.id)

    def test_administrator_can_comment_on_closed_community_post(self):
        """
         should be able to comment in the community post which is closed if administrator
         """
        user = make_user()
        admin = make_user()
        headers = make_authentication_headers_for_user(admin)

        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.is_closed = True
        post.save()
        post_comment_text = make_fake_post_comment_text()
        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)
        parsed_response = json.loads(response.content)

        response_id = parsed_response['id']
        post_comment = PostComment.objects.get(post_id=post.pk, text=post_comment_text, commenter=admin)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=post_comment_text).exists())
        self.assertEqual(response_id, post_comment.id)

    def test_can_comment_in_connected_user_encircled_post_part_of(self):
        """
          should be able to comment in the encircled post of a connected user which the user is part of and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk, circles_ids=[circle.pk])

        connected_user_post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(connected_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=connected_user_post.pk, text=post_comment_text).count() == 1)

    def test_cannot_comment_in_connected_user_encircled_post_not_part_of(self):
        """
             should NOT be able to comment in the encircled post of a connected user which the user is NOT part of and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        # Note there is no confirmation of the connection on the other side

        connected_user_post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(connected_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(PostComment.objects.filter(post_id=connected_user_post.pk, text=post_comment_text).count() == 0)

    def test_can_comment_in_user_public_post(self):
        """
          should be able to comment in the public post of any user and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        foreign_user = make_user()

        foreign_user_post = foreign_user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(foreign_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostComment.objects.filter(post_id=foreign_user_post.pk, text=post_comment_text).count() == 1)

    def test_cannot_comment_in_followed_user_encircled_post(self):
        """
          should be able to comment in the encircled post of a followed user return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_follow = make_user()
        circle = make_circle(creator=user_to_follow)

        user.follow_user_with_id(user_to_follow.pk)

        followed_user_post = user_to_follow.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(followed_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(post_id=followed_user_post.pk, text=post_comment_text).count() == 0)

    def test_cannot_comment_in_post_from_community_banned_from(self):
        """
          should not be able to comment in the post of a community banned from and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user.join_community_with_name(community_name=community.name)

        post = community_owner.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post(post=post, text=make_fake_post_comment_text())

        community_owner.ban_user_with_username_from_community_with_name(username=user.username,
                                                                        community_name=community.name)

        new_post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(new_post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=new_post_comment_text).count() == 0)

    def test_cannot_comment_in_own_post_from_community_banned_from(self):
        """
          should not be able to comment in own post of a community banned from and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user.join_community_with_name(community_name=community.name)

        post = user.create_community_post(community_name=community.name, text=make_fake_post_text())

        community_owner.ban_user_with_username_from_community_with_name(username=user.username,
                                                                        community_name=community.name)

        new_post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(new_post_comment_text)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(post_id=post.pk, text=new_post_comment_text).count() == 0)

    def test_commenting_in_foreign_post_creates_notification(self):
        """
         should create a notification when commenting on a foreign post
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        foreign_user = make_user()

        post = foreign_user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        self.assertTrue(PostCommentNotification.objects.filter(post_comment__text=post_comment_text,
                                                               notification__owner=foreign_user).exists())

    def test_commenting_in_own_post_does_not_create_notification(self):
        """
         should not create a notification when commenting on an own post
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        self.assertFalse(PostCommentNotification.objects.filter(post_comment__text=post_comment_text,
                                                                notification__owner=user).exists())

    def test_commenting_in_commented_post_by_foreign_user_creates_foreign_notification(self):
        """
         should create a notification when a user comments in a post where a foreign user commented before
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        post_creator = make_user()

        foreign_user = make_user()

        post = post_creator.create_public_post(text=make_fake_post_text())

        foreign_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        self.assertTrue(PostCommentNotification.objects.filter(post_comment__text=post_comment_text,
                                                               notification__owner=foreign_user).exists())

    def test_commenting_in_commented_post_by_foreign_user_not_creates_foreign_notification_when_muted(self):
        """
         should NOT create a notification when a user comments in a post where a foreign user commented and muted before
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        post_creator = make_user()

        foreign_user = make_user()

        post = post_creator.create_public_post(text=make_fake_post_text())

        foreign_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        foreign_user.mute_post_with_id(post_id=post.pk)

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        self.assertFalse(PostCommentNotification.objects.filter(post_comment__text=post_comment_text,
                                                                notification__owner=foreign_user).exists())

    def test_comment_in_an_encircled_post_with_a_user_removed_from_the_circle_not_notifies_it(self):
        """
         should not create a comment notification for a user that has been been removed from an encircled post circle
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        post_owner = make_user()
        foreign_user = make_user()
        circle = make_circle(creator=post_owner)

        user.connect_with_user_with_id(user_id=post_owner.pk)
        post_owner.confirm_connection_with_user_with_id(user_id=user.pk, circles_ids=[circle.pk])

        foreign_user.connect_with_user_with_id(user_id=post_owner.pk)
        post_owner.confirm_connection_with_user_with_id(user_id=foreign_user.pk, circles_ids=[circle.pk])

        post = post_owner.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        # Comment so we "subscribe" for notifications
        foreign_user.comment_post_with_id(post_id=post.pk, text=make_fake_post_text())

        # Remove him from the circles
        post_owner.update_connection_with_user_with_id(user_id=foreign_user.pk,
                                                       circles_ids=[post_owner.connections_circle_id])

        post_comment_text = make_fake_post_comment_text()

        data = self._get_create_post_comment_request_data(post_comment_text)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        self.assertFalse(PostCommentNotification.objects.filter(post_comment__text=post_comment_text,
                                                                notification__owner=foreign_user).exists())

    def test_should_retrieve_all_comments_on_public_post(self):
        """
        should retrieve all comments on public post
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        amount_of_post_comments = 10
        post_comments = []

        for i in range(amount_of_post_comments):
            post_comment_text = make_fake_post_comment_text()
            post_comments.append(user.comment_post_with_id(post_id=post.pk, text=post_comment_text))

        url = self._get_url(post)
        response = self.client.get(url, **headers)
        parsed_response = json.loads(response.content)
        response_ids = [comment['id'] for comment in parsed_response]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(parsed_response) == amount_of_post_comments)

        for comment in post_comments:
            self.assertTrue(comment.pk in response_ids)

    def test_should_retrieve_all_comments_on_public_post_with_sort(self):
        """
        should retrieve all comments on public post with sort ascending
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        amount_of_post_comments = 10
        post_comments = []

        for i in range(amount_of_post_comments):
            post_comment_text = make_fake_post_comment_text()
            post_comments.append(user.comment_post_with_id(post_id=post.pk, text=post_comment_text))

        url = self._get_url(post)
        response = self.client.get(url, {'sort': 'ASC'}, **headers)
        parsed_response = json.loads(response.content)
        response_ids = [comment['id'] for comment in parsed_response]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(parsed_response) == amount_of_post_comments)

        for comment in post_comments:
            self.assertTrue(comment.pk in response_ids)

    def test_should_retrieve_comments_less_than_max_id_on_post(self):
        """
        should retrieve comments less than max id for post if param is present
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        amount_of_post_comments = 10
        post_comments = []

        for i in range(amount_of_post_comments):
            post_comment_text = make_fake_post_comment_text()
            post_comments.append(user.comment_post_with_id(post_id=post.pk, text=post_comment_text))

        random_int = random.randint(3, 9)
        max_id = post_comments[random_int].pk

        url = self._get_url(post)
        response = self.client.get(url, {
            'max_id': max_id
        }, **headers)
        parsed_response = json.loads(response.content)
        response_ids = [comment['id'] for comment in parsed_response]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for returned_id in response_ids:
            self.assertTrue(returned_id < max_id)

    def test_should_retrieve_comments_greater_than_or_equal_to_min_id(self):
        """
        should retrieve comments greater than or equal to min_id for post if param is present
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        amount_of_post_comments = 10
        post_comments = []

        for i in range(amount_of_post_comments):
            post_comment_text = make_fake_post_comment_text()
            post_comments.append(user.comment_post_with_id(post_id=post.pk, text=post_comment_text))

        random_int = random.randint(3, 9)
        min_id = post_comments[random_int].pk

        url = self._get_url(post)
        response = self.client.get(url, {
            'min_id': min_id
        }, **headers)
        parsed_response = json.loads(response.content)
        response_ids = [comment['id'] for comment in parsed_response]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for returned_id in response_ids:
            self.assertTrue(returned_id >= min_id)

    def test_should_retrieve_comments_slice_for_min_id_and_max_id(self):
        """
        should retrieve comments slice for post comments taking into account min_id and max_id
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        amount_of_post_comments = 20
        post_comments = []

        for i in range(amount_of_post_comments):
            post_comment_text = make_fake_post_comment_text()
            post_comments.append(user.comment_post_with_id(post_id=post.pk, text=post_comment_text))

        random_int = random.randint(3, 17)
        min_id = post_comments[random_int].pk
        max_id = min_id
        count_max = 2
        count_min = 3

        url = self._get_url(post)
        response = self.client.get(url, {
            'min_id': min_id,
            'max_id': max_id,
            'count_max': count_max,
            'count_min': count_min
        }, **headers)
        parsed_response = json.loads(response.content)
        response_ids = [int(comment['id']) for comment in parsed_response]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(parsed_response) == (count_max + count_min))
        comments_after_min_id = [id for id in response_ids if id >= min_id]
        comments_before_max_id = [id for id in response_ids if id < max_id]
        self.assertTrue(len(comments_after_min_id) == count_min)
        self.assertTrue(len(comments_before_max_id) == count_max)

    def test_should_retrieve_comments_slice_with_sort_for_min_id_and_max_id(self):
        """
        should retrieve comments slice sorted ascending for post comments taking into account min_id and max_id
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        amount_of_post_comments = 20
        post_comments = []

        for i in range(amount_of_post_comments):
            post_comment_text = make_fake_post_comment_text()
            post_comments.append(user.comment_post_with_id(post_id=post.pk, text=post_comment_text))

        random_int = random.randint(3, 17)
        min_id = post_comments[random_int].pk
        max_id = min_id
        count_max = 2
        count_min = 3

        url = self._get_url(post)
        response = self.client.get(url, {
            'min_id': min_id,
            'max_id': max_id,
            'count_max': count_max,
            'count_min': count_min,
            'sort': 'ASC'
        }, **headers)
        parsed_response = json.loads(response.content)
        response_ids = [int(comment['id']) for comment in parsed_response]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(parsed_response) == (count_max + count_min))
        self.assertTrue(sorted(response_ids) == response_ids)
        comments_after_min_id = [id for id in response_ids if id >= min_id]
        comments_before_max_id = [id for id in response_ids if id < max_id]
        self.assertTrue(len(comments_after_min_id) == count_min)
        self.assertTrue(len(comments_before_max_id) == count_max)

    def _get_create_post_comment_request_data(self, post_comment_text):
        return {
            'text': post_comment_text
        }

    def _get_url(self, post):
        return reverse('post-comments', kwargs={
            'post_uuid': post.uuid,
        })


class PostCommentItemAPITests(APITestCase):
    """
    PostCommentItemAPI
    """

    fixtures = [
        'openbook_circles/fixtures/circles.json'
    ]

    def test_cannot_delete_foreign_comment_in_own_post(self):
        """
          should not be able to delete a foreign comment in own post and return 200
        """
        user = make_user()

        commenter = make_user()

        post = user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = commenter.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 1)

    def test_can_delete_community_post_comment_if_mod(self):
        """
         should be able to delete a community post comment if is moderator and return 200
         """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_moderator_with_username_to_community_with_name(username=user.username,
                                                                             community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        community_post_commentator = make_user()
        community_post_commentator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_commentator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_can_delete_community_post_comment_if_admin(self):
        """
         should be able to delete a community post comment if is administrator and return 200
         """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_administrator_with_username_to_community_with_name(username=user.username,
                                                                                 community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        community_post_commentator = make_user()
        community_post_commentator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_commentator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_can_delete_community_post_comment_for_post_with_disabled_comments_if_comment_owner(self):
        """
         should be able to delete a community post comment for post with disabled comments if comment owner
         """
        user = make_user()

        admin = make_user()
        community = make_community(creator=admin)

        user.join_community_with_name(community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        commenter = make_user()
        commenter.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = commenter.comment_post_with_id(text=make_fake_post_comment_text(),
                                                      post_id=post.pk)

        post.comments_enabled = False
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(commenter)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_can_delete_community_post_comment_with_disabled_comments_if_admin(self):
        """
         should be able to delete a community post comment for post with comments disabled if administrator
         """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_administrator_with_username_to_community_with_name(username=user.username,
                                                                                 community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        community_post_commentator = make_user()
        community_post_commentator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_commentator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        post.comments_enabled = False
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_can_delete_community_post_comment_for_post_with_disabled_comments_if_moderator(self):
        """
         should be able to delete a community post comment for post with disabled comments if moderator
         """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_moderator_with_username_to_community_with_name(username=user.username,
                                                                             community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        community_post_commentator = make_user()
        community_post_commentator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_commentator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        post.comments_enabled = False
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_can_delete_community_post_comment_with_closed_post_if_admin(self):
        """
         should be able to delete a community post comment for closed post if administrator
         """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_administrator_with_username_to_community_with_name(username=user.username,
                                                                                 community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        community_post_commentator = make_user()
        community_post_commentator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_commentator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        post.is_closed = True
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_can_delete_community_post_comment_for_closed_post_if_moderator(self):
        """
         should be able to delete a community post comment for closed post if moderator
         """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_moderator_with_username_to_community_with_name(username=user.username,
                                                                             community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        community_post_commentator = make_user()
        community_post_commentator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_commentator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        post.is_closed = True
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_cannot_delete_community_post_comment_for_closed_post_if_comment_owner(self):
        """
         should NOT be able to delete a community post comment for closed post if comment owner
         """
        user = make_user()

        admin = make_user()
        community = make_community(creator=admin)

        user.join_community_with_name(community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        commenter = make_user()
        commenter.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = commenter.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        post.is_closed = True
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(commenter)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_can_delete_own_community_post_comment_for_closed_post_if_post_creator(self):
        """
         should be able to delete own community post comment for closed post if post creator
         """
        user = make_user()

        admin = make_user()
        community = make_community(creator=admin)

        user.join_community_with_name(community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_creator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                      post_id=post.pk)

        post.is_closed = True
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(community_post_creator)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PostComment.objects.filter(id=post_comment.pk).exists())

    def test_logs_community_post_comment_deleted_by_non_creator(self):
        """
        should create a log when a community post comment was deleted by an admin/moderator
        """
        user = make_user()

        community_creator = make_user()
        community = make_community(creator=community_creator)

        user.join_community_with_name(community_name=community.name)
        community_creator.add_administrator_with_username_to_community_with_name(username=user.username,
                                                                                 community_name=community.name)

        community_post_creator = make_user()
        community_post_creator.join_community_with_name(community_name=community.name)

        community_post_commentator = make_user()
        community_post_commentator.join_community_with_name(community_name=community.name)

        post = community_post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)
        post_comment = community_post_commentator.comment_post_with_id(text=make_fake_post_comment_text(),
                                                                       post_id=post.pk)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        self.client.delete(url, **headers)

        self.assertTrue(
            community.logs.filter(action_type='RPC', target_user=community_post_commentator, source_user=user).exists())

    def test_can_delete_own_comment_in_foreign_public_post(self):
        """
          should be able to delete own comment in foreign public post and return 200
        """
        user = make_user()

        foreign_user = make_user()

        post = foreign_user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 0)

    def test_cannot_delete_foreign_comment_in_foreign_public_post(self):
        """
          should NOT be able to delete foreign comment in foreign public post and return 400
        """
        user = make_user()

        foreign_user = make_user()

        post = foreign_user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = foreign_user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 1)

    def test_can_delete_own_comment_in_connected_user_public_post(self):
        """
          should be able to delete own comment in a connected user public post and return 200
        """
        user = make_user()

        user_to_connect = make_user()

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk)

        post = user_to_connect.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 0)

    def test_cannot_delete_foreign_comment_in_connected_user_public_post(self):
        """
          should not be able to delete foreign comment in a connected user public post and return 400
        """
        user = make_user()

        user_to_connect = make_user()

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk)

        foreign_user = make_user()

        post = user_to_connect.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = foreign_user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 1)

    def test_can_delete_own_comment_in_connected_user_encircled_post_part_of(self):
        """
           should be able to delete own comment in a connected user encircled post it's part of and return 200
         """
        user = make_user()

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk, circles_ids=[circle.pk])

        post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        post_comment = user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 0)

    def test_cannot_delete_foreign_comment_in_connected_user_encircled_post_part_of(self):
        """
           should NOT be able to delete foreign comment in a connected user encircled post it's part of and return 400
         """
        user = make_user()

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk, circles_ids=[circle.pk])

        foreign_user = make_user()
        foreign_user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(foreign_user.pk, circles_ids=[circle.pk])

        post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        post_comment = foreign_user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 1)

    def test_cannot_delete_foreign_comment_in_connected_user_encircled_post_not_part_of(self):
        """
           should NOT be able to delete foreign comment in a connected user encircled post NOT part of and return 400
         """
        user = make_user()

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        foreign_user = make_user()
        foreign_user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(foreign_user.pk, circles_ids=[circle.pk])

        post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        post_comment = foreign_user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 1)

    def test_can_delete_own_comment_in_followed_user_public_post(self):
        """
           should be able to delete own comment in a followed user public post and return 200
         """
        user = make_user()

        user_to_follow = make_user()

        user.follow_user_with_id(user_to_follow.pk)

        post = user_to_follow.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 0)

    def test_cannot_delete_foreign_comment_in_followed_user_public_post(self):
        """
           should not be able to delete foreign comment in a followed user public post and return 400
         """
        user = make_user()

        user_to_follow = make_user()

        user.follow_user_with_id(user_to_follow.pk)

        foreign_user = make_user()

        post = user_to_follow.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = foreign_user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 1)

    def test_cannot_delete_foreign_comment_in_folowed_user_encircled_post(self):
        """
            should not be able to delete foreign comment in a followed user encircled post and return 400
        """
        user = make_user()

        user_to_follow = make_user()
        circle = make_circle(creator=user_to_follow)

        user.follow_user_with_id(user_to_follow.pk)

        foreign_user = make_user()
        foreign_user.connect_with_user_with_id(user_to_follow.pk)
        user_to_follow.confirm_connection_with_user_with_id(foreign_user.pk, circles_ids=[circle.pk])

        post = user_to_follow.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        post_comment_text = make_fake_post_comment_text()

        post_comment = foreign_user.comment_post_with_id(post.pk, text=post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostComment.objects.filter(id=post_comment.pk).count() == 1)

    def test_post_comment_notification_is_deleted_when_deleting_comment(self):
        """
            should delete the post comment notification when a post comment is deleted
        """
        user = make_user()

        commenter = make_user()

        post = user.create_public_post(text=make_fake_post_text())

        post_comment_text = make_fake_post_comment_text()

        post_comment = commenter.comment_post_with_id(post.pk, text=post_comment_text)

        post_comment_notification = PostCommentNotification.objects.get(post_comment=post_comment,
                                                                        notification__owner=user)
        notification = Notification.objects.get(notification_type=Notification.POST_COMMENT,
                                                object_id=post_comment_notification.pk)

        url = self._get_url(post_comment=post_comment, post=post)

        headers = make_authentication_headers_for_user(commenter)
        self.client.delete(url, **headers)

        self.assertFalse(PostCommentNotification.objects.filter(pk=post_comment_notification.pk).exists())
        self.assertFalse(Notification.objects.filter(pk=notification.pk).exists())

    def test_can_edit_own_post_comment_on_own_post(self):
        """
            should be able to edit own post comment
        """

        user = make_user()
        post = user.create_public_post(text=make_fake_post_text())
        original_post_comment_text = make_fake_post_comment_text()
        post_comment = user.comment_post_with_id(post.pk, text=original_post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        edited_post_comment_text = make_fake_post_comment_text()
        headers = make_authentication_headers_for_user(user)

        response = self.client.patch(url, {
            'text': edited_post_comment_text
        }, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post_comment.refresh_from_db()
        self.assertTrue(post_comment.text == edited_post_comment_text)
        self.assertTrue(post_comment.is_edited)

    def test_can_edit_own_post_comment_on_others_post(self):
        """
            should be able to edit own post comment on someone else's post
        """

        user = make_user()
        post_creator = make_user()
        post = post_creator.create_public_post(text=make_fake_post_text())
        original_post_comment_text = make_fake_post_comment_text()
        post_comment = user.comment_post_with_id(post.pk, text=original_post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        edited_post_comment_text = make_fake_post_comment_text()
        headers = make_authentication_headers_for_user(user)

        response = self.client.patch(url, {
            'text': edited_post_comment_text
        }, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post_comment.refresh_from_db()
        self.assertTrue(post_comment.text == edited_post_comment_text)

    def test_cannot_edit_others_post_comment(self):
        """
            should not be able to edit someone else's comment
        """

        user = make_user()
        commenter = make_user()
        post = user.create_public_post(text=make_fake_post_text())
        original_post_comment_text = make_fake_post_comment_text()
        post_comment = commenter.comment_post_with_id(post.pk, text=original_post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        edited_post_comment_text = make_fake_post_comment_text()
        headers = make_authentication_headers_for_user(user)

        response = self.client.patch(url, {
            'text': edited_post_comment_text
        }, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        post_comment.refresh_from_db()
        self.assertTrue(post_comment.text == original_post_comment_text)
        self.assertFalse(post_comment.is_edited)

    def test_cannot_edit_post_comment_if_comments_disabled(self):
        """
            should not be able to edit own comment if comments are disabled
        """

        admin = make_user()
        user = make_user()
        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())

        original_post_comment_text = make_fake_post_comment_text()
        post_comment = user.comment_post_with_id(post.pk, text=original_post_comment_text)

        post.comments_enabled = False
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        edited_post_comment_text = make_fake_post_comment_text()
        headers = make_authentication_headers_for_user(user)

        response = self.client.patch(url, {
            'text': edited_post_comment_text
        }, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        post_comment.refresh_from_db()
        self.assertTrue(post_comment.text == original_post_comment_text)
        self.assertFalse(post_comment.is_edited)

    def test_cannot_edit_post_comment_if_post_closed_and_not_not_post_creator(self):
        """
            should NOT be able to edit own comment if post is closed and not post creator
        """

        admin = make_user()
        user = make_user()
        community = make_community(admin)
        user.join_community_with_name(community_name=community.name)
        post = admin.create_community_post(community.name, text=make_fake_post_text())

        original_post_comment_text = make_fake_post_comment_text()
        post_comment = user.comment_post_with_id(post.pk, text=original_post_comment_text)

        post.is_closed = True
        post.save()

        url = self._get_url(post_comment=post_comment, post=post)

        edited_post_comment_text = make_fake_post_comment_text()
        headers = make_authentication_headers_for_user(user)

        response = self.client.patch(url, {
            'text': edited_post_comment_text
        }, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        post_comment.refresh_from_db()
        self.assertTrue(post_comment.text == original_post_comment_text)
        self.assertFalse(post_comment.is_edited)

    def test_cannot_edit_others_community_post_comment_even_if_admin(self):
        """
            should not be able to edit someone else's comment even if community admin
        """

        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        original_post_comment_text = make_fake_post_comment_text()
        post_comment = user.comment_post_with_id(post.pk, text=original_post_comment_text)

        url = self._get_url(post_comment=post_comment, post=post)

        edited_post_comment_text = make_fake_post_comment_text()
        headers = make_authentication_headers_for_user(admin)

        response = self.client.patch(url, {
            'text': edited_post_comment_text
        }, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        post_comment.refresh_from_db()
        self.assertTrue(post_comment.text == original_post_comment_text)

    def _get_url(self, post, post_comment):
        return reverse('post-comment', kwargs={
            'post_uuid': post.uuid,
            'post_comment_id': post_comment.pk
        })


class PostReactionsAPITests(APITestCase):
    """
    PostReactionsAPI
    """

    fixtures = [
        'openbook_circles/fixtures/circles.json'
    ]

    def test_can_react_to_own_post(self):
        """
         should be able to reaction in own post and return 201
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                                    reactor_id=user.pk).count() == 1)

    def test_cannot_react_to_foreign_post(self):
        """
         should not be able to reaction in a foreign encircled post and return 400
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        foreign_user = make_user()
        circle = make_circle(creator=foreign_user)
        post = foreign_user.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                                    reactor_id=user.pk).count() == 0)

    def test_cannot_react_to_foreign_post_with_non_reaction_emoji(self):
        """
         should not be able to reaction in a post with a non reaction emoji group and return 400
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        emoji_group = make_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                                    reactor_id=user.pk).count() == 0)

    def test_can_react_to_connected_user_public_post(self):
        """
         should be able to reaction in the public post of a connected user post and return 201
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_connect = make_user()

        user.connect_with_user_with_id(user_to_connect.pk)

        connected_user_post = user_to_connect.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(connected_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PostReaction.objects.filter(post_id=connected_user_post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 1)

    def test_can_react_to_connected_user_encircled_post_part_of(self):
        """
          should be able to reaction in the encircled post of a connected user which the user is part of and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk, circles_ids=[circle.pk])

        connected_user_post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(connected_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PostReaction.objects.filter(post_id=connected_user_post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 1)

    def test_cannot_react_to_connected_user_encircled_post_not_part_of(self):
        """
             should NOT be able to reaction in the encircled post of a connected user which the user is NOT part of and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        # Note there is no confirmation of the connection on the other side

        connected_user_post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(connected_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(
            PostReaction.objects.filter(post_id=connected_user_post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_can_react_to_user_public_post(self):
        """
          should be able to reaction in the public post of any user and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        foreign_user = make_user()

        foreign_user_post = foreign_user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(foreign_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PostReaction.objects.filter(post_id=foreign_user_post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 1)

    def test_cannot_react_to_followed_user_encircled_post(self):
        """
          should be able to reaction in the encircled post of a followed user return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_follow = make_user()
        circle = make_circle(creator=user_to_follow)

        user.follow_user_with_id(user_to_follow.pk)

        followed_user_post = user_to_follow.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(followed_user_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            PostReaction.objects.filter(post_id=followed_user_post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_cannot_react_in_post_from_community_banned_from(self):
        """
          should not be able to react in the post of a community banned from and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user.join_community_with_name(community_name=community.name)

        post = community_owner.create_community_post(community_name=community.name, text=make_fake_post_text())

        community_owner.ban_user_with_username_from_community_with_name(username=user.username,
                                                                        community_name=community.name)

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(
            PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_cannot_react_to_closed_community_post_if_not_creator(self):
        """
          should NOT be able to react in a closed community post if not creator
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)
        headers = make_authentication_headers_for_user(user)

        post_creator = make_user()
        post_creator.join_community_with_name(community_name=community.name)
        user.join_community_with_name(community_name=community.name)

        community_post = post_creator.create_community_post(community_name=community.name, text=make_fake_post_comment_text())
        community_post.is_closed = True
        community_post.save()

        emoji_group = make_reactions_emoji_group()
        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(community_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            PostReaction.objects.filter(post_id=community_post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_can_react_to_closed_community_post_if_creator(self):
        """
          should be able to react in a closed community post if creator
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        post_creator = make_user()
        post_creator.join_community_with_name(community_name=community.name)
        user.join_community_with_name(community_name=community.name)

        community_post = post_creator.create_community_post(community_name=community.name, text=make_fake_post_comment_text())
        community_post.is_closed = True
        community_post.save()

        emoji_group = make_reactions_emoji_group()
        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        headers = make_authentication_headers_for_user(post_creator)
        url = self._get_url(community_post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PostReaction.objects.filter(post_id=community_post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=post_creator.pk).count() == 1)

    def test_cannot_react_to_blocked_user_post(self):
        """
          should not be able to react to a blocked user post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_block = make_user()

        user.follow_user_with_id(user_to_block.pk)

        post = user_to_block.create_public_post(text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=user_to_block.pk)

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_cannot_react_to_blocking_user_post(self):
        """
          should not be able to react to a blocking user post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        user_to_block = make_user()

        user.follow_user_with_id(user_to_block.pk)

        post = user_to_block.create_public_post(text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user_to_block.block_user_with_id(user_id=user.pk)

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_cannot_react_to_blocked_user_community_post(self):
        """
          should not be able to react to a blocked user community post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user_to_block = make_user()

        user_to_block.join_community_with_name(community_name=community.name)

        post = user_to_block.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=user_to_block.pk)

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertTrue(
            PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_cannot_react_to_blocking_user_community_post(self):
        """
          should not be able to react to a blocking user community post and return 400
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        user_to_block = make_user()

        user_to_block.join_community_with_name(community_name=community.name)

        post = user_to_block.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user_to_block.block_user_with_id(user_id=user.pk)

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertTrue(
            PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 0)

    def test_can_react_to_blocked_community_staff_member_post(self):
        """
          should be able to react to a blocked community staff member post and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        post = community_owner.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=community_owner.pk)

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 1)

    def test_can_react_to_blocking_community_staff_member_post(self):
        """
          should be able to react to a blocking community staff member post and return 201
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        community_owner = make_user()
        community = make_community(creator=community_owner)

        post = community_owner.create_community_post(community_name=community.name, text=make_fake_post_text())

        user.comment_post_with_id(post_id=post.pk, text=make_fake_post_comment_text())

        user.block_user_with_id(user_id=community_owner.pk)

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PostReaction.objects.filter(post_id=post.pk, emoji_id=post_reaction_emoji_id,
                                        reactor_id=user.pk).count() == 1)

    def test_can_react_to_post_only_once(self):
        """
         should be able to reaction in own post only once, update the old reaction and return 201
         """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        new_post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(new_post_reaction_emoji_id, emoji_group.pk)
        response = self.client.put(url, data, **headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PostReaction.objects.filter(post_id=post.pk, reactor_id=user.pk).count() == 1)

    def test_reacting_in_foreign_post_creates_notification(self):
        """
         should create a notification when reacting on a foreign post
         """
        user = make_user()
        reactor = make_user()

        headers = make_authentication_headers_for_user(reactor)
        post = user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        self.assertTrue(PostReactionNotification.objects.filter(post_reaction__emoji__id=post_reaction_emoji_id,
                                                                notification__owner=user).exists())

    def test_reacting_in_own_post_does_not_create_notification(self):
        """
         should not create a notification when reacting on an own post
         """
        user = make_user()

        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        data = self._get_create_post_reaction_request_data(post_reaction_emoji_id, emoji_group.pk)

        url = self._get_url(post)
        self.client.put(url, data, **headers)

        self.assertFalse(PostReactionNotification.objects.filter(post_reaction__emoji__id=post_reaction_emoji_id,
                                                                 notification__owner=user).exists())

    def _get_create_post_reaction_request_data(self, emoji_id, emoji_group_id):
        return {
            'emoji_id': emoji_id,
            'group_id': emoji_group_id
        }

    def _get_url(self, post):
        return reverse('post-reactions', kwargs={
            'post_uuid': post.uuid,
        })


class PostReactionItemAPITests(APITestCase):
    """
    PostReactionItemAPI
    """

    fixtures = [
        'openbook_circles/fixtures/circles.json'
    ]

    def test_can_delete_foreign_reaction_in_own_post(self):
        """
          should be able to delete a foreign reaction in own post and return 200
        """
        user = make_user()

        reactioner = make_user()

        post = user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = reactioner.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                         emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 0)

    def test_can_delete_own_reaction_in_foreign_public_post(self):
        """
          should be able to delete own reaction in foreign public post and return 200
        """
        user = make_user()

        foreign_user = make_user()

        post = foreign_user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                   emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 0)

    def test_cannot_delete_foreign_reaction_in_foreign_public_post(self):
        """
          should NOT be able to delete foreign reaction in foreign public post and return 400
        """
        user = make_user()

        foreign_user = make_user()

        post = foreign_user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = foreign_user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                           emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 1)

    def test_cannot_delete_reaction_in_closed_community_post_when_not_creator(self):
        """
          should NOT be able to delete reaction in closed community post if not creator
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        post_creator = make_user()
        post_creator.join_community_with_name(community_name=community.name)
        user.join_community_with_name(community_name=community.name)

        community_post = post_creator.create_community_post(community_name=community.name, text=make_fake_post_comment_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = user.react_to_post_with_id(community_post.pk, emoji_id=post_reaction_emoji_id,
                                                           emoji_group_id=emoji_group.pk)
        # now close the post
        community_post.is_closed = True
        community_post.save()

        url = self._get_url(post_reaction=post_reaction, post=community_post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 1)

    def test_can_delete_reaction_in_closed_community_post_if_creator(self):
        """
          should be able to delete reaction in closed community post if creator
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        post_creator = make_user()
        post_creator.join_community_with_name(community_name=community.name)
        user.join_community_with_name(community_name=community.name)

        community_post = post_creator.create_community_post(community_name=community.name, text=make_fake_post_comment_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = user.react_to_post_with_id(community_post.pk, emoji_id=post_reaction_emoji_id,
                                                   emoji_group_id=emoji_group.pk)
        # now close the post
        community_post.is_closed = True
        community_post.save()

        url = self._get_url(post_reaction=post_reaction, post=community_post)

        headers = make_authentication_headers_for_user(post_creator)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 0)

    def test_can_delete_own_reaction_in_connected_user_public_post(self):
        """
          should be able to delete own reaction in a connected user public post and return 200
        """
        user = make_user()

        user_to_connect = make_user()

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk)

        post = user_to_connect.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                   emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 0)

    def test_cannot_delete_foreign_reaction_in_connected_user_public_post(self):
        """
          should not be able to delete foreign reaction in a connected user public post and return 400
        """
        user = make_user()

        user_to_connect = make_user()

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk)

        foreign_user = make_user()

        post = user_to_connect.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = foreign_user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                           emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 1)

    def test_can_delete_own_reaction_in_connected_user_encircled_post_part_of(self):
        """
           should be able to delete own reaction in a connected user encircled post it's part of and return 200
         """
        user = make_user()

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk, circles_ids=[circle.pk])

        post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                   emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 0)

    def test_cannot_delete_foreign_reaction_in_connected_user_encircled_post_part_of(self):
        """
           should NOT be able to delete foreign reaction in a connected user encircled post it's part of and return 400
         """
        user = make_user()

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(user.pk, circles_ids=[circle.pk])

        foreign_user = make_user()
        foreign_user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(foreign_user.pk, circles_ids=[circle.pk])

        post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = foreign_user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                           emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 1)

    def test_cannot_delete_foreign_reaction_in_connected_user_encircled_post_not_part_of(self):
        """
           should NOT be able to delete foreign reaction in a connected user encircled post NOT part of and return 400
         """
        user = make_user()

        user_to_connect = make_user()
        circle = make_circle(creator=user_to_connect)

        foreign_user = make_user()
        foreign_user.connect_with_user_with_id(user_to_connect.pk)
        user_to_connect.confirm_connection_with_user_with_id(foreign_user.pk, circles_ids=[circle.pk])

        post = user_to_connect.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = foreign_user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                           emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 1)

    def test_can_delete_own_reaction_in_followed_user_public_post(self):
        """
           should be able to delete own reaction in a followed user public post and return 200
         """
        user = make_user()

        user_to_follow = make_user()

        user.follow_user_with_id(user_to_follow.pk)

        post = user_to_follow.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                   emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 0)

    def test_cannot_delete_foreign_reaction_in_followed_user_public_post(self):
        """
           should not be able to delete foreign reaction in a followed user public post and return 400
         """
        user = make_user()

        user_to_follow = make_user()

        user.follow_user_with_id(user_to_follow.pk)

        foreign_user = make_user()

        post = user_to_follow.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = foreign_user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                           emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 1)

    def test_cannot_delete_foreign_reaction_in_folowed_user_encircled_post(self):
        """
             should not be able to delete foreign reaction in a followed user encircled post and return 400
        """
        user = make_user()

        user_to_follow = make_user()
        circle = make_circle(creator=user_to_follow)

        user.follow_user_with_id(user_to_follow.pk)

        foreign_user = make_user()
        foreign_user.connect_with_user_with_id(user_to_follow.pk)
        user_to_follow.confirm_connection_with_user_with_id(foreign_user.pk, circles_ids=[circle.pk])

        post = user_to_follow.create_encircled_post(text=make_fake_post_text(), circles_ids=[circle.pk])

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = foreign_user.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                           emoji_group_id=emoji_group.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.delete(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(PostReaction.objects.filter(id=post_reaction.pk).count() == 1)

    def test_post_reaction_notification_is_deleted_when_deleting_reaction(self):
        """
        should delete the post reaction notification when a post reaction is deleted
        """
        user = make_user()

        reactioner = make_user()

        post = user.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()

        post_reaction_emoji_id = make_emoji(group=emoji_group).pk

        post_reaction = reactioner.react_to_post_with_id(post.pk, emoji_id=post_reaction_emoji_id,
                                                         emoji_group_id=emoji_group.pk)

        post_reaction_notification = PostReactionNotification.objects.get(post_reaction=post_reaction,
                                                                          notification__owner=user)
        notification = Notification.objects.get(notification_type=Notification.POST_REACTION,
                                                object_id=post_reaction_notification.pk)

        url = self._get_url(post_reaction=post_reaction, post=post)

        headers = make_authentication_headers_for_user(user)
        self.client.delete(url, **headers)

        self.assertFalse(PostReactionNotification.objects.filter(pk=post_reaction_notification.pk).exists())
        self.assertFalse(Notification.objects.filter(pk=notification.pk).exists())

    def _get_url(self, post, post_reaction):
        return reverse('post-reaction', kwargs={
            'post_uuid': post.uuid,
            'post_reaction_id': post_reaction.pk
        })


class PostReactionsEmojiCountAPITests(APITestCase):
    """
    PostReactionsEmojiCountAPI
    """

    def test_can_retrieve_reactions_emoji_count(self):
        """
        should be able to retrieve a valid reactions emoji count and return 200
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)
        post = user.create_public_post(text=make_fake_post_text())
        emoji_group = make_reactions_emoji_group()

        emojis_to_react_with = [
            {
                'emoji': make_emoji(group=emoji_group),
                'count': 3
            },
            {
                'emoji': make_emoji(group=emoji_group),
                'count': 7
            },
            {
                'emoji': make_emoji(group=emoji_group),
                'count': 2
            }
        ]

        reactions = {}

        for reaction in emojis_to_react_with:
            id = reaction.get('emoji').pk
            reactions[str(id)] = reaction

        for reaction in emojis_to_react_with:
            for count in range(reaction['count']):
                reactor = make_user()
                emoji = reaction.get('emoji')
                reactor.react_to_post_with_id(post_id=post.pk, emoji_id=emoji.pk, emoji_group_id=emoji_group.pk)

        url = self._get_url(post)

        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_emojis_counts = json.loads(response.content)

        self.assertTrue(len(response_emojis_counts), len(emojis_to_react_with))

        for response_emoji_count in response_emojis_counts:
            response_emoji_id = response_emoji_count.get('emoji').get('id')
            count = response_emoji_count.get('count')
            reaction = reactions[str(response_emoji_id)]
            reaction_emoji = reaction['emoji']
            self.assertIsNotNone(reaction_emoji)
            reaction_count = reaction['count']
            self.assertEqual(count, reaction_count)

    def test_cannot_retrieve_reaction_from_blocked_user(self):
        """
         should not be able to retrieve the reaction from a blocked user
         """
        user = make_user()

        post_creator = make_user()
        blocked_user = make_user()

        post = post_creator.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()
        emoji = make_emoji(group=emoji_group)
        blocked_user.react_to_post_with_id(post_id=post.pk, emoji_id=emoji.pk, emoji_group_id=emoji_group.pk)

        user.block_user_with_id(user_id=blocked_user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_reactions = json.loads(response.content)

        self.assertEqual(len(response_reactions), 0)

    def test_cannot_retrieve_reactions_from_blocking_user(self):
        """
         should not be able to retrieve the reactions from a blocking user
         """
        user = make_user()

        post_creator = make_user()
        blocking_user = make_user()

        post = post_creator.create_public_post(text=make_fake_post_text())

        emoji_group = make_reactions_emoji_group()
        emoji = make_emoji(group=emoji_group)
        blocking_user.react_to_post_with_id(post_id=post.pk, emoji_id=emoji.pk, emoji_group_id=emoji_group.pk)

        blocking_user.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_reactions = json.loads(response.content)

        self.assertEqual(len(response_reactions), 0)

    def test_cannot_retrieve_reactions_from_blocked_user_in_a_community(self):
        """
         should not be able to retrieve the reactions from a blocked user in a community
         """
        user = make_user()

        post_creator = make_user()
        community = make_community(creator=post_creator)

        blocked_user = make_user()

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        emoji_group = make_reactions_emoji_group()
        emoji = make_emoji(group=emoji_group)
        blocked_user.react_to_post_with_id(post_id=post.pk, emoji_id=emoji.pk, emoji_group_id=emoji_group.pk)

        user.block_user_with_id(user_id=blocked_user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_reactions = json.loads(response.content)

        self.assertEqual(len(response_reactions), 0)

    def test_cannot_retrieve_reactions_from_blocking_user_in_a_community(self):
        """
         should not be able to retrieve the reactions from a blocking user in a community
         """
        user = make_user()

        post_creator = make_user()
        community = make_community(creator=post_creator)

        blocking_user = make_user()

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        emoji_group = make_reactions_emoji_group()
        emoji = make_emoji(group=emoji_group)
        blocking_user.react_to_post_with_id(post_id=post.pk, emoji_id=emoji.pk, emoji_group_id=emoji_group.pk)

        blocking_user.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_reactions = json.loads(response.content)

        self.assertEqual(len(response_reactions), 0)

    def test_can_retrieve_reactions_from_blocked_user_in_a_community_if_staff(self):
        """
         should be able to retrieve the reactions from a blocked user in a community if staff member
         """
        user = make_user()
        community = make_community(creator=user)
        post_creator = make_user()
        blocked_user = make_user()

        post_creator.join_community_with_name(community_name=community.name)

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        emoji_group = make_reactions_emoji_group()
        emoji = make_emoji(group=emoji_group)
        blocked_user.react_to_post_with_id(post_id=post.pk, emoji_id=emoji.pk, emoji_group_id=emoji_group.pk)

        user.block_user_with_id(user_id=blocked_user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_emoji_counts = json.loads(response.content)

        self.assertEqual(1, len(response_emoji_counts))

        response_emoji_count = response_emoji_counts[0]

        response_emoji_id = response_emoji_count.get('emoji').get('id')
        response_emoji_count = response_emoji_count.get('count')

        self.assertEqual(response_emoji_id, emoji.pk)
        self.assertEqual(1, response_emoji_count)

    def test_can_retrieve_reactions_from_blocking_user_in_a_community_if_staff(self):
        """
         should be able to retrieve the reactions from a blocking user in a community if staff member
         """
        user = make_user()
        community = make_community(creator=user)
        post_creator = make_user()
        blocking_user = make_user()

        post_creator.join_community_with_name(community_name=community.name)

        post = post_creator.create_community_post(text=make_fake_post_text(), community_name=community.name)

        emoji_group = make_reactions_emoji_group()
        emoji = make_emoji(group=emoji_group)
        blocking_user.react_to_post_with_id(post_id=post.pk, emoji_id=emoji.pk, emoji_group_id=emoji_group.pk)

        blocking_user.block_user_with_id(user_id=user.pk)

        url = self._get_url(post)

        headers = make_authentication_headers_for_user(user)
        response = self.client.get(url, **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_emoji_counts = json.loads(response.content)

        self.assertEqual(1, len(response_emoji_counts))

        response_emoji_count = response_emoji_counts[0]

        response_emoji_id = response_emoji_count.get('emoji').get('id')
        response_emoji_count = response_emoji_count.get('count')

        self.assertEqual(response_emoji_id, emoji.pk)
        self.assertEqual(1, response_emoji_count)

    def _get_url(self, post):
        return reverse('post-reactions-emoji-count', kwargs={
            'post_uuid': post.uuid
        })


class TestPostReactionEmojiGroups(APITestCase):
    """
    PostReactionEmojiGroups API
    """

    def test_can_retrieve_reactions_emoji_groups(self):
        """
         should be able to retrieve post reaction emoji groups
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        group_ids = []
        amount_of_groups = 4

        for x in range(amount_of_groups):
            group = make_emoji_group(is_reaction_group=True)
            group_ids.append(group.pk)

        url = self._get_url()
        response = self.client.get(url, **headers)
        self.assertTrue(response.status_code, status.HTTP_200_OK)

        response_groups = json.loads(response.content)
        response_groups_ids = [group['id'] for group in response_groups]

        self.assertEqual(len(response_groups), len(group_ids))

        for group_id in group_ids:
            self.assertIn(group_id, response_groups_ids)

    def test_cannot_retrieve_non_reactions_emoji_groups(self):
        """
         should not able to retrieve non post reaction emoji groups
        """
        user = make_user()
        headers = make_authentication_headers_for_user(user)

        group_ids = []
        amount_of_groups = 4

        for x in range(amount_of_groups):
            group = make_emoji_group(is_reaction_group=False)
            group_ids.append(group.pk)

        url = self._get_url()
        response = self.client.get(url, **headers)
        self.assertTrue(response.status_code, status.HTTP_200_OK)

        response_groups = json.loads(response.content)

        self.assertEqual(len(response_groups), 0)

    def _get_url(self):
        return reverse('posts-emoji-groups')


class PostCommentsEnableAPITests(APITestCase):
    """
    PostCommentsEnable APITests
    """

    def test_can_enable_comments_on_post_if_moderator_of_community(self):
        """
         should be able to enable comments if moderator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=user.username,
                                                                 community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(user)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertTrue(post.comments_enabled)
        self.assertTrue(parsed_response['comments_enabled'])

    def test_can_enable_comments_on_post_if_administrator_of_community(self):
        """
         should be able to enable comments if administrator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertTrue(post.comments_enabled)
        self.assertTrue(parsed_response['comments_enabled'])

    def test_logs_enabled_comments_on_post_by_administrator_of_community(self):
        """
         should log enable comments by administrator of a community
        """
        community_post_creator = make_user()
        admin = make_user()
        community = make_community(admin)

        community_post_creator.join_community_with_name(community_name=community.name)
        post = community_post_creator.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        self.client.post(url, **headers)

        self.assertTrue(community.logs.filter(action_type='EPC',
                                              post=post,
                                              source_user=admin,
                                              target_user=community_post_creator).exists())

    def test_cannot_enable_comments_on_post_if_not_administrator_or_moderator_of_community(self):
        """
         should not be able to enable comments if not administrator/moderator
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.comments_enabled = False
        post.save()

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(user)
        response = self.client.post(url, **headers)

        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertFalse(post.comments_enabled)

    def _get_url(self, post):
        return reverse('enable-post-comments', kwargs={
            'post_uuid': post.uuid
        })


class PostCommentsDisableAPITests(APITestCase):
    """
    PostCommentsDisable APITests
    """

    def test_can_disable_comments_on_post_if_moderator_of_community(self):
        """
         should be able to disable comments if moderator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=user.username,
                                                                 community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(user)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertFalse(post.comments_enabled)
        self.assertFalse(parsed_response['comments_enabled'])

    def test_can_disable_comments_on_post_if_administrator_of_community(self):
        """
         should be able to disable comments if administrator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertFalse(post.comments_enabled)
        self.assertFalse(parsed_response['comments_enabled'])

    def test_logs_disabled_comments_on_post_by_administrator_of_community(self):
        """
         should log disable comments by administrator of a community
        """
        community_post_creator = make_user()
        admin = make_user()
        community = make_community(admin)

        community_post_creator.join_community_with_name(community_name=community.name)
        post = community_post_creator.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        self.client.post(url, **headers)

        self.assertTrue(community.logs.filter(action_type='DPC',
                                              post=post,
                                              source_user=admin,
                                              target_user=community_post_creator).exists())

    def test_cannot_disable_comments_on_post_if_not_administrator_or_moderator_of_community(self):
        """
         should not be able to disable comments if not administrator/moderator
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(user)
        response = self.client.post(url, **headers)

        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertTrue(post.comments_enabled)

    def _get_url(self, post):
        return reverse('disable-post-comments', kwargs={
            'post_uuid': post.uuid
        })


class PostCloseAPITests(APITestCase):
    """
    PostCloseAPITests APITests
    """

    def test_can_close_post_if_administrator_of_community(self):
        """
         should be able to close post if administrator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertTrue(post.is_closed)
        self.assertTrue(parsed_response['is_closed'])

    def test_can_close_post_if_moderator_of_community(self):
        """
         should be able to close post if moderator of a community
        """
        user = make_user()
        admin = make_user()
        moderator = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        moderator.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=moderator.username,
                                                                 community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(moderator)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertTrue(post.is_closed)
        self.assertTrue(parsed_response['is_closed'])

    def test_cannot_close_post_if_not_administrator_or_moderator_of_community(self):
        """
         should not be able to close post if not moderator/administrator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(user)
        response = self.client.post(url, **headers)

        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertFalse(post.is_closed)

    def test_logs_close_post_by_administrator_of_community(self):
        """
         should log close post by administrator of a community
        """
        community_post_creator = make_user()
        admin = make_user()
        community = make_community(admin)

        community_post_creator.join_community_with_name(community_name=community.name)
        post = community_post_creator.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        self.client.post(url, **headers)

        self.assertTrue(community.logs.filter(action_type='CP',
                                              post=post,
                                              source_user=admin,
                                              target_user=community_post_creator).exists())

    def _get_url(self, post):
        return reverse('close-post', kwargs={
            'post_uuid': post.uuid
        })


class PostOpenAPITests(APITestCase):
    """
    PostOpenAPITests APITests
    """

    def test_can_open_post_if_administrator_of_community(self):
        """
         should be able to open post if administrator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.is_closed = True
        post.save()

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertFalse(post.is_closed)
        self.assertFalse(parsed_response['is_closed'])

    def test_can_open_post_if_moderator_of_community(self):
        """
         should be able to open post if moderator of a community
        """
        user = make_user()
        admin = make_user()
        moderator = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        moderator.join_community_with_name(community_name=community.name)
        admin.add_moderator_with_username_to_community_with_name(username=moderator.username,
                                                                 community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.is_closed = True
        post.save()

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(moderator)
        response = self.client.post(url, **headers)

        parsed_response = json.loads(response.content)

        self.assertTrue(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertFalse(post.is_closed)
        self.assertFalse(parsed_response['is_closed'])

    def test_cannot_open_post_if_not_administrator_or_moderator_of_community(self):
        """
         should not be able to open post if not moderator/administrator of a community
        """
        user = make_user()
        admin = make_user()
        community = make_community(admin)

        user.join_community_with_name(community_name=community.name)
        post = user.create_community_post(community.name, text=make_fake_post_text())
        post.is_closed = True
        post.save()

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(user)
        response = self.client.post(url, **headers)

        self.assertTrue(response.status_code, status.HTTP_400_BAD_REQUEST)
        post.refresh_from_db()
        self.assertTrue(post.is_closed)

    def test_logs_open_post_by_administrator_of_community(self):
        """
         should log open post by administrator of a community
        """
        community_post_creator = make_user()
        admin = make_user()
        community = make_community(admin)

        community_post_creator.join_community_with_name(community_name=community.name)
        post = community_post_creator.create_community_post(community.name, text=make_fake_post_text())

        url = self._get_url(post)
        headers = make_authentication_headers_for_user(admin)
        self.client.post(url, **headers)

        self.assertTrue(community.logs.filter(action_type='OP',
                                              post=post,
                                              source_user=admin,
                                              target_user=community_post_creator).exists())

    def _get_url(self, post):
        return reverse('open-post', kwargs={
            'post_uuid': post.uuid
        })
