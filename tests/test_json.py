import unittest
from datahub.main import run_json


json_str = '{' \
           '"file": "/Users/gobbo_a/dev/back/json.h5", ' \
           '"print": true, ' \
           '"epics": {"url": null, "query":{"start":null, "end":3.0, "channels": ["TESTIOC:TESTCALCOUT:Input", "TESTIOC:TESTSINUS:SinCalc", "TESTIOC:TESTWF2:MyWF"]}},' \
           '"bsread": {"url": "tcp://localhost:9999", "mode":"PULL", "query":{"start":null, "end":3.0, "channels":  ["UInt8Scalar", "Float32Scalar"]}}' \
           '}'

json_str = '{' \
           '"file": "/Users/gobbo_a/dev/back/json.h5", ' \
           '"print": true, ' \
           '"start": null, ' \
           '"end": 3.0, ' \
           '"epics": {"channels": ["TESTIOC:TESTCALCOUT:Input", "TESTIOC:TESTSINUS:SinCalc", "TESTIOC:TESTWF2:MyWF"]},' \
           '"bsread": {"url": "tcp://localhost:9999", "mode":"PULL", "channels":  ["UInt8Scalar", "Float32Scalar"]}' \
           '}'

class EpicsTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_json(self):
        run_json(json_str)


if __name__ == '__main__':
    unittest.main()
