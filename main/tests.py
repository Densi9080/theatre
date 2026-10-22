# main/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Actor, Genre, Show, Hall, Session,
    UserProfile, Ticket, News,
)
from .factories import (
    UserFactory, UserProfileFactory, ActorFactory, GenreFactory,
    ShowFactory, HallFactory, SessionFactory, TicketFactory, NewsFactory,
)


# ============================================================
#                       ТЕСТЫ МОДЕЛЕЙ
# ============================================================

class ActorModelTest(TestCase):
    def test_create_actor(self):
        actor = ActorFactory(name="Иван Иванов")
        self.assertEqual(actor.name, "Иван Иванов")
        self.assertEqual(Actor.objects.count(), 1)

    def test_actor_factory_generates(self):
        ActorFactory.create_batch(3)
        self.assertEqual(Actor.objects.count(), 3)


class GenreModelTest(TestCase):
    def test_create_genre(self):
        genre = GenreFactory(genre_name="Комедия")
        self.assertEqual(genre.genre_name, "Комедия")


class ShowModelTest(TestCase):
    def setUp(self):
        self.show = ShowFactory()
        # ShowFactory через post_generation создаёт 1 жанр и 1 актёра
        self.assertEqual(self.show.genre.count(), 1)
        self.assertEqual(self.show.actor.count(), 1)

    def test_show_fields(self):
        self.assertTrue(self.show.available)
        self.assertGreaterEqual(self.show.duration, 60)
        self.assertLessEqual(self.show.duration, 180)

    def test_show_custom_m2m(self):
        g1, g2 = GenreFactory(), GenreFactory()
        a1 = ActorFactory()
        show = ShowFactory(genre=[g1, g2], actor=[a1])
        self.assertEqual(show.genre.count(), 2)
        self.assertEqual(show.actor.count(), 1)


class HallSessionModelTest(TestCase):
    def test_hall(self):
        hall = HallFactory(rows=10, seats_per_row=20)
        self.assertEqual(hall.rows, 10)
        self.assertEqual(hall.seats_per_row, 20)

    def test_session_inherits_hall_sizes(self):
        hall = HallFactory(rows=8, seats_per_row=12)
        session = SessionFactory(hall=hall)
        self.assertEqual(session.hall_rows, 8)
        self.assertEqual(session.hall_seats, 12)


class TicketModelTest(TestCase):
    def test_create_ticket(self):
        ticket = TicketFactory(price=500)
        self.assertEqual(ticket.price, 500)
        self.assertTrue(ticket.status)
        self.assertIsNotNone(ticket.session)
        self.assertIsNotNone(ticket.user)


class UserProfileModelTest(TestCase):
    def test_default_role(self):
        profile = UserProfileFactory(role="user")
        self.assertEqual(profile.role, "user")
        self.assertIsNotNone(profile.user)
        # пароль установлен фабрикой
        self.assertTrue(profile.user.check_password("testpass123"))


# ============================================================
#                       ТЕСТЫ API: SHOWS
# ============================================================

