"""Default backend test suite entrypoint for `manage.py test`."""

from unittest import TestLoader, TestSuite


TEST_MODULES = [
    'apps.auth.tests',
    'apps.users.tests',
    'apps.projects.tests',
]


def load_tests(loader: TestLoader, standard_tests, pattern):
    suite = TestSuite()
    for module in TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(module))
    return suite
