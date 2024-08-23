import logging
import h5py
import numpy
import datetime
import threading
from datahub import Consumer, Compression, bitshuffle_compression_lz4, decompress

_logger = logging.getLogger(__name__)

class HDF5Writer(Consumer):

    def __init__(self, filename: str, default_compression=Compression.GZIP, auto_decompress=False, path=None, metadata_compression=Compression.GZIP, **kwargs):
        Consumer.__init__(self, **kwargs)
        self.nbytes_read = 0
        self.filename = filename
        self.default_compression = default_compression
        self.auto_decompress = auto_decompress
        self.metadata_compression = metadata_compression
        self.in_channel = False
        self.path = ""
        self.file = None
        if path:
            if not path.startswith("/"):
                path = "/" + path
            self.path = path
        self.datasets = {}
        self.lock = threading.Lock()

    def on_start(self, source):
        with self.lock:
            if self.file is None:
                self.file = h5py.File(self.filename, "w")
                now_date = datetime.datetime.now(datetime.timezone.utc)
                self.file.attrs["creation"] = now_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def on_stop(self, source, exception):
        pass

    def get_path(self, source):
        if self.path and not source.path:
            return self.path
        return f"{source.get_path()}"


    def get_group(self, source, channel):
        prefix = self.get_path(source)
        for i in range(1000):
            if i==0:
               name = channel
            else:
               name = f"{channel}_{i}"
            group = f"{prefix}/{name}"
            if not group in self.file:
                break
        return name

    def _get_time_fmt(self, source):
        if source.time_type == "str":
            return "str"
        elif source.time_type == "sec":
            return numpy.float64
        else:
            return numpy.int64

    def on_channel_header(self, source, name, typ, byteOrder, shape, channel_compression, metadata):
        prefix, channel = self.get_path(source), self.get_group(source, name)
        has_id = metadata.get("has_id", True)
        ts_ds = Dataset(prefix, channel, "timestamp", self.file, dtype=self._get_time_fmt(source), dataset_compression=self.metadata_compression)
        id_ds = Dataset(prefix, channel, "id", self.file, dtype=numpy.int64, dataset_compression=self.metadata_compression) if has_id else None
        data_ds_name = "value"
        if channel_compression and (not self.auto_decompress):
            if shape is None or (len(shape) == 0):
                raise RuntimeError(f"Compression not supported on scalars")
            if channel_compression != Compression.BITSHUFFLE_LZ4:
                raise RuntimeError(f"Compression not supported: " + channel_compression)
            val_ds = DirectChunkWriteDataset(prefix, channel, data_ds_name, self.file,shape, typ, channel_compression, dataset_compression=Compression.BITSHUFFLE_LZ4)
        else:
            val_ds = Dataset(prefix, channel, data_ds_name, self.file, shape, typ, channel_compression, dataset_compression=self.default_compression)
            if metadata.get("bins", None):
                min_ds = Dataset(prefix,  channel, "min", self.file, shape, typ, channel_compression, dataset_compression=self.default_compression)
                max_ds = Dataset(prefix, channel, "max", self.file, shape, typ, channel_compression,dataset_compression=self.default_compression)
                cnt_ds = Dataset(prefix, channel, "count", self.file, dtype=numpy.int64, dataset_compression=self.metadata_compression)
                start_ds = Dataset(prefix, channel, "start", self.file, dtype=self._get_time_fmt(source),dataset_compression=self.metadata_compression)
                end_ds = Dataset(prefix, channel, "end", self.file, dtype=self._get_time_fmt(source),dataset_compression=self.metadata_compression)
                val_ds = val_ds, min_ds, max_ds, cnt_ds, start_ds, end_ds

        if not self.datasets.get(source, None):
            self.datasets[source] = {}
            self.file[f"{prefix}"].attrs["type"] = str(source.type)
            self.file[f"{prefix}"].attrs["backend"] = str(source.backend)
            self.file[f"{prefix}"].attrs["url"] = str(source.url)
            self.file[f"{prefix}"].attrs["query_index"] = str(source.query_index)
            self.file[f"{prefix}"].attrs["name"] = str(source.get_name())
            for key in source.query.keys():
                self.file[f"{prefix}"].attrs[key] = str(source.query[key])
        self.datasets[source][name] = [ts_ds, id_ds, val_ds]
        self.file[f"{prefix}/{channel}"].attrs["name"] = str(name)
        self.file[f"{prefix}/{channel}"].attrs["type"] = str(type)
        self.file[f"{prefix}/{channel}"].attrs["byteOrder"] = str(byteOrder)
        self.file[f"{prefix}/{channel}"].attrs["shape"] = str(shape)
        self.file[f"{prefix}/{channel}"].attrs["compression"] = str(channel_compression)
        for key in metadata.keys():
            self.file[f"{prefix}/{channel}"].attrs[key] = metadata[key]

    def on_channel_record(self, source, name, timestamp, pulse_id, value, **kwargs):
        [ts_ds, id_ds, val_ds] = self.datasets[source][name]
        if ts_ds:
            ts_ds.append(timestamp)
        if id_ds:
            id_ds.append(pulse_id)
        if kwargs.get("bins", None):
            val_ds, min_ds, max_ds, cnt_ds, start_ds, end_ds = val_ds
            min_ds.append(kwargs.get("min"))
            max_ds.append(kwargs.get("max"))
            cnt_ds.append(kwargs.get("count"))
            start_ds.append(kwargs.get("start"))
            end_ds.append(kwargs.get("end"))
        val_ds.append(value)

    def on_channel_completed(self, source, name):
        self.close_datasets(source, name)

    def close_datasets(self, source=None, name=None):
        if source is None:
            for source in list(self.datasets.keys()):
                self.close_datasets(source, None)
            return
        if name is None:
            for name in list(self.datasets[source].keys()):
                self.close_datasets(source, name)
            return
        for dataset in self.datasets[source].get(name, []):
            try:
                if dataset is not None:
                    if type(dataset) is tuple:
                        for d in dataset:
                            d.close()
                    else:
                        dataset.close()
            except Exception as ex:
                _logger.exception("Error closing datasets of channel %s: %s " % (name, str(ex)))

        self.datasets[source].pop(name, None)

    def on_close(self):
        self.close_datasets()
        try:
            if self.file:
                now_date = datetime.datetime.now(datetime.timezone.utc)
                self.file.attrs["conclusion"] = now_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                self.file.close()
        except Exception as ex:
            _logger.exception("Error closing file: %s " % str(self.file_name))
        self.file = None




