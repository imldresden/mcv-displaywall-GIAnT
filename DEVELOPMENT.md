# Development Guide

## Used data set

The data set that was used and produced in our study in our research article can be found on our [project page](https://imld.de/mcv-displaywall/). This data set is already in the GIAnT readable format.

## Setup and Run within PyCharm

1. Load the root folder in PyCharm and open the **Project** tab.
2. Prepare the config files for the data conversion.
3. Right click on `data_setup/divico_to_giant.py` and choose **Run 'divico_to_giant'**.
4. Right click on `data_setup/db_setup` and choose **Run 'db_setup'**.
3. Right click on `main.py` and choose **Run 'main'**.

## Importing the data and the videos

GIAnT expects its data to be in an SQLite database and provides a script to generate this database from raw csv files. You will probably need to tweak settings in setup.py and pat_model.py to get it to find your files, and, if necessary, adapt the import to your csv files.

### CSV files

There are currently four csv files per session, formatted as follows:

* optitrack head data (giant_session_X_users.csv): 
  * timestamp: hh:mm:ss:mil
  * userid
  * pos: (x,y,z) in meters. (0,0,0) is at the lower left corner of the wall. When facing the wall, x points left, y up, z into the wall.
  * rot: (yaw, pitch, roll) angle in radians. Angles are applied in this order. Origin is facing the wall.
  
```csv
"timestamp","id","pos","rot"
"15:24:36.685","1","(-2.7256436347961426, 1.3635157346725464, -1.8309845924377441)","(0.21834592521190643, -0.7315365076065063, 0.20152150094509125)"
"15:24:36.686","1","(-2.7256436347961426, 1.3635157346725464, -1.8309845924377441)","(0.21834592521190643, -0.7315365076065063, 0.20152150094509125)"
"15:24:36.686","1","(-2.7256436347961426, 1.3635157346725464, -1.8309845924377441)","(0.21834592521190643, -0.7315365076065063, 0.20152150094509125)"
```
  
* touch data (giant_session_X_touch.csv):
  * timestamp: hh:mm:ss:mil
  * (x,y): position in pixels
  * userid: String identifier of the user
  * injected: bool, if this touch was injected through any other means
  * type: the type of the touch input

```csv
"timestamp","pos","userid","injected","type"
"15:25:16.947","(6365,1501)","1","False","UP"
"15:25:18.447","(5387,1804)","2","True","DOWN"
"15:25:18.447","(5372,1839)","None","False","MOTION"
```

Two extra files were added for the use in DiViCo:

* device position and pointing data (giant_session_X_device.csv):
  * timestamp: hh:mm:ss:mil
  * userid: The id of the user and the device
  * screenPos: (x, y) position of the pointing cursor on the wall
  * spacePos: (x, y, z)
  * orientation: (pitch, yaw, roll)
  
```csv
"timestamp","userid","screenPos","spacePos","orientation"
"15:02:23.145","2","(6032.192031, -4836.587135)","(2.585115, 1.307900, 3.521495)","(-0.597896, -3.023183, 2.757448)"
"15:02:23.261","2","(6032.192031, -4836.587135)","(2.585115, 1.307900, 3.521495)","(-0.597896, -3.023183, 2.757448)"
"15:02:23.394","1","(10518.515699, -2930.899890)","(5.511001, 1.887489, 1.403250)","(-0.557851, -2.045609, 2.356642)"
```

* touch data on the device (giant_session_X_device_touch.csv):
  * timestamp: hh:mm:ss:mil
  * userid: String identifier of the user
  * (x,y): the position in pixels on the display of the device
  * injected: bool, if this touch was injected through any other means
  * type: the type of the touch input
  
```csv
"timestamp","userid","screenPos","type"
"15:34:50.329","2","(820.000000, 1139.000000)","UP"
"15:35:03.242","1","(311.000000, 1579.000000)","DOWN"
"15:35:03.340","1","(309.000000, 1550.000000)","MOTION"
```

### Prepare the videos

GIAnt also expects a video file for each session. This video file should be coded so that it contains no delta frames, e.g. by running it through ffmpeg or avconv:
```
$ avconv -i filename.mp4 -vcodec h264 -g 1 filename.mp4
```
The timestamp in the video filename is used for synchronization with the motion and touch data, so it's best to generate the video file name automatically.

To convert a 1080p to a 720p video with it only contain i-frames, use this:
```
$ avconv -i filename.mp4 -vcodec h264 -g 1 -strict -2 -s hd720 filename.mp4
```

*NOTE: Its also possible to use GIAnT without the videos.*
  
### Run the scripts

First of all, it is necessary to convert the raw output data to a csv-file format the *db_setup.py* script can read. The logging files needs to be placed correctly:
+ The files needs to placed and names as `data_logs/session_[number]/session_[number]_[type].csv`, where `number` is the *session id* and `type` is *[body_tracking, device_position, touch, ...*.
+ Also add the videos without delta framges in the same folder with the following name `session_[number]_video_[type]_[timestamp].mp4` where `type` is *[kinect, camUser, camWall]* and the `timestamp` is the start timestamp of the video.

To convert the raw data, run the following script:
```
data_setup/divico_to_giant.py
```

After this the now GIAnT readable csv-files can be converted to an sqlite database that the prototyp uses. 
+ Look at the *divico_to_giant.py* first line the set the input/output files prefix.
+ The converted files will be placed in the `data_setup` folder.
+ The results are named `giant_session_[number]_[type].csv` where `type` is *[touch, user, device]*.
+ The script will also create a file with the name `session_[number]_sekelton_id_mapping.txt` in the `data_logs/session_[number]` folder. This shows the mapping of the skelleton ids from a kinect to the GIAnT users. The mapping can be changed and used in the config file for the session.

To achieve the conversion, run the following script:
```
data_setup/db_setup.py
```

## Parameters in a config file for a session

It's possible to configure the parameters that will be used for the `divico_to_giant.py` script. Each session can get it's own config file with the `name session_[number]_config.py`. Each of those config files should have the following parameters:
+ session_time_offset
+ video_offset
+ video_timestamps
+ phase_timestamps
+ joint_type_body_to_device
+ joint_type_body_to_touch
+ device_id_count_threshold
+ max_time_delta_body_to_device
+ max_dist_delta_body_to_device
+ max_time_delta_touch_to_inj
+ max_time_delta_inj_to_de
+ max_time_delta_body_to_touch
+ min_body_dist_to_wall
+ arm_span
+ ignore_not_found_touch_ids
+ ignore_skeleton_ids
+ user_ids

For a further explanation of each of the parameters look in the `data_logs/session_EXAMPLE_config.py`.

## Keyboard Shortcuts

The GIAnT application has a few keyboard shortcuts that can be used:

- __Right__: Shift the currently shown time interval further in the future.
- __Left__: Moves the currently shown time interval further in the past.
- __Up__: Zooms in. This factor is far greater than the factor for the zoom out.
- __Down__: Zooms out.
- __Space__: Starts or pauses the video playback.
- __F__: Changes (toggles) the view for the floor panel.
- __H__: Toggles the heatmaps in the floor panels.
- __1 - "X"__: Toggles (hides or shows) the user corresponding to the number (1 = 0, 2 = 1, ...). "X" is the max number
of users.

## Known Problems

* error message: 'Can't seek to a negative time in a video.'
  - body-tracking data timestamps start before video data start_time
  - __solution:__ just remove the first couple of (hundred) lines in the body tracking file (this is less than a minute of data and is hence just setup moving around information that can be removed)