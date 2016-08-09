import os
import sys
import time
import numpy as np
import pmc_camera

if __name__=="__main__":
    bc = pmc_camera.Birger()
    pc = pmc_camera.PyCamera(num_buffers=2)

    bc.aperture_full_open()

    output_dir = '/data1/2016-08-08_morning_with_ND_filter'
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    start_at = time.mktime((2016,8,8,4,0,0,0,0,1))
    start_at = time.time()
    print ""
    while time.time() < start_at:
        print ("\rWaiting to start at %s, in %.2f hours" % (time.ctime(start_at),((start_at-time.time())/3600.))),
        sys.stdout.flush()
        time.sleep(60)
    start = time.time()
    while (time.time() - start) < 2.5*3600:
        pc.simple_exposure_adjust(verbose=True,max=10000)
        #pc.set_exposure_counts(10000)
        bc.focus_infinity()
        bc.move_focus(-60)
        for focus_step in range(20):
            print focus_step,
            sys.stdout.flush()
            d = pc.get_image()
            d = pc.get_image()
            d = pc.get_image()
            state = bc.state_dict
            state['time'] = time.time()
            state['exposure_counts'] = pc.exposure_counts
            timestamp = time.strftime('%Y-%m-%d_%H%M%S')
            fn = '%s_focus_step_%04d.npz' % (timestamp,focus_step)
            np.savez(os.path.join(output_dir,fn),image=d,
                     state=state)
            bc.move_focus(-1)