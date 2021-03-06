# -*- coding: utf-8 -*-

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse 
from django.contrib.auth.models import User
from django_ulogin import views
from django_ulogin.models import ULoginUser
from django_ulogin.signals import assign

def response(update=None):
    """
    Emulates JSON response from ulogin serivce for test purposes
    """
    data = {
        'network'    : 'vkontakte',
        'identity'   : 'http://vk.com/id12345',
        'uid'        : '12345',
        'email'      : 'demo@demo.de',
        'first_name' : 'John',
        'last_name'  : 'Doe',
        'bdate'      : '01.01.1970',
        'sex'        : '2',
        'photo'      : 'http://www.google.ru/images/srpr/logo3w.png',
        'photo_big'  : 'http://www.google.ru/images/srpr/logo3w.png',
        'city'       : 'Washington',
        'country'    : 'United States',
    }
    if update:
        data.update(update)
    return data

class Test(test.TestCase):
    """
    """
    urls = 'django_ulogin.tests.urls'

    def setUp(self):
        self.client = test.Client()
        self.url = reverse('ulogin_postback')
        views.ulogin_response = lambda token, host: response(None)

    def test_has_error(self):
        """
        Tests if in response there is key 'error', in context it there is
        too
        """
        views.ulogin_response = lambda token, host: response({'error': 'Token expired'})
        resp = self.client.post(self.url, data={'token': '31337'})

        self.assertEquals(200, resp.status_code)
        self.assertTrue('json' in resp.context)
        self.assertTrue('error' in resp.context['json'])

    def test_405_if_not_post(self):
        """
        Tests if a request is made with a non-POST method, the response
        code is 405 (Method not allowed)
        """
        resp = self.client.get(self.url)
        self.assertEquals(405, resp.status_code)

    def test_400_if_no_token_given(self):
        """
        Tests if no token given the response code is 400 (Bad Request)
        """
        resp = self.client.post(self.url)
        self.assertEquals(400, resp.status_code)

    def test_302_if_post_and_token_given(self):
        """
        Test if input date is correct, redirect will be appeared
        """
        resp = self.client.post(self.url, data={'token': '31337'})
        self.assertEquals(302, resp.status_code)

    def test_user_is_created(self):
        """
        Test that user is created
        """
        self.assertEquals(0, User.objects.count())
        self.assertEquals(0, ULoginUser.objects.count())

        resp = self.client.post(self.url, data={'token': '31337'})

        self.assertEquals(1, User.objects.count())
        self.assertEquals(1, ULoginUser.objects.count())


    def test_assign_user(self):
        """
        Test if user is authenticated new user will not be created, but
        current user will be assigned with ulogin
        """
        username, password = 'demo', 'demo'
        user = User.objects.create_user(username=username,
                                   password=password,
                                   email='demo@demo.de')

        self.assertEquals(1, User.objects.count())
        self.assertEquals(0, ULoginUser.objects.count())

        self.client.login(username=username, password=password)
        self.client.post(self.url, data={'token': '31337'})

        self.assertEquals(1, User.objects.count())
        self.assertEquals(1, ULoginUser.objects.count())

    def test_no_duplicates_when_post_twise(self):
        """
        Test no duplicate ULoginUser creates when identity already
        exists
        """
        self.assertEquals(0, User.objects.count())
        self.assertEquals(0, ULoginUser.objects.count())
        
        self.client.post(self.url, data={'token': '31337'})
        self.client.post(self.url, data={'token': '31337'})

        self.assertEquals(1, User.objects.count())
        self.assertEquals(1, ULoginUser.objects.count())
        
    def test_user_logged(self):
        resp = self.client.post(self.url, data={'token': 31331},follow=True)

        self.assertEquals(200, resp.status_code)
        self.assertTrue( resp.context['request'].user.is_authenticated() )


    def test_user_authenticated_ulogin_not_exists(self):
        """
        Tests received from view data when user is authenticated but
        ulogin not exists
        """
        username, password = 'demo', 'demo'
        user = User.objects.create_user(username=username,
                                   password=password,
                                   email='demo@demo.de')
        def handler(**kwargs):
            self.assertTrue( kwargs['registered'] )

        assign.connect(receiver=handler, sender=ULoginUser,
                       dispatch_uid='test')

        self.client.login(username=username, password=password)
        self.client.post(self.url, data={'token': '31337'})

    def test_user_authenticated_ulogin_exists(self):
        """
        Tests received from view data when user is authenticated and
        ulogin exists too
        """
        username, password = 'demo', 'demo'
        user = User.objects.create_user(username=username,
                                   password=password,
                                   email='demo@demo.de')
        def handler(**kwargs):
            self.assertFalse( kwargs['registered'] )

        assign.connect(receiver=handler, sender=ULoginUser,
                       dispatch_uid='test')

        ULoginUser.objects.create(user=user, network=response()['network'],
                                         uid=response()['uid'])
        self.client.login(username=username, password=password)
        self.client.post(self.url, data={'token': '31337'})
       
    def test_user_not_authenticated_ulogin_exists(self):
        """
        Tests received from view data when user is not authenticated and
        ulogin exists
        """
        def handler(**kwargs):
            ''
            self.assertFalse( kwargs['registered'] )

        username, password = 'demo', 'demo'
        user = User.objects.create_user(username=username,
                                   password=password,
                                   email='demo@demo.de')
        ULoginUser.objects.create(user=user, network=response()['network'],
                                         uid=response()['uid'])

        assign.connect(receiver=handler, sender=ULoginUser,
                       dispatch_uid='test')
        self.client.post(self.url, data={'token': '31337'})

    def test_user_not_authenticated_ulogin_not_exists(self):
        """
        Tests received from view data when user is not authenticated and
        ulogin not exists 
        """
        username, password = 'demo', 'demo'
        user = User.objects.create_user(username=username,
                                   password=password,
                                   email='demo@demo.de')

        def handler(**kwargs):
            ''
            self.assertTrue( kwargs['registered'] )

        assign.connect(receiver=handler, sender=ULoginUser,
                       dispatch_uid='test')
        self.client.post(self.url, data={'token': '31337'})