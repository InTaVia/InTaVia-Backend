import unittest
import json
from intavia_backend.models_v2 import InTaViaModelBaseClass


class TestInTaViaBaseClass(unittest.TestCase):
    def setUp(self) -> None:
        with open("intavia_backend/tests/test_data.json") as f:
            self.test_data = json.load(f)
        with open("intavia_backend/tests/test_data_events.json") as f:
            self.test_data_events = json.load(f)
        return super().setUp()

    def test_filter_sparql(self):
        res = InTaViaModelBaseClass().filter_sparql(self.test_data["results"], anchor="person")
        self.assertEqual(len(res), 2)

    def test_filter_sparql_no_values_selected(self):
        res = InTaViaModelBaseClass().filter_sparql(self.test_data["results"], anchor="person", list_of_keys=None)
        for ent in res:
            self.assertFalse("_additional_values" in ent)

    def test_filter_sparql_values_selected(self):
        res = InTaViaModelBaseClass().filter_sparql(
            self.test_data["results"], anchor="person", list_of_keys=["person", "entityLabel"]
        )
        for ent in res:
            self.assertTrue("_additional_values" in ent)

    def test_complex_example(self):
        res = InTaViaModelBaseClass().filter_sparql(
            self.test_data_events["results"], anchor="person", list_of_keys=["person", "entityLabel"]
        )
        res2 = InTaViaModelBaseClass().filter_sparql(
            res[0]["_additional_values"], anchor="event", list_of_keys=["event", "eventLabel", "start"]
        )
        self.assertEqual(len(res2), 14)
