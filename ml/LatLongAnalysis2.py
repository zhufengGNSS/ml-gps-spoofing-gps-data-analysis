from utils.data import get_lat_long_entries_from_file
from utils.data import nmea_log_to_entry
import multiprocessing as mp
from threading import Thread
from kafka import KafkaConsumer
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.animation as animation

topic_name = 'raw_nmea'


def main(file):
    fig, axes = plt.subplots(nrows=2, ncols=1)
    plt.subplots_adjust(left=0.15, hspace=0.5)

    lat_long_entries = get_lat_long_entries_from_file(file)

    lat_entries = []
    long_entries = []
    for lat_long_entry in lat_long_entries:
        lat_entries.append(float(lat_long_entry[0]))
        long_entries.append(float(lat_long_entry[1]))

    axes[0].set_title("Latitude")
    axes[0].boxplot(lat_entries, vert=False)
    axes[0].set_yticklabels(['Monitoring', 'Ground\nTruth'])

    Q1_lat = np.percentile(lat_entries, 25)
    Q3_lat = np.percentile(lat_entries, 75)

    lat_lower_whisker = Q1_lat - (1.5 * (Q3_lat - Q1_lat))
    lat_upper_whisker = Q3_lat + (1.5 * (Q3_lat - Q1_lat))

    print("    Lat values:")
    print("\tMedian: " + str(np.median(lat_entries)))
    print("\tLower percentile: " + str(Q1_lat))
    print("\tUpper percentile: " + str(Q3_lat))
    print("\tLower whisker: " + str(lat_lower_whisker))
    print("\tUpper whisker: " + str(lat_upper_whisker))

    axes[1].set_title("Longitude")
    axes[1].boxplot(long_entries, vert=False)
    axes[1].set_yticklabels(['Monitoring', 'Ground\nTruth'])

    Q1_long = np.percentile(long_entries, 25)
    Q3_long = np.percentile(long_entries, 75)

    long_lower_whisker = Q1_long - (1.5 * (Q3_long - Q1_long))
    long_upper_whisker = Q3_long + (1.5 * (Q3_long - Q1_long))

    print("    Long values:")
    print("\tMedian: " + str(np.median(long_entries)))
    print("\tLower percentile: " + str(Q1_long))
    print("\tUpper percentile: " + str(Q3_long))
    print("\tLower whisker: " + str(long_lower_whisker))
    print("\tUpper whisker: " + str(long_upper_whisker))

    queue = mp.Queue()

    lat_long_vals = [[], []]

    thread = Thread(target=consumeData, args=(queue,))
    thread.start()

    # Set up plot to call animate() function periodically
    ani = animation.FuncAnimation(fig, animate, fargs=(fig, axes, queue, [lat_entries, long_entries], lat_long_vals),
                                  interval=1000)
    plt.show()

    print("    Exiting...")
    return


def animate(i, fig, axes, q, ground_truth, observation_vals):

    try:
        lat_long = q.get(timeout=10)
    except:
        print("    Timeout expired, closing visualization.")
        plt.close(fig)
        return

    observation_vals[0].append(lat_long[0])
    observation_vals[1].append(lat_long[1])

    #we observe only the last 20 entries, otherwise our boxplot is influenced by old values
    observation_vals[0] = observation_vals[0][-20:]
    observation_vals[1] = observation_vals[1][-20:]

    axes[0].clear()
    axes[0].boxplot([observation_vals[0], ground_truth[0]], vert=False)
    axes[0].set_yticklabels(['Monitoring', 'Ground\nTruth'])
    axes[0].set_title('Latitude')

    axes[1].clear()
    axes[1].boxplot([observation_vals[1], ground_truth[1]], vert=False)
    axes[1].set_yticklabels(['Monitoring', 'Ground\nTruth'])
    axes[1].set_title('Longitude')


def consumeData(queue):

    consumer = KafkaConsumer(topic_name, auto_offset_reset='earliest', bootstrap_servers=['localhost:9092'],
                             consumer_timeout_ms=10000)

    for msg in consumer:
        entry = msg.value.decode('utf-8')

        entry = nmea_log_to_entry(entry)

        if len(entry) == 0:
            continue

        GGA_entry = entry['$GPGGA']
        lat = GGA_entry[1]
        long = GGA_entry[2]

        queue.put([float(lat), float(long)])

    consumer.close()


if __name__ == '__main__':
    main("../data/true_data.txt")
