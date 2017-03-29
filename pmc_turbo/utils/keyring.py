def setup_simple_supergroup():
    from pmc_turbo.communication import housekeeping_classes
    # For use during testing
    ccpath = '/home/pmc/pmchome/pmc-turbo/status_item_params/charge_controller_register_items.json'
    cpath = '/home/pmc/pmchome/pmc-turbo/status_item_params/camera_items.json'
    collectdpath = '/home/pmc/pmchome/pmc-turbo/status_item_params/collectd_items.json'
    return housekeeping_classes.construct_super_group_from_json_list([cpath, ccpath, collectdpath])


class KeyRing():
    '''
    Simple util to find 1 level above last keys in dict and give the path to those items.
    Can be used to find all items in a
    '''
    def __init__(self, dict_):
        self.key_dict = {}
        self.dict = dict_
        self.create_keyring_from_dict(self.dict, prev_keys=())

    def create_keyring_from_dict(self, dict_, prev_keys=()):
        for key in dict_.keys():
            # print key
            dict_value = dict_[key]
            if isinstance(dict_value, dict):

                if isinstance(dict_value.values()[0], dict):

                    new_prev_keys = prev_keys + (key,)
                    self.create_keyring_from_dict(dict_value, new_prev_keys)
                else:
                    if key in self.key_dict.keys():
                        raise ValueError('Key %r already in key_dict.keys' % key)
                    else:
                        self.key_dict[key] = prev_keys

    def __getitem__(self, item):
        # group_key, filewatcher_key = self.key_dict[item]
        # return self.dict[group_key][filewatcher_key][item]
        keys = self.key_dict.get(item, None)

        if keys is None:
            return {'value': float('nan')} # TODO: Think of a good null item to put here.

        # Start off first key
        i = 0
        result = self.dict[keys[0]]

        # Go through rest of keys
        while i < len(keys) - 1:
            i += 1
            result = result[keys[i]]

        # Items is the final key.
        return result[item]

    def keys(self):
        return self.key_dict.keys()
