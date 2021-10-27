import os
import schedule
import time
import logging
import datetime as dt
import urllib.request
from urllib.error import HTTPError
import visualization
import pandas as pd

# internals
import utils

# Logging options
logging.basicConfig(format='%(asctime)s: %(name)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
# Module logger
log = logging.getLogger(__name__)
log.setLevel('INFO')


# parse settings and credentials
cfg = utils.parse_params()
cred = utils.parse_credentials_file()

# fixed settings
holfuy_dyn_url = r'https://holfuy.com/dynamic/camsave/s{}/{}_{}.jpg'
api_dyn_url = 'http://api.holfuy.com/live/?s={}&m=JSON&pw={}&cam=True'


def retrieve_last(station_list):
    now = dt.datetime.now()
    last_img_record_time = now - dt.timedelta(minutes=now.minute % 10,
                                              seconds=now.second,
                                              microseconds=now.microsecond)

    for s in station_list:
        api_url = api_dyn_url.format(str(s), cred['holfuy_api']['password'])
        try:
            json_df = pd.read_json(urllib.request.urlopen(api_url).read())
        except ValueError: # no data in the last 10 minutes
            json_df = pd.read_json(urllib.request.urlopen(api_url).read(),
                                   typ='series')
            if 'error' in json_df:  # No new images in interval
                print('Error for station {}: {}'.format(str(s),
                                                            json_df.error))
                continue
            else:
                try:
                    last_img_full = json_df['last_image'].iloc[0]
                except KeyError:
                    print('Error for station {}'.format(str(s)))

        try:
            last_img_full = json_df['last_image'].iloc[0]
        except KeyError:  # last image older than 24 hrs
            continue

        last_img_mod = dt.datetime.strptime(last_img_full, '%Y-%m-%d %H:%M:%S')
        time_str = last_img_mod.strftime('%H:%M')
        date_str = last_img_mod.strftime('%Y-%m-%d')

        url = holfuy_dyn_url.format(str(s), date_str, time_str)
        log.info('Trying {}...'.format(url))

        # no colon allowed in Windows filename
        save_path = os.path.join(cfg['save_dir'], str(s),
                                 url.split('/')[-1].replace(':', '-'))

        try:
            urllib.request.urlretrieve(url, save_path, None)
            log.info('Successfully retrieved {}.'.format(url))

        except HTTPError:
            # 1 minute diff. between acquisition and arrival on Holfuy server
            last_img_mod -= dt.timedelta(minutes=1)
            time_str = last_img_mod.strftime('%H:%M')
            url = holfuy_dyn_url.format(str(s), date_str, time_str)
            log.info('Trying {}...'.format(url))
            try:
                urllib.request.urlretrieve(url, save_path, None)
                log.info('Successfully retrieved {}.'.format(url))
            except HTTPError:
                log.warning('Image for station {} on {} could not be' 
                             'retrieved'.format(str(s), time_str))

            # set file permissions
            try:
                os.chmod(save_path, 0o2750)
            except:
                print('Setting permissions went wrong...')
        except Exception as e:
            log.error(e)
            log.info(
                'Image for station {} on {} could not be retrieved. Error '
                'message: {}'.format(str(s), last_img_record_time.
                                     strftime('%Y-%m-%d %H:%M'), str(e)))
        try:
            os.chmod(save_path, 0o2750)
        except:
            print('Setting permissions went wrong....')


def setup_tasks():
    """Stuff that needs to be done when running the first time."""

    if not os.path.exists(cfg['save_dir']):
        os.mkdir(cfg['save_dir'])

    for s in cfg['stations']:
        s_dir = os.path.join(cfg['save_dir'], str(s))
        if not os.path.exists(s_dir):
            os.mkdir(s_dir)


@utils.retry(tries=cfg['retrieval_interval_min']-1, exceptions=Exception,
             log_to=log)
def retrieval_interval_tasks():
    """Get the images operationally."""

    retrieve_last(cfg['stations'])


def daily_tasks():
    """ Do daily mop-up operations"""

    utils.set_external_animation_paths()

    # todo: retrieve missing images: getting list from Holfuy API not possible

    # if given, copy to a backup directory
    if cfg['backup_dir']:
        try:
            utils.custom_copytree(cfg['save_dir'], cfg['backup_dir'])
        except (RuntimeError, PermissionError):
            log.warning('Backup to directory {} did not work. No retry attempt'
                        ' has been made.')

    if cfg['copy_to_uni_fribourg']:
        for ufrs in cfg['stations_to_fribourg']:
            try:
                utils.copy_to_ufr_ftp(os.path.join(cfg['save_dir'], str(ufrs)))
            except:
                log.warning('Copy to Fribourg failed....')

    ani_dir = os.path.join(cfg['save_dir'], 'animations')
    for s in cfg['stations']:
        ani_path = os.path.join(ani_dir, '{}.mp4'.format(s))
        if not os.path.exists(os.path.dirname(ani_path)):
            os.mkdir(os.path.dirname(ani_path))
        try: 
            visualization.make_image_animation(path=os.path.join(cfg['save_dir'],
                                                                 str(s)),
                                               save_path=ani_path)
        except ValueError:  # when no files there yet
            pass
            
    utils.copy_to_webpage_dir(ani_dir) 


if __name__ == '__main__':
    setup_tasks()
    retrieval_interval_tasks()
    daily_tasks()

    intv = cfg['retrieval_interval_min']
    # bug in schedule: if "every 10min", exec. gets delayed by the task runtime
    for minute in range(0, 60, intv):
        t = ":{minute:02d}".format(minute=minute)
        schedule.every().hour.at(t).do(retrieval_interval_tasks).tag(
            'retrieval_interval-tasks')
    # when the sun is set for sure
    schedule.every().day.at("00:01").do(daily_tasks).tag('daily-tasks')

    # run jobs
    while True:
        schedule.run_pending()
        time.sleep(1)
