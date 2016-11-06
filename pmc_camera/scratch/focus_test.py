import os
import sys
import time
import numpy as np
import pmc_camera

if __name__=="__main__":
    pc = pmc_camera.PyCamera()


    output_dir = '/data4/2016-10-12_135mm_focus_test_100_ms_dusk_no_sim_sky'
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
#    start_at = time.mktime((2016,8,8,4,0,0,0,0,1))
    #start_at = time.time()
    start_at = time.mktime((2016,10,13,05,00,0,0,0,1))
    print ""
    while time.time() < start_at:
        print ("\rWaiting to start at %s, in %.2f hours" % (time.ctime(start_at),((start_at-time.time())/3600.))),
        sys.stdout.flush()
        time.sleep(60)
    start = time.time()
    max_focus = pc.get_focus_max()
    pc.set_exposure_milliseconds(100)
    while (time.time() - start) < 9*3600:
        #pc.simple_exposure_adjust(verbose=True,max=10000)
        #pc.set_focus(4690)
        # For 50 mm
        #pc.set_focus(2025)
        # For 135 mm
        for focus_step in range(1975, 2011):
            pc.set_focus(focus_step)
#            print focus_step,
            sys.stdout.flush()
            try:
                state,d = pc.get_image_with_info()
            except RuntimeError, e:
                print e
                continue
            state.update(dict(focus_step=focus_step,max_focus=max_focus))
            state['time'] = time.time()
            state['exposure_milliseconds'] = 100.
            timestamp = time.strftime('%Y-%m-%d_%H%M%S')
            fn = '%s_focus_step_%04d.npz' % (timestamp,focus_step)
            np.savez(os.path.join(output_dir,fn),
                     image=d,
                     state=state)
            #pc.set_focus(4690+focus_step)
