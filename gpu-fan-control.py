#!/usr/bin/env python

import subprocess
import time
from xml.etree import ElementTree

FAN_BASE_PATH = '/sys/class/hwmon/hwmon1'
GPU_FAN_ENABLE = f'{FAN_BASE_PATH}/pwm3_enable'
GPU_FAN_SPEED_CONTROL = f'{FAN_BASE_PATH}/pwm3'
UPDATE_INTERVAL_MS = 1000
AVERAGE_SAMPLE_COUNT = 3

FAN_CURVE = (
    (40, 10),
    (60, 30),
    (80, 70),
    (90, 100),
)


def get_gpu_temp():
    subproc_result = subprocess.run(
        ['nvidia-smi', '--query', '--xml-format'],
        capture_output=True,
        encoding='UTF-8',
        check=True
    )

    et = ElementTree.fromstring(subproc_result.stdout)
    temp = int(et.find('./gpu/temperature/gpu_temp').text.split(' ')[0])
    return temp


def interpolate(temp, last_less, first_greater):
    location = (temp - last_less[0]) / (first_greater[0] - last_less[0])
    return location * (first_greater[1] - last_less[1]) + last_less[1]


last_gpu_temps = []


def get_speed_for_current_gpu_temp():
    temp = get_gpu_temp()
    global last_gpu_temps
    last_gpu_temps.append(temp)
    if len(last_gpu_temps) > AVERAGE_SAMPLE_COUNT:
        last_gpu_temps = last_gpu_temps[-AVERAGE_SAMPLE_COUNT:]

    temp = sum(last_gpu_temps) / len(last_gpu_temps)

    if temp < FAN_CURVE[0][0]:
        return FAN_CURVE[0][1]

    if temp > FAN_CURVE[-1][0]:
        return FAN_CURVE[-1][1]

    for entry in FAN_CURVE:
        if entry[0] == temp:
            return entry[1]
        elif entry[0] < temp:
            last_less = entry
        elif entry[0] > temp:
            first_greater = entry
            break

    return interpolate(temp, last_less, first_greater)


def scale_percentage(percentage):
    return int(percentage / 100 * 255)


def update_fan_speed():
    fan_speed_percent = get_speed_for_current_gpu_temp()
    pwm_value = scale_percentage(fan_speed_percent)

    with open(GPU_FAN_SPEED_CONTROL, 'w') as control_file:
        control_file.write(str(pwm_value))


def init_pwm_control():
    with open(GPU_FAN_ENABLE, 'w') as pwm_enable:
        pwm_enable.write('1')


def main():
    init_pwm_control()

    while True:
        update_fan_speed()
        time.sleep(UPDATE_INTERVAL_MS / 1000)


if __name__ == '__main__':
    main()
