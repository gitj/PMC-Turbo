import os
import sys
import time
import numpy as np
import pmc_camera

if __name__=="__main__":
    pc = pmc_camera.PyCamera()


    output_dir = '/data1/2016-09-24_50mm_star_focus_test_100ms'
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
#    start_at = time.mktime((2016,8,8,4,0,0,0,0,1))
    start_at = time.time()
    print ""
    while time.time() < start_at:
        print ("\rWaiting to start at %s, in %.2f hours" % (time.ctime(start_at),((start_at-time.time())/3600.))),
        sys.stdout.flush()
        time.sleep(60)
    start = time.time()
    max_focus = pc.get_focus_max()
    while (time.time() - start) < 7*3600:
        #pc.simple_exposure_adjust(verbose=True,max=10000)
        pc.set_exposure_milliseconds(100)
        pc.set_focus(max_focus-153)
        for focus_step in range(20):
            print focus_step,
            sys.stdout.flush()
            state,d = pc.get_image_with_info()
            state.update(dict(focus_step=focus_step,max_focus=max_focus))
            state['time'] = time.time()
            state['exposure_milliseconds'] = 100.
            timestamp = time.strftime('%Y-%m-%d_%H%M%S')
            fn = '%s_focus_step_%04d.npz' % (timestamp,focus_step)
            np.savez(os.path.join(output_dir,fn),
                     image=d,
                     state=state)
            pc.set_focus(max_focus-153-focus_step)
