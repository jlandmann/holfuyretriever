import os
import shutil
import time
import re
import glob
from configobj import ConfigObj
from functools import wraps
import matplotlib as mpl
import ftplib
import urllib.request
import platform
import sys
import hashlib
import zipfile
import tempfile
import paramiko as pm


def retry(exceptions, tries=100, delay=60, backoff=1, log_to=None):
    """
    Retry decorator calling the decorated function with an exponential backoff.

    Amended from Python wiki [1]_ and calazan.com [2]_.

    Parameters
    ----------
    exceptions: str or tuple
        The exception to check. May be a tuple of exceptions to check. If just
        `Exception` is provided, it will retry after any Exception.
    tries: int
        Number of times to try (not retry) before giving up. Default: 100.
    delay: int or float
        Initial delay between retries in seconds. Default: 60.
    backoff: int or float
        Backoff multiplier (e.g. value of 2 will double the delay
        each retry). Default: 1 (no increase).
    log_to: logging.logger
        Logger to use. If None, print.

    References
    -------
    .. [1] https://wiki.python.org/moin/PythonDecoratorLibrary#CA-901f7a51642f4dbe152097ab6cc66fef32bc555f_5
    .. [2] https://www.calazan.com/retry-decorator-for-python-3/
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = '{}, Retrying in {} seconds...'.format(e, mdelay)
                    if log_to:
                        log_to.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


def set_external_animation_paths():
    if sys.platform.startswith('win'):
        fpath = os.popen('where ffmpeg').read().split('\n')[0]
        mpath = os.popen('where magick').read().split('\n')[0]
    else:
        fpath = os.popen('which ffmpeg').read().split('\n')[0]
        mpath = os.popen('which convert').read().split('\n')[0]

    mpl.rcParams['animation.ffmpeg_path'] = fpath
    mpl.rcParams['animation.convert_path'] = mpath


def custom_copytree(src, dst, symlinks=False, ignore=None):
    """
    A custom version of shutil.copytree not complaining when the destination
    directory already exists.

    From:
    https://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth

    Parameters
    ----------
    src: str
        Source directory that shall be copied.
    dst: str
        Destination directory that can possibly exist already.
    symlinks: bool
        If True, symbolic links in the source tree are represented as symbolic
        links in the new tree and the metadata of the original links will be
        copied as far as the platform allows; if false or omitted, the contents
        and metadata of the linked files are copied to the new tree. Default:
        False.
    ignore:
        If given, it must be a callable that will receive as its
        arguments the directory being visited by copytree(), and a list of its
        contents, as returned by os.listdir(). These names will then be ignored
        in the copy process. Default: None.
    """
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def parse_params(paramfile='./params.cfg'):
    cfg = ConfigObj(paramfile, file_error=True)

    for p in ['stations', 'stations_to_fribourg']:
        cfg[p] = [int(i) for i in cfg.as_list(p)]

    for p in ['retrieval_interval_min']:
        cfg[p] = cfg.as_int(p)

    for p in ['copy_to_uni_fribourg', 'copy_to_website_dir']:
        cfg[p] = cfg.as_bool(p)

    return cfg


def parse_credentials_file(credfile=None):
    if credfile is None:
        credfile = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                '.credentials')
    cr = ConfigObj(credfile, file_error=True)

    return cr


def copy_to_ufr_ftp(img_dir, credfile=None, user='plainemorte'):
    """
    Copy files to FTP server of University of Fribourg.

    Parameters
    ----------
    credfile: str
        Path to the credentials file (must be parsable as
        configobj.ConfigObj).
    user: str
        User to log in with. Default: 'plainemorte'.
    """
    cr = parse_credentials_file(credfile)

    if user == 'plainemorte':
        client = ftplib.FTP(cr['ufr-ftp']['host'], cr['ufr-ftp']['user'],
                            cr['ufr-ftp']['password'])
        client.login(user=cr['ufr-ftp']['user'],
                     passwd=cr['ufr-ftp']['password'])
    else:
        raise ValueError(
            'No credentials known for Uni Fribourg FTP user {}'.format(user))

    client.cwd('findelen_cambilder')
    imgs = glob.glob(os.path.join(img_dir, '*.jpg'))
    for img in imgs:
        fp = open(img, 'rb')
        client.storbinary('STOR %s' % os.path.basename(img), fp, 1024)


def copy_to_webpage_dir(src_dir, dest_dir=None, file_type=None):
    """
    Copy content from given path to the CRAMPON webpage directory.

    Parameters
    ----------
    src_dir: str
        Source directory containing the file to be copied.
    dest_dir: str
        If given, the directory where to save the files in the webpage tree
        under 'public_html'. Default: None (use
    file_type: str
        File type ending to be copied, e.g. "mp4" for videos. Default: None
        (copy all files).
    """
    if file_type is not None:
        to_put = glob.glob(os.path.join(src_dir, '*' + file_type))
    else:
        to_put = glob.glob(os.path.join(src_dir, '*'))

    client = pm.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(pm.AutoAddPolicy())
    cred = parse_credentials_file()
    # first connect to login.ee.ethz.ch, then ssh to webbi04
    try:
        client.connect(cred['webbi11']['host'], cred['webbi11']['port'],
                       cred['webbi11']['user'], cred['webbi11']['password'])
        _ = client.exec_command(cred['webbi11']['remote_cmd'])

        # now we should be on webbi04
        sftp = client.open_sftp()
        if dest_dir is not None:
            srv_path = './public_html/' + dest_dir
        else:
            srv_path = './public_html/' + os.path.split(src_dir)[1]

        for tp in to_put:
            print(tp, srv_path + '/' + os.path.split(tp)[-1])
            sftp.listdir()
            sftp.put(tp, srv_path + '/' + os.path.split(tp)[-1])
        sftp.close()
        client.close()
    except Exception:
        print('Could not connect to webbi 11')
        pass