class ShowAPITest(APITestCase):
    def setUp(self):
        self.genre = GenreFactory()
        self.show = ShowFactory(title="Тестовое шоу", genre=[self.genre])
        self.session = SessionFactory(show=self.show, hall=HallFactory())

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
    def test_list_news(self):
        NewsFactory()
        response = self.client.get("/api/news/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_news_ordered_desc(self):
        NewsFactory(description="Старая")
        NewsFactory(description="Новая")
        response = self.client.get("/api/news/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["description"], "Новая")


# ============================================================
#                       ТЕСТЫ API: SESSIONS
# ============================================================

class SessionAPITest(APITestCase):
    def setUp(self):
        self.hall = HallFactory(rows=5, seats_per_row=5)
        self.session = SessionFactory(hall=self.hall, hall_rows=5, hall_seats=5)

    def test_list_sessions(self):
        response = self.client.get("/api/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_show(self):
        response = self.client.get(f"/api/sessions/?show={self.session.show.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_seats_schema(self):
        response = self.client.get(f"/api/sessions/{self.session.id}/seats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("seats_matrix", response.data)
        self.assertEqual(response.data["rows"], 5)
        self.assertEqual(response.data["seats_per_row"], 5)
        self.assertEqual(len(response.data["seats_matrix"]), 5)
        self.assertEqual(len(response.data["seats_matrix"][0]), 5)

    def test_seats_matrix_marks_occupied(self):
        TicketFactory(session=self.session, row=1, seat=1, status=True)
        response = self.client.get(f"/api/sessions/{self.session.id}/seats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first_seat = response.data["seats_matrix"][0][0]
        self.assertTrue(first_seat["occupied"])
        self.assertFalse(first_seat["available"])


# ============================================================
#                       ТЕСТЫ API: AUTH
# ============================================================

class LoginLogoutAPITest(APITestCase):
    def setUp(self):
        self.user = UserFactory(username="testuser", password=None)
        self.user.set_password("testpass123")
        self.user.save()
        self.profile = UserProfileFactory(user=self.user, role="user")

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


class MyProfileAPITest(APITestCase):
    def setUp(self):
        self.profile = UserProfileFactory()
        self.client.force_authenticate(user=self.profile.user)

    def test_my_profile_authenticated(self):
        response = self.client.get("/api/users/my/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.profile.user.username)
        self.assertTrue(response.data["is_authenticated"])


class RegisterAPITest(APITestCase):
    def _payload(self, username="newuser"):
        return {
            "username": username,
            "password": "newpass123",
            "email": f"{username}@test.com",
            "full_name": "Новый Пользователь",
            "birth_date": "2000-01-01",
            "passport_series": 1234,
            "passport_number": 567890,
        }

    def test_register_success(self):
        response = self.client.post("/api/auth/register/", self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertTrue(UserProfile.objects.filter(user__username="newuser").exists())

    def test_register_duplicate_username(self):
        UserFactory(username="dup", password=None)
        response = self.client.post("/api/auth/register/", self._payload("dup"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
#                       ТЕСТЫ API: TICKETS
# ============================================================

class TicketAPITest(APITestCase):
    def setUp(self):
        self.profile = UserProfileFactory()
        self.session = SessionFactory(
            hall=HallFactory(rows=5, seats_per_row=5),
            hall_rows=5, hall_seats=5,
        )
        self.client.force_authenticate(user=self.profile.user)

    def _buy_payload(self, row=1, seat=1, price=500):
        return {
            "session": self.session.id,
            "row": row,
            "seat": seat,
            "price": price,
            "user": self.profile.id,
        }

    def test_list_tickets(self):
        TicketFactory(session=self.session, user=self.profile)
        response = self.client.get("/api/tickets/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_buy_ticket_success(self):
        response = self.client.post("/api/tickets/", self._buy_payload(), format="json")
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, status.HTTP_201_CREATED,
        ])
        self.assertTrue(
            Ticket.objects.filter(session=self.session, row=1, seat=1).exists()
        )

    def test_buy_occupied_seat(self):
        TicketFactory(session=self.session, row=1, seat=1, status=True)
        response = self.client.post("/api/tickets/", self._buy_payload(row=1, seat=1), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_available_seat(self):
        response = self.client.get(
            f"/api/tickets/available/?session={self.session.id}&row=2&seat=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["available"])

    def test_unavailable_seat(self):
        TicketFactory(session=self.session, row=2, seat=2, status=True)
        response = self.client.get(
            f"/api/tickets/available/?session={self.session.id}&row=2&seat=2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["available"])

    def test_export_returns_xlsx(self):
        TicketFactory(session=self.session, user=self.profile)
        response = self.client.get("/api/tickets/export/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("spreadsheetml", response["Content-Type"])


# ============================================================
#               ТЕСТЫ ПРАВ ДОСТУПА
# ============================================================

class ReadOnlyPermissionTest(APITestCase):
    def setUp(self):
        self.show = ShowFactory()

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
        ActorFactory()
        response = self.client.get("/api/actors/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================
#                       ТЕСТЫ API: GENRES / ACTORS
# ============================================================

class GenreAPITest(APITestCase):
    def test_list_genres(self):
        GenreFactory.create_batch(3)
        response = self.client.get("/api/genres/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)


class ActorAPITest(APITestCase):
    def test_list_actors(self):
        ActorFactory.create_batch(2)
        response = self.client.get("/api/actors/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)