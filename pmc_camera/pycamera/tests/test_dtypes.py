from ..dtypes import chunk_dtype

def test_chunk_dtype():
    assert(chunk_dtype.itemsize==48)