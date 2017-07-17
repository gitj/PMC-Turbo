from ..dtypes import chunk_dtype, decode_aperture_chunk_data,decode_lens_status_chunk_data


def test_chunk_dtype():
    assert (chunk_dtype.itemsize == 56)

def test_decode_aperture():
    assert decode_aperture_chunk_data(24) == 2.0

def test_decode_lens_status():
    for k in range(64):
        decode_lens_status_chunk_data(k)

    result = decode_lens_status_chunk_data(24)
    assert not result['error']
    assert result['lens_attached']
    assert result['auto_focus']
    assert result['last_error'] == 0