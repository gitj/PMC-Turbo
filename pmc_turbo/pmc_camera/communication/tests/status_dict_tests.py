import tempfile
import unittest

from pmc_turbo.pmc_camera.communication import housekeeping_classes


class StatusDictTest(unittest.TestCase):
    def test_item(self):
        item = housekeeping_classes.FloatStatusItem(name='test_item', column_name='value',
                                                    nominal_range=housekeeping_classes.Range(0, 1),
                                                    good_range=housekeeping_classes.Range(1, 2), warning_range=housekeeping_classes.Range(2, 3))
        value_dict = {'epoch': 1000, 'value':0.5}
        item.update_value(value_dict)
        assert (item.get_status_summary() == housekeeping_classes.NOMINAL)
        value_dict = {'epoch': 1000, 'value':1.5}
        item.update_value(value_dict)
        assert (item.get_status_summary() == housekeeping_classes.GOOD)
        value_dict = {'epoch': 1000, 'value':2.5}
        item.update_value(value_dict)
        assert (item.get_status_summary() == housekeeping_classes.WARNING)

    def test_filewatcher(self):
        tfile = tempfile.NamedTemporaryFile()

        with open(tfile.name, 'w') as f:
            f.write('epoch,data0,data1\n')
            f.write('1000,1,5\n')

        item0 = housekeeping_classes.FloatStatusItem(name='data0', column_name='data0', nominal_range=housekeeping_classes.Range(0, 1),
                                                     good_range=housekeeping_classes.Range(1, 2), warning_range=housekeeping_classes.Range(2, 3))
        item1 = housekeeping_classes.FloatStatusItem(name='data1', column_name='data1', nominal_range=housekeeping_classes.Range(0, 1),
                                                     good_range=housekeeping_classes.Range(1, 2), warning_range=housekeeping_classes.Range(2, 3))
        items = [item0, item1]
        filewatcher = housekeeping_classes.StatusFileWatcher(name='test_filewatcher', items=items, filename_glob=tfile.name)
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

        item0 = housekeeping_classes.FloatStatusItem(name='data0', column_name='data0', nominal_range=housekeeping_classes.Range(0, 1),
                                                     good_range=housekeeping_classes.Range(1, 2), warning_range=housekeeping_classes.Range(2, 3))
        item1 = housekeeping_classes.FloatStatusItem(name='data1', column_name='data1', nominal_range=housekeeping_classes.Range(0, 1),
                                                     good_range=housekeeping_classes.Range(1, 2), warning_range=housekeeping_classes.Range(2, 3))
        items0 = [item0, item1]
        filewatcher0 = housekeeping_classes.StatusFileWatcher(name='test_filewatcher0', items=items0, filename_glob=tfile0.name)

        item2 = housekeeping_classes.FloatStatusItem(name='data2', column_name='data2', nominal_range=housekeeping_classes.Range(0, 1),
                                                     good_range=housekeeping_classes.Range(1, 2), warning_range=housekeeping_classes.Range(2, 3))
        item3 = housekeeping_classes.FloatStatusItem(name='data3', column_name='data3', nominal_range=housekeeping_classes.Range(0, 1),
                                                     good_range=housekeeping_classes.Range(1, 2), warning_range=housekeeping_classes.Range(2, 3))
        items1 = [item2, item3]
        filewatcher1 = housekeeping_classes.StatusFileWatcher(name='test_filewatcher1', items=items1, filename_glob=tfile1.name)

        status_group = housekeeping_classes.StatusGroup('test_group', [filewatcher0, filewatcher1])
        status_group.update()

        print status_group.get_status_summary()
        assert (status_group.get_status_summary() == (housekeeping_classes.CRITICAL, ['data1', 'data3', 'data2']))
        # Error here - I don't want the order to matter
        # assert (status_group.get_status_summary() == (status_dict.CRITICAL, ['data1', 'data2', 'data3']))
