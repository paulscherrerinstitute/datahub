import unittest
from datahub import *


class TimingTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_pulse_id(self):
        t1 = time.time()
        id = time_to_pulse_id(t1)
        t2 = pulse_id_to_time(id)
        print (t1-t2)
        self.assertLess(abs(t1-t2), PULSE_ID_INTERVAL)

    def test_performance(self):
            # Comparimg performance for multiplying  by 100 and dividing by 0.01
            import timeit
            time_multiply_int = timeit.timeit('result = x * 100', setup='x = 1.23456789', number=1000000)
            time_multiply = timeit.timeit('result = x * 100.0', setup='x = 1.23456789', number=1000000)
            time_divide = timeit.timeit('result = x / 0.01', setup='x = 1.23456789', number=1000000)
            print(f'Time taken for int multiplication: {time_multiply_int:.6f} seconds')
            print(f'Time taken for multiplication: {time_multiply:.6f} seconds')
            print(f'Time taken for division: {time_divide:.6f} seconds')

if __name__ == '__main__':
    unittest.main()
