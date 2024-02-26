from datahub import *

query = {
    "channels": ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"],
    "start": "2024-02-14 08:50:00.000",
    "end": "2024-02-14 08:50:05.000"
}

with DataBuffer(backend="sf-databuffer") as source:
    stdout = StdoutWriter()
    table = Table()
    source.add_listener(table)
    source.request(query)
    dataframe = table.as_dataframe(Table.PULSE_ID)
    print(dataframe)
