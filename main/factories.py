# main/factories.py
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Actor, Genre, Show, Hall, Session,
    UserProfile, Ticket, News,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    passport_series = factory.Sequence(lambda n: 1000 + n)
    passport_number = factory.Sequence(lambda n: 100000 + n)
    full_name = factory.Faker("name", locale="ru_RU")
    birth_date = factory.Faker("date_of_birth", minimum_age=18, maximum_age=70)
    role = "user"


class ActorFactory(DjangoModelFactory):
    class Meta:
        model = Actor

    name = factory.Faker("name", locale="ru_RU")
    bio = factory.Faker("text", max_nb_chars=200, locale="ru_RU")
    photo = None  # ImageField оставляем пустым в тестах


class GenreFactory(DjangoModelFactory):
    class Meta:
        model = Genre

    genre_name = factory.Sequence(lambda n: f"Жанр {n}")
    description = factory.Faker("sentence", locale="ru_RU")


class ShowFactory(DjangoModelFactory):
    class Meta:
        model = Show

    title = factory.Sequence(lambda n: f"Спектакль {n}")
    description = factory.Faker("paragraph", locale="ru_RU")
    duration = factory.Faker("random_int", min=60, max=180)
    poster = "shows/test.jpg"
    available = True

    @factory.post_generation
    def genre(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for g in extracted:
                self.genre.add(g)
        else:
            self.genre.add(GenreFactory())

    @factory.post_generation
    def actor(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for a in extracted:
                self.actor.add(a)
        else:
            self.actor.add(ActorFactory())


class HallFactory(DjangoModelFactory):
    class Meta:
        model = Hall

    name = factory.Sequence(lambda n: f"Зал {n}")
    rows = 5
    seats_per_row = 5


class SessionFactory(DjangoModelFactory):
    class Meta:
        model = Session

    date = factory.LazyFunction(timezone.now)
    show = factory.SubFactory(ShowFactory)
    hall = factory.SubFactory(HallFactory)
    hall_rows = factory.LazyAttribute(lambda o: o.hall.rows)
    hall_seats = factory.LazyAttribute(lambda o: o.hall.seats_per_row)


class TicketFactory(DjangoModelFactory):
    class Meta:
        model = Ticket

    row = factory.Sequence(lambda n: (n % 5) + 1)
    seat = factory.Sequence(lambda n: (n % 5) + 1)
    status = True
    price = factory.Faker("random_int", min=100, max=2000)
    session = factory.SubFactory(SessionFactory)
    user = factory.SubFactory(UserProfileFactory)


class NewsFactory(DjangoModelFactory):
    class Meta:
        model = News

    description = factory.Faker("paragraph", locale="ru_RU")
    news_image = "news/test.jpg"