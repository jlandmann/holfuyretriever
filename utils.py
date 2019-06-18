import os
import shutil
import time
from functools import wraps


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
