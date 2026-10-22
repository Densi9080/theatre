# main/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from .models import (
    Actor, Genre, Show, Hall, Session,
    UserProfile, Ticket, News,
)


# ============================================================
#                  ХЕЛПЕР ДЛЯ БЫСТРОЙ НАСТРОЙКИ
# ============================================================

class BaseSetUpMixin:
    def _create_base(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.profile = UserProfile.objects.create(
            user=self.user,
            passport_number=123456,
            passport_series=1234,
            full_name="Тест Тестов",
            birth_date="1990-01-01",
        )
        self.hall = Hall.objects.create(name="Зал 1", rows=5, seats_per_row=5)
        self.genre = Genre.objects.create(genre_name="Драма", description="Описание")
        self.actor = Actor.objects.create(name="Актёр Тестов")
        self.show = Show.objects.create(
            title="Тестовое шоу",
            description="Описание шоу",
            duration=120,
            poster="shows/test.jpg",
            available=True,
        )
        self.show.genre.add(self.genre)
        self.show.actor.add(self.actor)
        self.session = Session.objects.create(
            date=timezone.now(),
            show=self.show,
            hall=self.hall,
            hall_rows=5,
            hall_seats=5,
        )


# ============================================================
#                       ТЕСТЫ МОДЕЛЕЙ
# ============================================================

class ActorModelTest(TestCase):
    def test_create_actor(self):
        actor = Actor.objects.create(name="Иван Иванов", bio="Био")
        self.assertEqual(actor.name, "Иван Иванов")
        self.assertEqual(Actor.objects.count(), 1)


class GenreModelTest(TestCase):
    def test_create_genre(self):
        genre = Genre.objects.create(genre_name="Комедия", description="Смешно")
        self.assertEqual(genre.genre_name, "Комедия")


class ShowModelTest(BaseSetUpMixin, TestCase):
    def setUp(self):
        self._create_base()

    def test_show_fields(self):
        self.assertEqual(self.show.title, "Тестовое шоу")
        self.assertTrue(self.show.available)
        self.assertEqual(self.show.duration, 120)

    def test_show_m2m(self):
        self.assertEqual(self.show.genre.count(), 1)
        self.assertEqual(self.show.actor.count(), 1)


class HallSessionModelTest(BaseSetUpMixin, TestCase):
    def setUp(self):
        self._create_base()

    def test_hall(self):
        self.assertEqual(self.hall.rows, 5)
        self.assertEqual(self.hall.seats_per_row, 5)

    def test_session(self):
        self.assertEqual(self.session.show, self.show)
        self.assertEqual(self.session.hall, self.hall)


class TicketModelTest(BaseSetUpMixin, TestCase):
    def setUp(self):
        self._create_base()

    def test_create_ticket(self):
        ticket = Ticket.objects.create(
            row=1, seat=1, status=True, price=500,
            session=self.session, user=self.profile,
        )
        self.assertEqual(ticket.price, 500)
        self.assertTrue(ticket.status)
        self.assertEqual(ticket.session, self.session)


class UserProfileModelTest(TestCase):
    def test_default_role(self):
        user = User.objects.create_user(username="u2", password="pass")
        profile = UserProfile.objects.create(
            user=user,
            passport_number=1,
            passport_series=2,
            full_name="Имя",
            birth_date="2000-01-01",
        )
        self.assertEqual(profile.role, "user")


# ============================================================
#                       ТЕСТЫ API: SHOWS
# ============================================================

class ShowAPITest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()

    def test_list_shows(self):
        response = self.client.get("/api/shows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_filter_by_genre(self):
        response = self.client.get(f"/api/shows/?genre={self.genre.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_shows(self):
        response = self.client.get("/api/shows/?search=Тестовое")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_show_sessions_action(self):
        response = self.client.get(f"/api/shows/{self.show.id}/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


# ============================================================
#                       ТЕСТЫ API: NEWS
# ============================================================

class NewsAPITest(APITestCase):
    def setUp(self):
        self.news = News.objects.create(description="Новость", news_image="news/1.jpg")

    def test_list_news(self):
        response = self.client.get("/api/news/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_news_ordered_desc(self):
        News.objects.create(description="Новость 2", news_image="news/2.jpg")
        response = self.client.get("/api/news/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # первая должна быть самая свежая
        self.assertEqual(response.data[0]["description"], "Новость 2")


# ============================================================
#                       ТЕСТЫ API: SESSIONS
# ============================================================

class SessionAPITest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()

    def test_list_sessions(self):
        response = self.client.get("/api/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_show(self):
        response = self.client.get(f"/api/sessions/?show={self.show.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_seats_schema(self):
        response = self.client.get(f"/api/sessions/{self.session.id}/seats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("seats_matrix", response.data)
        self.assertEqual(response.data["rows"], 5)
        self.assertEqual(response.data["seats_per_row"], 5)
        # 5 строк по 5 мест
        self.assertEqual(len(response.data["seats_matrix"]), 5)
        self.assertEqual(len(response.data["seats_matrix"][0]), 5)


# ============================================================
#                       ТЕСТЫ API: AUTH
# ============================================================

class LoginLogoutAPITest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()

    def test_login_success(self):
        response = self.client.post("/api/users/login/", {
            "username": "testuser",
            "password": "testpass123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data["user"]["username"], "testuser")

    def test_login_fail(self):
        response = self.client.post("/api/users/login/", {
            "username": "testuser",
            "password": "wrong",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data.get("success"))

    def test_login_returns_role(self):
        response = self.client.post("/api/users/login/", {
            "username": "testuser",
            "password": "testpass123",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["role"], "user")

    def test_logout(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/users/logout/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MyProfileAPITest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()
        self.client.force_authenticate(user=self.user)

    def test_my_profile_authenticated(self):
        response = self.client.get("/api/users/my/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")
        self.assertTrue(response.data["is_authenticated"])


class RegisterAPITest(APITestCase):
    def test_register_success(self):
        response = self.client.post("/api/auth/register/", {
            "username": "newuser",
            "password": "newpass123",
            "email": "new@test.com",
            "full_name": "Новый Пользователь",
            "birth_date": "2000-01-01",
            "passport_series": 1234,
            "passport_number": 567890,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertTrue(UserProfile.objects.filter(user__username="newuser").exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username="dup", password="pass")
        response = self.client.post("/api/auth/register/", {
            "username": "dup",
            "password": "newpass123",
            "full_name": "Дубликат",
            "birth_date": "2000-01-01",
            "passport_series": 1234,
            "passport_number": 567890,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
#                       ТЕСТЫ API: TICKETS
# ============================================================

class TicketAPITest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()
        self.client.force_authenticate(user=self.user)

    def test_list_tickets(self):
        response = self.client.get("/api/tickets/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buy_ticket_success(self):
        response = self.client.post("/api/tickets/", {
            "session": self.session.id,
            "row": 1,
            "seat": 1,
            "price": 500,
            "user": self.profile.id,
        }, format="json")
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, status.HTTP_201_CREATED,
        ])
        self.assertTrue(
            Ticket.objects.filter(session=self.session, row=1, seat=1).exists()
        )

    def test_buy_occupied_seat(self):
        Ticket.objects.create(
            row=1, seat=1, status=True, price=500,
            session=self.session, user=self.profile,
        )
        response = self.client.post("/api/tickets/", {
            "session": self.session.id,
            "row": 1,
            "seat": 1,
            "price": 500,
            "user": self.profile.id,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_available_seat(self):
        response = self.client.get(
            f"/api/tickets/available/?session={self.session.id}&row=2&seat=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["available"])

    def test_unavailable_seat(self):
        Ticket.objects.create(
            row=2, seat=2, status=True, price=500,
            session=self.session, user=self.profile,
        )
        response = self.client.get(
            f"/api/tickets/available/?session={self.session.id}&row=2&seat=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["available"])

    def test_export_returns_xlsx(self):
        Ticket.objects.create(
            row=1, seat=1, status=True, price=500,
            session=self.session, user=self.profile,
        )
        response = self.client.get("/api/tickets/export/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("spreadsheetml", response["Content-Type"])


# ============================================================
#               ТЕСТЫ ПРАВ ДОСТУПА (READ_ONLY PERMISSION)
# ============================================================

class ReadOnlyPermissionTest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()

    def test_anonymous_can_list_shows(self):
        response = self.client.get("/api/shows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_create_show(self):
        response = self.client.post("/api/shows/", {
            "title": "Новое шоу",
            "description": "desc",
            "duration": 90,
            "available": True,
        }, format="json")
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_anonymous_can_list_actors(self):
        response = self.client.get("/api/actors/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================
#                       ТЕСТЫ API: GENRES / ACTORS
# ============================================================

class GenreAPITest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()

    def test_list_genres(self):
        response = self.client.get("/api/genres/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


class ActorAPITest(BaseSetUpMixin, APITestCase):
    def setUp(self):
        self._create_base()

    def test_list_actors(self):
        response = self.client.get("/api/actors/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)