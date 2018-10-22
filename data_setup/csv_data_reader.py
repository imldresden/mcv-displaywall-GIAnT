import os.path
import csv


def get_data(filename):

    if not os.path.isfile(filename):
        raise Exception("There is no " + filename + " to create the data from.")

    with open(filename, 'rb') as file_csv:
        csv_reader = csv.reader(file_csv, delimiter=",")

        data = {}
        index_keys = {}
        header_done = False
        for row in csv_reader:
            if not header_done:
                # work through header -> dict with list for each item, header elements are keys
                for index, value in enumerate(row):
                    value = str(value).strip()
                    index_keys[index] = value
                    data[value] = []
                header_done = True
                continue

            for index, value in enumerate(row):
                # Make sure that all milliseconds have 3 digits
                if index_keys[index] == "time" and len(value) < 13:
                    value = "{}{}{}".format(value[:10], "0" * (13 - len(value)), value[10:])
                data[index_keys[index]].append(value)

    return data
