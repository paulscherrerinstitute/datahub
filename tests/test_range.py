import unittest
from datahub import *


class RangeTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_range(self):
        query = {}
        query["start"] = "2024-01-29 11:48:00Z"
        query["end"] = "2024-01-29 12:48:00.050Z"
        now = time.time()

        # print (now)

        tr = QueryRange(query)
        t = time.time()
        print(t)

        id = tr.time_to_id(t)
        print(id)

        tm = tr.id_to_time(id)
        print(tm)

        self.assertLess(abs(tm - t), PULSE_ID_INTERVAL)

        print(tr.seconds_to_string(tm, False))

        print(tr.seconds_to_string(now, False))

        """
        def time_to_id(self, time=datetime.now()):
            start_pulse_id = datetime(2017, 9, 4, 11, 11, 18)
            millis = int((now - start_pulse_id).total_seconds() * 1000)
            pid = millis // 10
            return pid
        """
        """
        #print(tr.time_to_id())
        s1=tr.seconds_to_string(now, True)
        s2=tr.seconds_to_string(now, False)
        print (s1)
        print (s2)

        s1 = tr.string_to_seconds(s1)
        s2 = tr.string_to_seconds(s2)
        print (s1)
        print (s2)

        print (tr.get_start())
        print (tr.get_end())
        print (tr.get_start_str())
        print (tr.get_end_str())

        """



if __name__ == '__main__':
    unittest.main()

