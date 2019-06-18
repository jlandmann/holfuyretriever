import os
import schedule
import time
import logging
import datetime as dt
import urllib.request
from itertools import product

# internals
import utils

# Logging options
logging.basicConfig(format='%(asctime)s: %(name)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
# Module logger
log = logging.getLogger(__name__)
log.setLevel('DEBUG')

# static
holfuy_dyn_url = r'https://holfuy.com/dynamic/camsave/s{}/{}_{}.jpg'

# SETTINGS
# local settings
save_dir = 'c:\\users\\johannes\\desktop\\holfuy_test'
backup_dir = 'c:\\users\\johannes\\desktop\\holfuy_test_backup'

# remote settings
stations = [551, 1003]  # station numbers as integers


def retrieve_last(station_list):
    now = dt.datetime.now()
    last_img_record_time = now - dt.timedelta(minutes=now.minute % 10,
                                              seconds=now.second,
                                              microseconds=now.microsecond)

    # images usually delivered at minute 11, 21, 31...
    last_img_time = last_img_record_time + dt.timedelta(minutes=1)
    date_str = last_img_time.strftime('%Y-%m-%d')
    time_str = last_img_time.strftime('%H:%M')

    wait_list = []
    for s in station_list:
        url = holfuy_dyn_url.format(str(s), date_str, time_str)
        log.info('Trying {}...'.format(url))

        # no colon allowed in Windows filename
        save_path = os.path.join(save_dir, str(s),
                                 url.split('/')[-1].replace(':', '-'))

        try:
            urllib.request.urlretrieve(url, save_path, None)
            log.info('Successfully retrieved {}.'.format(url))
        except:
            wait_list.append(s)

    if wait_list:
        # determine how long we should wait
        wait = max(((last_img_record_time + dt.timedelta(minutes=10)) -
                    dt.datetime.now()).seconds - 10, 0)  # some margin
        log.warning('Waiting {} seconds...'.format(str(wait)))
        time.sleep(wait)
        # eight should be enough by far
        for st in wait_list:
            success = False
            for md in [0, 1, -1, 2, 3, 4, 5, 6, 7, 8]:
                try_time = last_img_time + dt.timedelta(minutes=md)
                date_str = try_time.strftime('%Y-%m-%d')
                time_str = try_time.strftime('%H:%M')
                url = holfuy_dyn_url.format(str(st), date_str, time_str)
                save_path = os.path.join(save_dir, str(st),
                                         url.split('/')[-1].replace(':', '-'))
                try:
                    urllib.request.urlretrieve(url, save_path, None)
                    log.info('Successfully retrieved {}.'.format(url))
                    success = True
                    break
                except:
                    continue
            if success is False:
                log.warning(
                    'Image for station {} on {} could not be retrieved.'.format(
                        str(st),
                        last_img_record_time.strftime('%Y-%m-%d %H:%M')))


def setup_tasks():
    """Stuff that needs to be done when running the first time."""

    if not os.path.exists(save_dir):
        os.mkdir(save_dir)

    for s in stations:
        s_dir = os.path.join(save_dir, str(s))
        if not os.path.exists(s_dir):
            os.mkdir(s_dir)


@utils.retry(tries=7, exceptions=Exception, log_to=log)
def ten_minute_tasks():
    """Get the images operationally."""

    retrieve_last(stations)


def daily_tasks():
    """ Do daily mop-up operations"""

    # todo: retrieve missing images: getting list from Holfuy API not possible

    # if given, copy to a backup directory
    if backup_dir:
        try:
            utils.custom_copytree(save_dir, backup_dir)
        except (WindowsError, RuntimeError, PermissionError):
            log.warning('Backup to directory {} did not work. No retry attempt'
                        ' has been made.')


if __name__ == '__main__':
    setup_tasks()
    ten_minute_tasks()

    # set up jobs
    step = 10  # every x minutes
    for minute in range(2, 62, step):
        t = ":{minute:02d}".format(minute=minute)
        schedule.every().hour.at(t).do(ten_minute_tasks).tag('10min_tasks')
    # when the sun is set for sure
    schedule.every().day.at("23:59").do(daily_tasks).tag('daily-tasks')

    # run jobs
    while True:
        schedule.run_pending()
        time.sleep(1)
