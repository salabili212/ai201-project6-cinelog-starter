"""
tests/test_watchlist.py — CineLog

Tests for the watchlist service.
"""

import uuid

import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.watchlist_service import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    AlreadyInWatchlistError,
    NotInWatchlistError,
)
from services.collection_service import FilmNotFoundError


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """A user to use in tests."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in tests."""
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id


def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    """
    Adding a film_id that doesn't exist in the database should raise
    FilmNotFoundError, not a database integrity error.
    """
    with app.app_context():
        fake_film_id = str(uuid.uuid4())

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)


def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    """Adding the same film twice raises AlreadyInWatchlistError (Comment 2)."""
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(user_id=sample_user, film_id=sample_film)

        entries = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).all()
        assert len(entries) == 1


def test_add_to_watchlist_defaults_to_private(app, sample_user, sample_film):
    """Comment 4: entries are private unless the caller opts in."""
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film)
        assert entry.public is False


def test_add_to_watchlist_accepts_explicit_public_flag(app, sample_user, sample_film):
    """The public parameter lets callers opt in to sharing at add time."""
    with app.app_context():
        entry = add_to_watchlist(
            user_id=sample_user, film_id=sample_film, public=True
        )
        assert entry.public is True


def test_get_watchlist_empty_returns_empty_list(app, sample_user):
    """
    Edge case: a user with nothing saved must get back an empty list, not None.

    Chosen because an empty watchlist is the state every brand-new user is in,
    and because `jsonify(None)` and `jsonify([])` are different responses to a
    client — returning None here would break the endpoint for exactly the users
    least likely to have a workaround.
    """
    with app.app_context():
        result = get_watchlist(sample_user)
        assert result == []


def test_get_watchlist_returns_saved_films_newest_first(app, sample_user):
    """Comment 5: the default sort is date_added, newest first."""
    with app.app_context():
        first = Film(title="Arrival", year=2016)
        second = Film(title="Blade Runner 2049", year=2017)
        db.session.add_all([first, second])
        db.session.commit()

        add_to_watchlist(user_id=sample_user, film_id=first.id)
        add_to_watchlist(user_id=sample_user, film_id=second.id)

        result = get_watchlist(sample_user)
        assert [f["title"] for f in result] == ["Blade Runner 2049", "Arrival"]


def test_get_watchlist_sort_by_title(app, sample_user):
    """Comment 5: ?sort=title returns the same films ordered A-Z."""
    with app.app_context():
        first = Film(title="Zodiac", year=2007)
        second = Film(title="Amelie", year=2001)
        db.session.add_all([first, second])
        db.session.commit()

        add_to_watchlist(user_id=sample_user, film_id=first.id)
        add_to_watchlist(user_id=sample_user, film_id=second.id)

        result = get_watchlist(sample_user, sort_by="title")
        assert [f["title"] for f in result] == ["Amelie", "Zodiac"]


def test_remove_from_watchlist_removes_entry(app, sample_user, sample_film):
    """remove_from_watchlist deletes the entry and reports success."""
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)

        assert remove_from_watchlist(
            user_id=sample_user, film_id=sample_film
        ) is True
        assert get_watchlist(sample_user) == []


def test_remove_from_watchlist_missing_entry_raises(app, sample_user, sample_film):
    """
    Removing a film that was never saved raises NotInWatchlistError, mirroring
    remove_from_collection's NotInCollectionError.
    """
    with app.app_context():
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(user_id=sample_user, film_id=sample_film)
