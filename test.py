import pytest
import responses
from flask import Flask
from flask_testing import TestCase
from redis import Redis
import json
from main import app, connect_to_redis
from model import error_detection, receiving_data, get_data

MOCK_USER_DATA = {
    "results": [
        {
            "gender": "male",
            "name": {"title": "Mr", "first": "John", "last": "Doe"},
            "email": "john.doe@example.com",
            "phone": "123-456-7890",
            "cell": "987-654-3210",
            "location": {
                "street": {"number": 123, "name": "Main St"},
                "city": "Springfield",
                "state": "IL",
                "country": "USA",
                "postcode": "62701",
                "coordinates": {"latitude": "39.7817", "longitude": "-89.6501"}
            },
            "picture": {"large": "http://example.com/large.jpg", "thumbnail": "http://example.com/thumb.jpg"},
            "dob": {"date": "1980-01-01", "age": 45},
            "registered": {"date": "2010-01-01", "age": 15},
            "nat": "US"
        }
    ]
}

class BaseTestCase(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        return app

    def setUp(self):
        self.redis = connect_to_redis()
        self.redis.flushdb()
        self.client = self.app.test_client()

    def tearDown(self):
        self.redis.flushdb()

class TestModelFunctions(BaseTestCase):
    def test_error_detection_valid(self):
        assert error_detection("5") is False
        assert error_detection("100") is False

    def test_error_detection_invalid(self):
        assert error_detection("abc") is True
        assert error_detection("") is True
        assert error_detection("0") is True
        assert error_detection("-5") is True

    @responses.activate
    def test_receiving_data(self):
        responses.add(
            responses.GET,
            'https://randomuser.me/api/?results=5',
            json={"results": [MOCK_USER_DATA["results"][0]] * 5},
            status=200
        )
        data, number_rows = receiving_data(5, self.redis)
        assert len(data) == 5
        assert number_rows == 5
        assert self.redis.get("1") is not None
        assert json.loads(self.redis.get("1")) == MOCK_USER_DATA["results"][0]

    @responses.activate
    def test_receiving_data_capped(self):
        responses.add(
            responses.GET,
            'https://randomuser.me/api/?results=20',
            json={"results": [MOCK_USER_DATA["results"][0]] * 20},
            status=200
        )
        data, number_rows = receiving_data(20, self.redis)
        assert len(data) == 20
        assert number_rows == 15
        assert self.redis.get("1") is not None
        assert self.redis.get("20") is not None

    def test_get_data_less_than_15(self):
        for i in range(1, 10):
            self.redis.set(f"{i}", json.dumps(MOCK_USER_DATA["results"][0]))
        data = get_data(self.redis)
        assert len(data) == 9
        assert data[0] == MOCK_USER_DATA["results"][0]

    def test_get_data_more_than_15(self):
        for i in range(1, 20):
            self.redis.set(f"{i}", json.dumps(MOCK_USER_DATA["results"][0]))
        data = get_data(self.redis)
        assert len(data) == 15
        assert data[0] == MOCK_USER_DATA["results"][0]

class TestFlaskRoutes(BaseTestCase):
    def test_main_handler_get(self):
        for i in range(1, 5):
            self.redis.set(f"{i}", json.dumps(MOCK_USER_DATA["results"][0]))
        response = self.client.get('/')
        assert response.status_code == 200
        assert b"john.doe@example.com" in response.data
        assert b"Springfield" in response.data

    @responses.activate
    def test_main_handler_post_valid(self):
        responses.add(
            responses.GET,
            'https://randomuser.me/api/?results=3',
            json={"results": [MOCK_USER_DATA["results"][0]] * 3},
            status=200
        )
        response = self.client.post('/', data={'number': '3'})
        assert response.status_code == 200
        assert b"john.doe@example.com" in response.data
        assert self.redis.get("1") is not None
        assert self.redis.get("3") is not None

    def test_main_handler_post_invalid(self):
        response = self.client.post('/', data={'number': 'abc'})
        assert response.status_code == 200
        assert "Введите количество требуемых пользователей".encode('utf-8') in response.data

    def test_user_handler_valid(self):
        self.redis.set("1", json.dumps(MOCK_USER_DATA["results"][0]))
        response = self.client.get('/1')
        assert response.status_code == 200
        assert b"John Doe" in response.data
        assert b"Springfield" in response.data
        assert b"123-456-7890" in response.data

    def test_user_handler_invalid(self):
        self.redis.set("1", json.dumps(MOCK_USER_DATA["results"][0]))
        response = self.client.get('/2')
        assert response.status_code == 404

    def test_random_handler(self):
        self.redis.set("1", json.dumps(MOCK_USER_DATA["results"][0]))
        response = self.client.get('/random')
        assert response.status_code == 200
        assert b"John Doe" in response.data
        assert b"Springfield" in response.data

if __name__ == '__main__':
    pytest.main(["-v", __file__])