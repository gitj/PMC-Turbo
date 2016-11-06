import numpy as np

frame_info_dtype = np.dtype([('frame_id',np.uint64),('timestamp',np.uint64),
                             ('frame_status',np.uint32), ('is_filled', np.uint32)])