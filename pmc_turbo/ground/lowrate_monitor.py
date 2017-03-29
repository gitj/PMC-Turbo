import bisect
import os
import glob
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)
import pmc_turbo.communication.short_status
from pmc_turbo.ground.ground_configuration import GroundConfiguration


class LowrateMonitor(GroundConfiguration):
    def __init__(self,max_initial_files=100,**kwargs):
        super(LowrateMonitor,self).__init__(**kwargs)
        self.gse_root_dir = self.find_latest_gse_dir()
        self.lowrate_data = OrderedDict()
        self.by_message_id = {}
        self.bad_files = set()
        self.update(max_initial_files)

    def find_latest_gse_dir(self):
        dirs = glob.glob(os.path.join(self.root_data_path,'2*'))
        dirs.sort()
        logger.debug("Found gse dir %s" % dirs[-1])
        return dirs[-1]

    @property
    def message_ids(self):
        return self.by_message_id.keys()

    def latest(self,message_id):
        latest =  self.lowrate_data[self.by_message_id[message_id][-1]]
        logger.debug("latest file for message id %d is %s" % (message_id, self.by_message_id[message_id][-1]))
        return latest

    def update(self, max_files=0):
        filenames = glob.glob(os.path.join(self.gse_root_dir,'*/lowrate/*'))
        filenames.sort()
        if max_files:
            skipped_files = filenames[:-max_files]
            self.lowrate_data.update(zip(skipped_files,[{} for _ in range(len(skipped_files))]))
            filenames = filenames[-max_files:]
        logger.debug("Found %d total filenames" % len(filenames))
        added = 0
        for filename in filenames[::-1]:
            if filename in self.lowrate_data:
                if added:
                    logger.info("added %d files" % added)
                return
            if filename in self.bad_files:
                continue
            try:
                values = pmc_turbo.communication.short_status.load_short_status_from_file(filename).values
            except Exception:
                logger.exception("Failed to open %s" % filename)
                self.bad_files.add(filename)
                continue
            message_id = values['message_id']
            current_list = self.by_message_id.get(message_id,[])
            bisect.insort(current_list,filename)
            self.by_message_id[message_id] = current_list
            self.lowrate_data[filename] = values
            added += 1
        if added:
            logger.info("added %d files" % added)