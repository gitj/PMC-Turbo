from pmc_camera.communication import status_dict
import unittest


class StatusDictTest(unittest.TestCase):
    def test_item(self):
        item = status_dict.StatusItem(name='test_item', value=0, nominal_range=status_dict.Range(0, 1),
                                      good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        assert (item.get_status_summary() == status_dict.CRITICAL)
        item.update_value(1)
        assert (item.get_status_summary() == status_dict.NOMINAL)
        item.update_value(2)
        assert (item.get_status_summary() == status_dict.GOOD)
        item.update_value(3)
        assert (item.get_status_summary() == status_dict.WARNING)

    def test_filewatcher(self):
        with open('test_file.txt', 'w') as f:
            f.write('data0,data1\n')
            f.write('1,5\n')

        item0 = status_dict.StatusItem(name='data0', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        item1 = status_dict.StatusItem(name='data1', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        items = [item0, item1]
        filewatcher = status_dict.StatusFileWatcher(name='test_filewatcher', items=items, filename='test_file.txt')
        filewatcher.update()
        assert (item0.value == 1)
        assert (item1.value == 5)
        assert filewatcher.get_status_summary() == [('data1', status_dict.CRITICAL)]

    def test_status_group(self):
        with open('test_file0.txt', 'w') as f:
            f.write('data0,data1\n')
            f.write('1,5\n')

        with open('test_file1.txt', 'w') as f:
            f.write('data2,data3\n')
            f.write('5,5\n')

        item0 = status_dict.StatusItem(name='data0', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        item1 = status_dict.StatusItem(name='data1', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        items0 = [item0, item1]
        filewatcher0 = status_dict.StatusFileWatcher(name='test_filewatcher0', items=items0, filename='test_file0.txt')

        item2 = status_dict.StatusItem(name='data2', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        item3 = status_dict.StatusItem(name='data3', value=0, nominal_range=status_dict.Range(0, 1),
                                       good_range=status_dict.Range(1, 2), warning_range=status_dict.Range(2, 3))
        items1 = [item2, item3]
        filewatcher1 = status_dict.StatusFileWatcher(name='test_filewatcher1', items=items1, filename='test_file1.txt')

        status_group = status_dict.StatusGroup('test_group', [filewatcher0, filewatcher1])
        status_group.update()

        assert (status_group.get_status_summary() == [('test_filewatcher0', [('data1', status_dict.CRITICAL)]),
                                                      ('test_filewatcher1', [('data3', status_dict.CRITICAL),
                                                                             ('data2', status_dict.CRITICAL)])])
