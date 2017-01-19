from pmc_camera.communication import status_dict
import unittest
import tempfile


class StatusDictTest(unittest.TestCase):
    def test_item(self):
        item = status_dict.StatusItem(name='test_item', value=0, nominal_range=status_dict.Range(0, 1),
                                      good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        item.update_value(0.5)
        assert (item.get_status_summary() == status_dict.NOMINAL)
        item.update_value(1.5)
        assert (item.get_status_summary() == status_dict.GOOD)
        item.update_value(2.5)
        assert (item.get_status_summary() == status_dict.WARNING)

    def test_filewatcher(self):
        tfile = tempfile.NamedTemporaryFile()

        with open(tfile.name, 'w') as f:
            f.write('data0,data1\n')
            f.write('1,5\n')

        item0 = status_dict.StatusItem(name='data0', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        item1 = status_dict.StatusItem(name='data1', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        items = [item0, item1]
        filewatcher = status_dict.StatusFileWatcher(name='test_filewatcher', items=items, filename=tfile.name)
        filewatcher.update()
        assert (item0.value == 1)
        assert (item1.value == 5)
        assert filewatcher.get_status_summary() == [('data1', status_dict.CRITICAL)]

    def test_status_group(self):
        tfile0 = tempfile.NamedTemporaryFile()
        tfile1 = tempfile.NamedTemporaryFile()

        with open(tfile0.name, 'w') as f:
            f.write('data0,data1\n')
            f.write('1,5\n')

        with open(tfile1.name, 'w') as f:
            f.write('data2,data3\n')
            f.write('5,5\n')

        item0 = status_dict.StatusItem(name='data0', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        item1 = status_dict.StatusItem(name='data1', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        items0 = [item0, item1]
        filewatcher0 = status_dict.StatusFileWatcher(name='test_filewatcher0', items=items0, filename=tfile0.name)

        item2 = status_dict.StatusItem(name='data2', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        item3 = status_dict.StatusItem(name='data3', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        items1 = [item2, item3]
        filewatcher1 = status_dict.StatusFileWatcher(name='test_filewatcher1', items=items1, filename=tfile1.name)

        status_group = status_dict.StatusGroup('test_group', [filewatcher0, filewatcher1])
        status_group.update()

        assert (status_group.get_status_summary() == [('test_filewatcher0', [('data1', status_dict.CRITICAL)]),
                                                      ('test_filewatcher1', [('data3', status_dict.CRITICAL),
                                                                             ('data2', status_dict.CRITICAL)])])
