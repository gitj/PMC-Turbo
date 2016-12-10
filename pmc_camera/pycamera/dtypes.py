import numpy as np

image_dimensions = (3232,4864)

frame_info_dtype = np.dtype([('frame_id',np.uint64),('timestamp',np.uint64),
                             ('frame_status',np.uint32), ('is_filled', np.uint32)])

chunk_dtype = np.dtype([('image_chunk_identifier','<u4'),  # NB: This is part of the GigEVision chunk header, so order
                        ('image_chunk_length','<u4'),     # is little endian instead of big endian
                        ('acquisition_count', '>u4'),
                        ('lens_status_focus','>u2'),
                        ('lens_aperture','u1'),
                        ('lens_focal_length','u1'),
                        ('exposure_us','>u4'),
                        ('gain_db','>u4'),
                        ('sync_in','>u2'),
                        ('sync_out','>u2'),
                        ('reserved_1','>u4'),
                        ('reserved_2','>u4'),
                        ('reserved_3','>u4'),
                        ('reserved_4','>u4'),
                        ('reserved_5','>u4'),
                        ('chunk_identifier','<u4'),  # NB: This is part of the GigEVision chunk header, so order
                        ('chunk_length','<u4')])     # is little endian instead of big endian

chunk_num_bytes = chunk_dtype.itemsize
