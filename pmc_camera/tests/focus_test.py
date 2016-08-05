import os
import sys
import time
import numpy as np
import pmc_camera

if __name__=="__main__":
    bc = pmc_camera.Birger()
    pc = pmc_camera.PyCamera(num_buffers=2)

    bc.aperture_full_open()
    bc.focus_infinity()
    bc.move_focus(-40)
    pc.set_exposure_counts(10000)

    output_dir = '/data1/2016-08-04'
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    for focus_step in range(60):
        print focus_step,
        sys.stdout.flush()
        d = pc.get_image()
        d = pc.get_image()
        state = bc.state_dict
        state['time'] = time.time()
        state['exposure_counts'] = pc.exposure_counts
        fn = 'exposure_%d_focus_step_%04d.npz' % (pc.exposure_counts,focus_step)
        np.savez(os.path.join(output_dir,fn),image=d, state=state)
        bc.move_focus(-1)