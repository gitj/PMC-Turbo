def setup_simple_supergroup():
    import housekeeping_classes
    # For use during testing
    ccpath = '/home/pmc/pmchome/pmc-turbo/status_item_params/charge_controller_register_items.json'
    cpath = '/home/pmc/pmchome/pmc-turbo/status_item_params/camera_items.json'
    return housekeeping_classes.construct_super_group_from_json_list([cpath, ccpath])


class KeyRing():
    def __init__(self, dict_):
        self.key_dict = {}
        self.dict = dict_

    def add_key_to_keyring(self, item_name):

        if item_name in self.key_dict:
            raise ValueError('Item name %s is already in keyring' % item_name)
        for group_key in self.dict.keys():
            group = self.dict[group_key]
            for filewatcher_key in group.keys():
                filewatcher = group[filewatcher_key]
                if item_name in filewatcher.keys():
                    self.key_dict[item_name] = (group_key, filewatcher_key)
                    return self.key_dict
        raise ValueError('Item name %s not found in supergroup %s' % (item_name, self.dict.name))

    def create_keyring(self, status_items, supergroup_status_output):
        keyring = {}
        for status_item in status_items:
            keyring = self.add_key_to_keyring(status_item)
        return keyring

    def create_keyring_from_dict(self, dict_, prev_keys=()):
        '''

        Parameters
        ----------
        dict_ - dictionary to be scanned
        prev_keys - tuple of higher level keys - used for recursive call

        -------

        '''
        # Recursively find all the end keys, throw them into keyring dict.
        # TODO: I will actually need to stop this one level short due to the formatting of the items.
        for key in dict_.keys():
            if isinstance(dict_[key], dict):
                new_prev_keys = prev_keys + (key,)
                self.create_keyring_from_dict(dict_, new_prev_keys)
            else:
                self.key_dict[key] = prev_keys

    def get_keyring_item(self, item_name):
        group_key, filewatcher_key = self.key_dict[item_name]
        return self.dict[group_key][filewatcher_key][item_name]