class Dataset:
    STRING_TYPE = h5py.string_dtype()
    def __init__(self, prefix, channel, field, h5file, shape=None, dtype=None, channel_compression=None, chunks=None, dataset_compression=Compression.GZIP, compression_opts=None, shuffle=True):
        self.channel_compression = channel_compression
        self.dataset_compression = dataset_compression
        self.compression_opts=compression_opts
        self.channel = channel
        self.h5file = h5file
        if shape is None:
            shape = tuple()
        shape = tuple(shape)
        self.shape = shape

        if dtype is None:
            dtype = int
        elif dtype == "str":
            dtype = str
        self.is_value = type(dtype) is type
        if dtype == str:
            self.dtype = Dataset.STRING_TYPE
        else:
            self.dtype = numpy.dtype(dtype)

        if chunks is None:
            if len(shape) == 0:
                if self.is_string():
                    chunks = (1 * 1024,)
                else:
                    chunks = (8 * 1024,)
            elif len(shape) == 1:
                if self.is_string():
                    n = 1 * 1024 // shape[0]
                else:
                    n = 16 * 1024 // shape[0]
                if n < 2:
                    n = 2
                chunks = (n,) + shape
            elif len(shape) == 2:
                n = 32 * 1024 // shape[0] // shape[1]
                if n < 2:
                    n = 2
                chunks = (n,) + shape
            else:
                raise RuntimeError(f"unsupported shape {shape}")

        self.chunks = None if (chunks is None) else tuple(chunks)
        self.dataset = self.h5file.create_dataset(f"{prefix}/{channel}/{field}", (0,) + self. shape, maxshape=(None,) + self.shape, dtype=self.dtype , chunks=self.chunks, shuffle=shuffle, compression=self.dataset_compression , compression_opts=self.compression_opts)
        self.buf = numpy.zeros(shape=self.chunks, dtype=self.dtype)
        self.nbuf = 0
        self.nwritten = 0

    def append(self, v):
        if self.channel_compression:
            v = decompress(v, self.channel, self.channel_compression, self.shape, self.dtype)
        else:
            if not self.is_value:
                v = numpy.reshape(numpy.frombuffer(v, dtype=self.dtype), self.shape)
        if self.nbuf >= len(self.buf):
            self.flush()
        self.buf[self.nbuf] = v
        self.nbuf += 1

    def flush(self):
        nn = self.nwritten + self.nbuf
        self.dataset.resize((nn,) + self.shape)
        self.dataset[self.nwritten:nn] = self.buf[:self.nbuf]
        self.nwritten = nn
        self.nbuf = 0

    def close(self):
        self.flush()

    def is_string(self):
        return self.dtype == Dataset.STRING_TYPE


class StringDataset(Dataset):
    def __init__(self, prefix, channel, field, h5file, channel_compression, dataset_compression):
        dtype = str
        shape = tuple()
        chunks = (1 * 1024)
        Dataset.__init__(self, prefix, channel, field, h5file, shape, dtype, channel_compression, chunks, dataset_compression=dataset_compression)

class DirectChunkWriteDataset(Dataset):

    def __init__(self, prefix, channel, field, h5file, shape, dtype, channel_compression, dataset_compression):
        shape = tuple(shape)
        chunks = (1,) + shape
        block_size = 0
        compression_opts = (block_size, bitshuffle_compression_lz4)
        shuffle = False
        Dataset.__init__(self, prefix, channel, field, h5file, shape, dtype, channel_compression, chunks, dataset_compression, compression_opts, shuffle)

    def append(self, buf):
        nr = self.nwritten + 1
        self.dataset.resize((nr,)+self.shape)
        #k = struct.unpack(">qi", buf[:12])
        #uncompressed_size = k[0]
        #block_size = k[1]
        #self.compression_opts = (block_size, bitshuffle.h5.H5_COMPRESS_LZ4)
        off = (self.nwritten,) + (0,) * len(self.shape)
        self.dataset.id.write_direct_chunk(off, buf)
        self.nwritten += 1

    def flush(self):
        pass

