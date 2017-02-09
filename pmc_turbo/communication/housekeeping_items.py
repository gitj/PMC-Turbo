import glob
import os
import pandas as pd
import json


def get_collectd_items(csv_filename=None):
    collectd_files = glob.glob('/var/lib/collectd/csv/*/*/*-2017-01-25')
    collectd_files.sort()
    result = []
    for fn in collectd_files:
        name = os.path.join(os.path.split(os.path.split(fn)[0])[-1], os.path.split(fn)[-1])
        name = name.replace('2017-01-25', '*')
        df = pd.read_csv(fn, index_col='epoch', comment='#')
        for col in df.columns:
            class_type = 'FloatStatusItem'
            scaling = 1.0
            good_range_low, good_range_high = 'nan', 'nan'
            normal_range_low, normal_range_high = 0, 0
            warning_range_low, warning_range_high = 0, 0
            normal_string, warning_string, good_string = '', '', ''

            result.append((name, col, class_type, df[col].min(), df[col].mean(), df[col].max(), df[col].std(),
                           scaling, good_range_low, good_range_high, normal_range_low, normal_range_high,
                           warning_range_low, warning_range_high,
                           normal_string, good_string, warning_string))
    if csv_filename:
        with open(csv_filename, 'w') as fh:
            fh.write(
                ','.join(
                    ['partial_glob', 'column_name', 'class_type', 'min_value', 'mean_value', 'max_value', 'std_value',
                     'scaling_value', 'good_range_low', 'good_range_high', 'normal_range_low', 'normal_range_high',
                     'warning_range_low', 'warning_range_high', 'normal_string', 'good_string',
                     'warning_string']) + '\n')
            for row in result:
                fh.write(','.join([str(x) for x in row]) + '\n')
    return result


def get_items(partial_glob, csv_filename=None, json_filename=None):
    files = glob.glob(partial_glob)
    files.sort()
    fn = files[-1]
    print "using file", fn
    df = pd.read_csv(fn, index_col='epoch', comment='#')

    result = []
    for colname in df.columns:
        col = df[colname]
        if col.dtype == 'O':  # string columns are Objects
            class_type = 'StringStatusItem'
            min = ''
            max = ''
            mean = col.value_counts().index[0]
            std = ''
            scaling = ''
        else:
            class_type = 'FloatStatusItem'
            min = col.min()
            max = col.max()
            mean = col.mean()
            std = col.std()
            scaling = 1.0
        result.append((partial_glob, colname, class_type, min, mean, max, std, scaling))

    title_list = ['partial_glob', 'column_name', 'class_type', 'min_value', 'mean_value', 'max_value', 'std_value',
                  'scaling_value']

    if csv_filename:
        with open(csv_filename, 'w') as fh:
            fh.write(
                ','.join(title_list) + '\n')
            for row in result:
                fh.write(','.join([str(x) for x in row]) + '\n')

    if json_filename:
        result_list = [dict(zip(title_list, row)) for row in result]
        result_keys = [row[1] for row in result]

        result_dict = dict(zip(result_keys, result_list))

        with open(json_filename, 'w') as fh:
            fh.write(
                json.dumps(result_dict, separators=(',', ': '), indent=4, sort_keys=True)
            )
    return result


