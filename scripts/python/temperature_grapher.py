import csv
import matplotlib.pyplot as plt


# /home/pmc/logs/housekeeping/camera/2017-02-17_160805.csv


def get_camera_temps(csv_file):
    times = []
    main_temp = []
    sensor_temp = []
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            try:
                times.append(row[0])
                main_temp.append(row[3])
                sensor_temp.append(row[4])
            except IndexError:
                pass

    times = [float(t) for t in times[2:]]
    main_temp = [float(t) for t in main_temp[1:]]
    sensor_temp = [float(t) for t in sensor_temp[1:]]

    return times, main_temp, sensor_temp


def get_labjack_temps(csv_file):
    times = []
    labjack_temp = []
    lens_side_temp = []
    cable_side_temp = []

    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            try:
                times.append(row[0])
                labjack_temp.append(row[1])
                lens_side_temp.append(row[7])
                cable_side_temp.append(row[8])
            except IndexError:
                pass

    times = [float(t) for t in times[2:]]
    labjack_temp = [(float(t) - 273) for t in labjack_temp[1:]]
    lens_side_temp = [((float(t) * 1000) - 273) for t in lens_side_temp[1:]]
    cable_side_temp = [((float(t) * 1000) - 273) for t in cable_side_temp[1:]]

    return times, labjack_temp, lens_side_temp, cable_side_temp


def graph_temps(csv_file0, csv_file1):
    times0, main_temp, sensor_temp = get_camera_temps(csv_file0)

    times1, labjack_temp, lens_side_temp, cable_side_temp = get_labjack_temps(csv_file1)

    fig, axes = plt.subplots(3, 2)
    axes[0][0].plot(times0, main_temp)
    axes[0][0].set_title('Main temperature versus time')
    axes[0][0].set_xlabel('Timestamp (s)')
    axes[0][0].set_ylabel('Main temperature (C)')

    axes[1][0].plot(times0, sensor_temp)
    axes[1][0].set_title('Sensor temperature versus time')
    axes[1][0].set_xlabel('Timestamp (s)')
    axes[1][0].set_ylabel('Sensor temperature (C)')

    axes[0][1].plot(times1, labjack_temp)
    axes[0][1].set_title('Labjack temperature versus time')
    axes[0][1].set_xlabel('Timestamp (s)')
    axes[0][1].set_ylabel('Sensor temperature (C)')

    axes[1][1].plot(times1, lens_side_temp)
    axes[1][1].set_title('Lens side temperature versus time')
    axes[1][1].set_xlabel('Timestamp (s)')
    axes[1][1].set_ylabel('Sensor temperature (C)')

    axes[2][1].plot(times1, cable_side_temp)
    axes[2][1].set_title('Cable side temperature versus time')
    axes[2][1].set_xlabel('Timestamp (s)')
    axes[2][1].set_ylabel('Sensor temperature (C)')

    plt.show()


if __name__ == "__main__":
    # graph_temps('/home/pmc/logs/housekeeping/camera/2017-02-17_160805.csv',
    #            '/home/pmc/logs/housekeeping/labjack/2017-02-17_160813.csv')

    graph_temps('/home/pmc/logs/housekeeping/camera/2017-02-18_132924.csv',
                '/home/pmc/logs/housekeeping/labjack/2017-02-17_160813.csv')
