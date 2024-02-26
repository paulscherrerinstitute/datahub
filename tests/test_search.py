import unittest
from datahub import *

class RetrivalTest(unittest.TestCase):
    def setUp(self):
        self.retrieval = Retrieval()
        #self.databuffer = DataBuffer(url="https://data-api.psi.ch/sf")
        self.databuffer = DataBuffer()

    def tearDown(self):
        self.retrieval.close()
        self.databuffer.close()


    def test_search_retrieval(self):
        self.retrieval.search("SARFE10-PSSS059")


    def test_search_databuffer(self):
        self.databuffer.print_search("SARFE10-PSSS059")

if __name__ == '__main__':
    unittest.main()