def get_range_outline(partial_glob, json_filename=None):
    files = glob.glob(partial_glob)
    files.sort()
    fn = files[-1]
    print "using file", fn
    df = pd.read_csv(fn, index_col='epoch', comment='#')

    result = []
    for colname in df.columns:
        col = df[colname]
        if col.dtype == 'O':  # string columns are Objects
            class_type = 'StringStatusItem'

            good_range_low, good_range_high = '', ''
            normal_range_low, normal_range_high = '', ''
            warning_range_low, warning_range_high = '', ''
            normal_string, good_string, critical_string = '', '', ''
        else:
            class_type = 'FloatStatusItem'

            good_range_low, good_range_high = 'nan', 'nan'
            normal_range_low, normal_range_high = 'nan', 'nan'
            warning_range_low, warning_range_high = 'nan', 'nan'
            normal_string, good_string, critical_string = '', '', ''
        result.append((partial_glob, colname, class_type,
                       good_range_low, good_range_high, normal_range_low, normal_range_high,
                       warning_range_low, warning_range_high,
                       normal_string, good_string, critical_string))

    title_list = ['partial_glob', 'column_name', 'class_type',
                  'good_range_low', 'good_range_high', 'normal_range_low', 'normal_range_high',
                  'warning_range_low', 'warning_range_high', 'normal_string', 'good_string',
                  'warning_string']

    if json_filename:
        result_list = [dict(zip(title_list, row)) for row in result]
        result_keys = [row[1] for row in result]

        result_dict = dict(zip(result_keys, result_list))

        with open(json_filename, 'w') as fh:
            fh.write(
                json.dumps(result_dict, separators=(',', ': '), indent=4, sort_keys=True)
            )
    return result


def get_camera_items(csv_filename=None, json_filename=None):
    a = get_items(partial_glob='/home/pmc/logs/housekeeping/camera/*.csv', csv_filename=csv_filename,
                  json_filename=json_filename + '.json')

    b = get_range_outline(partial_glob='/home/pmc/logs/housekeeping/camera/*.csv',
                          json_filename=json_filename + '_ranges.json')

    return a, b


def get_labjack_items(csv_filename=None, json_filename=None):
    return get_items(partial_glob='/home/pmc/logs/housekeeping/labjack/*.csv', csv_filename=csv_filename,
                     json_filename=json_filename)


def get_charge_controller_items(csv_filename=None, json_filename=None):
    a = get_items(partial_glob='/home/pmc/logs/housekeeping/charge_controller/*-??_??????.csv',
                  csv_filename=csv_filename, json_filename=json_filename + '.json')

    b = get_range_outline(partial_glob='/home/pmc/logs/housekeeping/charge_controller/*-??_??????.csv',
                          json_filename=json_filename + '_ranges.json')

    return a, b


