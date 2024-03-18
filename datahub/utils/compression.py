########################################################################################################################
# Compression Utilities
########################################################################################################################

import numpy
import struct
import logging

_logger = logging.getLogger(__name__)

class Endianness:
     LITTLE = "LITTLE_ENDIAN"
     BIG = "BIG_ENDIAN"

try:
    import bitshuffle
    import bitshuffle.h5
    bitshuffle_compression_filter =  bitshuffle.h5.H5FILTER
    bitshuffle_compression_lz4 = bitshuffle.h5.H5_COMPRESS_LZ4

except:
    _logger.error("bitshuffle not installed: BITSHUFFLE_LZ4 compression not supported")
    #itshuffle does not need to be present to dump compressed channels
    bitshuffle = None
    bitshuffle_compression_filter =32008
    bitshuffle_compression_lz4 = 2

class Compression:
    BITSHUFFLE_LZ4 = bitshuffle_compression_filter
    GZIP = "gzip"
    SZIP = "szip"
    LZF = "lzf"

def decompress(blob, name, compression, shape, dtype, border=Endianness.LITTLE):
    if bitshuffle is None:
        raise Exception("Bitshuffle not available")
    if compression == Compression.BITSHUFFLE_LZ4:
        c_length = struct.unpack(">q", blob[0:8])[0]
        b_size = struct.unpack(">i", blob[8:12])[0]
        nbuf = numpy.frombuffer(blob[12:], dtype=numpy.uint8)
        if dtype == "str":
            if len(shape) > 0:
                raise RuntimeError(f"Compression of arrays of strings not supported")
            #if c_length < 1 or c_length > 4 * 1024:
            #    raise RuntimeError(f"unexpected string size: {c_length}")
            #if b_size < 512 or b_size > 16 * 1024:
            #    raise RuntimeError(f"unexpected block size: {b_size}")
            dtype = numpy.dtype(numpy.int8) #numpy.dtype("b")
            value = bitshuffle.decompress_lz4(nbuf, shape=(c_length,), dtype=dtype, block_size=b_size)
            value = value.tobytes().decode()
        else:
            if len(shape) == 0:
                raise RuntimeError(f"Compression not supported on scalar numeric data {name}  shape {shape}  dtype {dtype}")
            #if c_length < 1 or c_length > 1 * 1024 * 1024:
            #    raise RuntimeError(f"unexpected value size: {c_length}")
            #if b_size < 512 or b_size > 16 * 1024:
            #    raise RuntimeError(f"unexpected block size: {b_size}")
            if type(dtype) == str:
                dtype = numpy.dtype(dtype).newbyteorder('<' if border == "LITTLE_ENDIAN" else ">")
            block_size = int(b_size / dtype.itemsize) #0
            value = bitshuffle.decompress_lz4(nbuf, shape=shape, dtype=dtype ,block_size=block_size)
    else:
        raise RuntimeError(f"Compression type {compression} is not supported.")
    return value

