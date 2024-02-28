from datahub import *
import unittest
from datahub import *

class EpicsTest(unittest.TestCase):

    def test_databuffer(self):
        query = {
            "channels": ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"],
            "start": "2024-02-14 08:50:00.000",
            "end": "2024-02-14 08:50:05.000"
        }

        with DataBuffer(backend="sf-databuffer") as source:
            table = Table()
            source.add_listener(table)
            source.request(query)
            dataframe = table.as_dataframe(Table.PULSE_ID)
            print(dataframe)

    def test_epics(self):
        query = {
            "channels": ["TESTIOC:TESTCALCOUT:Input", "TESTIOC:TESTSINUS:SinCalc"],
            "start": "0.0",
            "end": "2.0",
        }
        with Epics(url="localhost:54321", time_type="str") as source:
            table = Table()
            source.add_listener(table)
            source.request(query)
            dataframe = table.as_dataframe(Table.TIMESTAMP)
            print(dataframe)
