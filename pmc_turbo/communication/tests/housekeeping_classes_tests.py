import tempfile
import unittest

from pmc_turbo.communication import housekeeping_classes


class StatusDictTest(unittest.TestCase):
    def test_item(self):
        item_value_dict = dict(name='test_item', column_name='value',
                               normal_range_low=0, normal_range_high=1,
                               good_range_low=1, good_range_high=2,
                               warning_range_low=2, warning_range_high=3, scaling_value=1)

        item = housekeeping_classes.FloatStatusItem(item_value_dict)
        value_dict = {'epoch': 1000, 'value': 0.5}
        item.update_value(value_dict)
        assert (item.get_status_summary() == housekeeping_classes.NOMINAL)
        value_dict = {'epoch': 1000, 'value': 1.5}
        item.update_value(value_dict)
        assert (item.get_status_summary() == housekeeping_classes.GOOD)
        value_dict = {'epoch': 1000, 'value': 2.5}
        item.update_value(value_dict)
        assert (item.get_status_summary() == housekeeping_classes.WARNING)

    def test_filewatcher(self):
        tfile = tempfile.NamedTemporaryFile()

        with open(tfile.name, 'w') as f:
            f.write('epoch,data0,data1\n')
            f.write('1000,1,5\n')

        value_dict_0 = dict(name='data0', column_name='data0',
                            normal_range_low=0, normal_range_high=1,
                            good_range_low=1, good_range_high=2,
                            warning_range_low=2, warning_range_high=3, scaling_value=1)

        item0 = housekeeping_classes.FloatStatusItem(value_dict_0)

        value_dict_1 = dict(name='data1', column_name='data1',
                            normal_range_low=0, normal_range_high=1,
                            good_range_low=1, good_range_high=2,
                            warning_range_low=2, warning_range_high=3, scaling_value=1)
        item1 = housekeeping_classes.FloatStatusItem(value_dict_1)
        items = [item0, item1]
        filewatcher = housekeeping_classes.StatusFileWatcher(name='test_filewatcher', items=items,
                                                             filename_glob=tfile.name)
        filewatcher.update()

        print item0.value

        print filewatcher.get_status_summary()
        assert (item0.value == 1)
        assert (item1.value == 5)
        assert (filewatcher.get_status_summary() == (housekeeping_classes.CRITICAL, ['data1']))

    def test_status_group(self):
        tfile0 = tempfile.NamedTemporaryFile()
        tfile1 = tempfile.NamedTemporaryFile()

        with open(tfile0.name, 'w') as f:
            f.write('epoch,data0,data1\n')
            f.write('1000,1,5\n')

        with open(tfile1.name, 'w') as f:
            f.write('epoch,data2,data3\n')
            f.write('1000,5,5\n')

        value_dict_0 = dict(name='data0', column_name='data0',
                            normal_range_low=0, normal_range_high=1,
                            good_range_low=1, good_range_high=2,
                            warning_range_low=2, warning_range_high=3, scaling_value=1)
        item0 = housekeeping_classes.FloatStatusItem(value_dict_0)

        value_dict_1 = dict(name='data1', column_name='data1',
                            normal_range_low=0, normal_range_high=1,
                            good_range_low=1, good_range_high=2,
                            warning_range_low=2, warning_range_high=3, scaling_value=1)
        item1 = housekeeping_classes.FloatStatusItem(value_dict_1)
        items0 = [item0, item1]
        filewatcher0 = housekeeping_classes.StatusFileWatcher(name='test_filewatcher0', items=items0,
                                                              filename_glob=tfile0.name)

        value_dict_2 = dict(name='data2', column_name='data2',
                            normal_range_low=0, normal_range_high=1,
                            good_range_low=1, good_range_high=2,
                            warning_range_low=2, warning_range_high=3, scaling_value=1)
        item2 = housekeeping_classes.FloatStatusItem(value_dict_2)
        value_dict_3 = dict(name='data3', column_name='data3',
                            normal_range_low=0, normal_range_high=1,
                            good_range_low=1, good_range_high=2,
                            warning_range_low=2, warning_range_high=3, scaling_value=1)
        item3 = housekeeping_classes.FloatStatusItem(value_dict_3)
        items1 = [item2, item3]
        filewatcher1 = housekeeping_classes.StatusFileWatcher(name='test_filewatcher1', items=items1,
                                                              filename_glob=tfile1.name)

        status_group = housekeeping_classes.StatusGroup('test_group', [filewatcher0, filewatcher1])
        status_group.update()

        print status_group.get_status_summary()
        assert (status_group.get_status_summary() == (housekeeping_classes.CRITICAL, ['data1', 'data3', 'data2']))
        # Error here - I don't want the order to matter
        # assert (status_group.get_status_summary() == (status_dict.CRITICAL, ['data1', 'data2', 'data3']))
