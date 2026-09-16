"""Tests for the small CI/CD exercise API."""

import unittest

from fastapi.testclient import TestClient

from big_data_example import __version__
from big_data_example.api import app


class ApiTest(unittest.TestCase):
    client = TestClient(app)

    def test_home_describes_the_application(self) -> None:
        response = self.client.get("/")

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "application": "BigDataExample",
                "version": __version__,
            },
            response.json(),
        )

    def test_health_reports_healthy(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "healthy"}, response.json())


if __name__ == "__main__":
    unittest.main()