all_collectd_sensors = ['cpu-0/cpu-idle-*',
                        'cpu-0/cpu-interrupt-*',
                        'cpu-0/cpu-nice-*',
                        'cpu-0/cpu-softirq-*',
                        'cpu-0/cpu-steal-*',
                        'cpu-0/cpu-system-*',
                        'cpu-0/cpu-user-*',
                        'cpu-0/cpu-wait-*',
                        'cpu-1/cpu-idle-*',
                        'cpu-1/cpu-interrupt-*',
                        'cpu-1/cpu-nice-*',
                        'cpu-1/cpu-softirq-*',
                        'cpu-1/cpu-steal-*',
                        'cpu-1/cpu-system-*',
                        'cpu-1/cpu-user-*',
                        'cpu-1/cpu-wait-*',
                        'cpu-2/cpu-idle-*',
                        'cpu-2/cpu-interrupt-*',
                        'cpu-2/cpu-nice-*',
                        'cpu-2/cpu-softirq-*',
                        'cpu-2/cpu-steal-*',
                        'cpu-2/cpu-system-*',
                        'cpu-2/cpu-user-*',
                        'cpu-2/cpu-wait-*',
                        'cpu-3/cpu-idle-*',
                        'cpu-3/cpu-interrupt-*',
                        'cpu-3/cpu-nice-*',
                        'cpu-3/cpu-softirq-*',
                        'cpu-3/cpu-steal-*',
                        'cpu-3/cpu-system-*',
                        'cpu-3/cpu-user-*',
                        'cpu-3/cpu-wait-*',
                        'cpu-4/cpu-idle-*',
                        'cpu-4/cpu-interrupt-*',
                        'cpu-4/cpu-nice-*',
                        'cpu-4/cpu-softirq-*',
                        'cpu-4/cpu-steal-*',
                        'cpu-4/cpu-system-*',
                        'cpu-4/cpu-user-*',
                        'cpu-4/cpu-wait-*',
                        'cpu-5/cpu-idle-*',
                        'cpu-5/cpu-interrupt-*',
                        'cpu-5/cpu-nice-*',
                        'cpu-5/cpu-softirq-*',
                        'cpu-5/cpu-steal-*',
                        'cpu-5/cpu-system-*',
                        'cpu-5/cpu-user-*',
                        'cpu-5/cpu-wait-*',
                        'cpu-6/cpu-idle-*',
                        'cpu-6/cpu-interrupt-*',
                        'cpu-6/cpu-nice-*',
                        'cpu-6/cpu-softirq-*',
                        'cpu-6/cpu-steal-*',
                        'cpu-6/cpu-system-*',
                        'cpu-6/cpu-user-*',
                        'cpu-6/cpu-wait-*',
                        'cpu-7/cpu-idle-*',
                        'cpu-7/cpu-interrupt-*',
                        'cpu-7/cpu-nice-*',
                        'cpu-7/cpu-softirq-*',
                        'cpu-7/cpu-steal-*',
                        'cpu-7/cpu-system-*',
                        'cpu-7/cpu-user-*',
                        'cpu-7/cpu-wait-*',
                        'df-data1/df_complex-free-*',
                        'df-data1/df_complex-reserved-*',
                        'df-data1/df_complex-used-*',
                        'df-data2/df_complex-free-*',
                        'df-data2/df_complex-reserved-*',
                        'df-data2/df_complex-used-*',
                        'df-data3/df_complex-free-*',
                        'df-data3/df_complex-reserved-*',
                        'df-data3/df_complex-used-*',
                        'df-data4/df_complex-free-*',
                        'df-data4/df_complex-reserved-*',
                        'df-data4/df_complex-used-*',
                        'df-home-pmc-pmchome/df_complex-free-*',
                        'df-home-pmc-pmchome/df_complex-reserved-*',
                        'df-home-pmc-pmchome/df_complex-used-*',
                        'df-root/df_complex-free-*',
                        'df-root/df_complex-reserved-*',
                        'df-root/df_complex-used-*',
                        'disk-sda/disk_merged-*',
                        'disk-sda/disk_octets-*',
                        'disk-sda/disk_ops-*',
                        'disk-sda/disk_time-*',
                        'disk-sda1/disk_merged-*',
                        'disk-sda1/disk_octets-*',
                        'disk-sda1/disk_ops-*',
                        'disk-sda1/disk_time-*',
                        'disk-sdb/disk_merged-*',
                        'disk-sdb/disk_octets-*',
                        'disk-sdb/disk_ops-*',
                        'disk-sdb/disk_time-*',
                        'disk-sdb1/disk_merged-*',
                        'disk-sdb1/disk_octets-*',
                        'disk-sdb1/disk_ops-*',
                        'disk-sdb1/disk_time-*',
                        'disk-sdc/disk_merged-*',
                        'disk-sdc/disk_octets-*',
                        'disk-sdc/disk_ops-*',
                        'disk-sdc/disk_time-*',
                        'disk-sdc1/disk_merged-*',
                        'disk-sdc1/disk_octets-*',
                        'disk-sdc1/disk_ops-*',
                        'disk-sdc1/disk_time-*',
                        'disk-sdd/disk_merged-*',
                        'disk-sdd/disk_octets-*',
                        'disk-sdd/disk_ops-*',
                        'disk-sdd/disk_time-*',
                        'disk-sdd1/disk_merged-*',
                        'disk-sdd1/disk_octets-*',
                        'disk-sdd1/disk_ops-*',
                        'disk-sdd1/disk_time-*',
                        'disk-sdd2/disk_merged-*',
                        'disk-sdd2/disk_octets-*',
                        'disk-sdd2/disk_ops-*',
                        'disk-sdd5/disk_merged-*',
                        'disk-sdd5/disk_octets-*',
                        'disk-sdd5/disk_ops-*',
                        'disk-sdd5/disk_time-*',
                        'disk-sde/disk_merged-*',
                        'disk-sde/disk_octets-*',
                        'disk-sde/disk_ops-*',
                        'disk-sde/disk_time-*',
                        'disk-sde1/disk_merged-*',
                        'disk-sde1/disk_octets-*',
                        'disk-sde1/disk_ops-*',
                        'disk-sde1/disk_time-*',
                        'disk-sde2/disk_merged-*',
                        'disk-sde2/disk_octets-*',
                        'disk-sde2/disk_ops-*',
                        'disk-sde5/disk_merged-*',
                        'disk-sde5/disk_octets-*',
                        'disk-sde5/disk_ops-*',
                        'disk-sde5/disk_time-*',
                        'disk-sdf/disk_merged-*',
                        'disk-sdf/disk_octets-*',
                        'disk-sdf/disk_ops-*',
                        'disk-sdf/disk_time-*',
                        'disk-sdf1/disk_merged-*',
                        'disk-sdf1/disk_octets-*',
                        'disk-sdf1/disk_ops-*',
                        'disk-sdf1/disk_time-*',
                        'entropy/entropy-*',
                        'ethstat-eth1/derive-collisions-*',
                        'ethstat-eth1/derive-dropped_smbus-*',
                        'ethstat-eth1/derive-multicast-*',
                        'ethstat-eth1/derive-os2bmc_rx_by_bmc-*',
                        'ethstat-eth1/derive-os2bmc_rx_by_host-*',
                        'ethstat-eth1/derive-os2bmc_tx_by_bmc-*',
                        'ethstat-eth1/derive-os2bmc_tx_by_host-*',
                        'ethstat-eth1/derive-rx_align_errors-*',
                        'ethstat-eth1/derive-rx_broadcast-*',
                        'ethstat-eth1/derive-rx_bytes-*',
                        'ethstat-eth1/derive-rx_crc_errors-*',
                        'ethstat-eth1/derive-rx_errors-*',
                        'ethstat-eth1/derive-rx_fifo_errors-*',
                        'ethstat-eth1/derive-rx_flow_control_xoff-*',
                        'ethstat-eth1/derive-rx_flow_control_xon-*',
                        'ethstat-eth1/derive-rx_frame_errors-*',
                        'ethstat-eth1/derive-rx_hwtstamp_cleared-*',
                        'ethstat-eth1/derive-rx_length_errors-*',
                        'ethstat-eth1/derive-rx_long_byte_count-*',
                        'ethstat-eth1/derive-rx_long_length_errors-*',
                        'ethstat-eth1/derive-rx_missed_errors-*',
                        'ethstat-eth1/derive-rx_multicast-*',
                        'ethstat-eth1/derive-rx_no_buffer_count-*',
                        'ethstat-eth1/derive-rx_over_errors-*',
                        'ethstat-eth1/derive-rx_packets-*',
                        'ethstat-eth1/derive-rx_queue_0_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_0_bytes-*',
                        'ethstat-eth1/derive-rx_queue_0_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_0_drops-*',
                        'ethstat-eth1/derive-rx_queue_0_packets-*',
                        'ethstat-eth1/derive-rx_queue_1_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_1_bytes-*',
                        'ethstat-eth1/derive-rx_queue_1_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_1_drops-*',
                        'ethstat-eth1/derive-rx_queue_1_packets-*',
                        'ethstat-eth1/derive-rx_queue_2_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_2_bytes-*',
                        'ethstat-eth1/derive-rx_queue_2_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_2_drops-*',
                        'ethstat-eth1/derive-rx_queue_2_packets-*',
                        'ethstat-eth1/derive-rx_queue_3_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_3_bytes-*',
                        'ethstat-eth1/derive-rx_queue_3_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_3_drops-*',
                        'ethstat-eth1/derive-rx_queue_3_packets-*',
                        'ethstat-eth1/derive-rx_queue_4_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_4_bytes-*',
                        'ethstat-eth1/derive-rx_queue_4_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_4_drops-*',
                        'ethstat-eth1/derive-rx_queue_4_packets-*',
                        'ethstat-eth1/derive-rx_queue_5_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_5_bytes-*',
                        'ethstat-eth1/derive-rx_queue_5_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_5_drops-*',
                        'ethstat-eth1/derive-rx_queue_5_packets-*',
                        'ethstat-eth1/derive-rx_queue_6_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_6_bytes-*',
                        'ethstat-eth1/derive-rx_queue_6_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_6_drops-*',
                        'ethstat-eth1/derive-rx_queue_6_packets-*',
                        'ethstat-eth1/derive-rx_queue_7_alloc_failed-*',
                        'ethstat-eth1/derive-rx_queue_7_bytes-*',
                        'ethstat-eth1/derive-rx_queue_7_csum_err-*',
                        'ethstat-eth1/derive-rx_queue_7_drops-*',
                        'ethstat-eth1/derive-rx_queue_7_packets-*',
                        'ethstat-eth1/derive-rx_short_length_errors-*',
                        'ethstat-eth1/derive-rx_smbus-*',
                        'ethstat-eth1/derive-tx_abort_late_coll-*',
                        'ethstat-eth1/derive-tx_aborted_errors-*',
                        'ethstat-eth1/derive-tx_broadcast-*',
                        'ethstat-eth1/derive-tx_bytes-*',
                        'ethstat-eth1/derive-tx_carrier_errors-*',
                        'ethstat-eth1/derive-tx_deferred_ok-*',
                        'ethstat-eth1/derive-tx_dma_out_of_sync-*',
                        'ethstat-eth1/derive-tx_dropped-*',
                        'ethstat-eth1/derive-tx_errors-*',
                        'ethstat-eth1/derive-tx_fifo_errors-*',
                        'ethstat-eth1/derive-tx_flow_control_xoff-*',
                        'ethstat-eth1/derive-tx_flow_control_xon-*',
                        'ethstat-eth1/derive-tx_heartbeat_errors-*',
                        'ethstat-eth1/derive-tx_hwtstamp_timeouts-*',
                        'ethstat-eth1/derive-tx_multi_coll_ok-*',
                        'ethstat-eth1/derive-tx_multicast-*',
                        'ethstat-eth1/derive-tx_packets-*',
                        'ethstat-eth1/derive-tx_queue_0_bytes-*',
                        'ethstat-eth1/derive-tx_queue_0_packets-*',
                        'ethstat-eth1/derive-tx_queue_0_restart-*',
                        'ethstat-eth1/derive-tx_queue_1_bytes-*',
                        'ethstat-eth1/derive-tx_queue_1_packets-*',
                        'ethstat-eth1/derive-tx_queue_1_restart-*',
                        'ethstat-eth1/derive-tx_queue_2_bytes-*',
                        'ethstat-eth1/derive-tx_queue_2_packets-*',
                        'ethstat-eth1/derive-tx_queue_2_restart-*',
                        'ethstat-eth1/derive-tx_queue_3_bytes-*',
                        'ethstat-eth1/derive-tx_queue_3_packets-*',
                        'ethstat-eth1/derive-tx_queue_3_restart-*',
                        'ethstat-eth1/derive-tx_queue_4_bytes-*',
                        'ethstat-eth1/derive-tx_queue_4_packets-*',
                        'ethstat-eth1/derive-tx_queue_4_restart-*',
                        'ethstat-eth1/derive-tx_queue_5_bytes-*',
                        'ethstat-eth1/derive-tx_queue_5_packets-*',
                        'ethstat-eth1/derive-tx_queue_5_restart-*',
                        'ethstat-eth1/derive-tx_queue_6_bytes-*',
                        'ethstat-eth1/derive-tx_queue_6_packets-*',
                        'ethstat-eth1/derive-tx_queue_6_restart-*',
                        'ethstat-eth1/derive-tx_queue_7_bytes-*',
                        'ethstat-eth1/derive-tx_queue_7_packets-*',
                        'ethstat-eth1/derive-tx_queue_7_restart-*',
                        'ethstat-eth1/derive-tx_single_coll_ok-*',
                        'ethstat-eth1/derive-tx_smbus-*',
                        'ethstat-eth1/derive-tx_tcp_seg_failed-*',
                        'ethstat-eth1/derive-tx_tcp_seg_good-*',
                        'ethstat-eth1/derive-tx_timeout_count-*',
                        'ethstat-eth1/derive-tx_window_errors-*',
                        'interface-eth0/if_errors-*',
                        'interface-eth0/if_octets-*',
                        'interface-eth0/if_packets-*',
                        'interface-eth1/if_errors-*',
                        'interface-eth1/if_octets-*',
                        'interface-eth1/if_packets-*',
                        'interface-eth2/if_errors-*',
                        'interface-eth2/if_octets-*',
                        'interface-eth2/if_packets-*',
                        'interface-eth3/if_errors-*',
                        'interface-eth3/if_octets-*',
                        'interface-eth3/if_packets-*',
                        'interface-lo/if_errors-*',
                        'interface-lo/if_octets-*',
                        'interface-lo/if_packets-*',
                        'ipmi/temperature-CPU Temp processor (3.1)-*',
                        'ipmi/temperature-DIMMA1 Temp memory_device (32.64)-*',
                        'ipmi/temperature-DIMMB1 Temp memory_device (32.68)-*',
                        'ipmi/temperature-Peripheral Temp system_board (7.2)-*',
                        'ipmi/temperature-System Temp system_board (7.1)-*',
                        'ipmi/voltage-12V system_board (7.17)-*',
                        'ipmi/voltage-3.3V AUX system_board (7.12)-*',
                        'ipmi/voltage-3.3VCC system_board (7.32)-*',
                        'ipmi/voltage-5V Dual system_board (7.15)-*',
                        'ipmi/voltage-5VCC system_board (7.33)-*',
                        'ipmi/voltage-VBAT system_board (7.18)-*',
                        'ipmi/voltage-VCCP processor (3.2)-*',
                        'ipmi/voltage-VDIMM memory_device (32.1)-*',
                        'load/load-*',
                        'md-0/md_disks-active-*',
                        'md-0/md_disks-failed-*',
                        'md-0/md_disks-missing-*',
                        'md-0/md_disks-spare-*',
                        'md-1/md_disks-active-*',
                        'md-1/md_disks-failed-*',
                        'md-1/md_disks-missing-*',
                        'md-1/md_disks-spare-*',
                        'memory/memory-buffered-*',
                        'memory/memory-cached-*',
                        'memory/memory-free-*',
                        'memory/memory-used-*',
                        'processes/fork_rate-*',
                        'processes/ps_state-blocked-*',
                        'processes/ps_state-paging-*',
                        'processes/ps_state-running-*',
                        'processes/ps_state-sleeping-*',
                        'processes/ps_state-stopped-*',
                        'processes/ps_state-zombies-*',
                        'protocols-Udp/protocol_counter-InCsumErrors-*',
                        'protocols-Udp/protocol_counter-InDatagrams-*',
                        'protocols-Udp/protocol_counter-InErrors-*',
                        'protocols-Udp/protocol_counter-NoPorts-*',
                        'protocols-Udp/protocol_counter-OutDatagrams-*',
                        'protocols-Udp/protocol_counter-RcvbufErrors-*',
                        'protocols-Udp/protocol_counter-SndbufErrors-*',
                        'sensors-coretemp-isa-0000/temperature-temp2-*',
                        'sensors-coretemp-isa-0000/temperature-temp3-*',
                        'sensors-coretemp-isa-0000/temperature-temp4-*',
                        'sensors-coretemp-isa-0000/temperature-temp5-*',
                        'sensors-coretemp-isa-0000/temperature-temp6-*',
                        'sensors-coretemp-isa-0000/temperature-temp7-*',
                        'sensors-coretemp-isa-0000/temperature-temp8-*',
                        'sensors-coretemp-isa-0000/temperature-temp9-*',
                        'sensors-jc42-i2c-1-18/temperature-temp1-*',
                        'swap/swap-cached-*',
                        'swap/swap-free-*',
                        'swap/swap-used-*',
                        'swap/swap_io-in-*',
                        'swap/swap_io-out-*',
                        'users/users-*']
