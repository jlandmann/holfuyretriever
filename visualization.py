import utils
import numpy as np
import glob
import xarray as xr
import matplotlib
# Force matplotlib to not use any Xwindows backend.
# needs to be executed before plt import
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import animation
import datetime as dt
import os


class UpdateQuad(object):
    def __init__(self, ax, data):
        self.ax = ax
        self.data = data
        self.quad = data.isel(time=0).plot.imshow(origin='lower',
                                                  vmin=np.nanmin(data.values),
                                                  vmax=np.nanmax(data.values))
        plt.title('Station {}'.format(data.attrs['station']))
        plt.axis('off')
        self.time_text = self.ax.text(.01, .01, self.data.time_str[0],
                                      fontsize=12, color='w',
                                      transform=ax.transAxes)
        plt.tight_layout()

    def init(self):
        self.time_text.set_text(str(self.data.time[0]))
        return self.quad

    def __call__(self, i):
        # data at time i
        ti = self.data.isel(time=i)
        self.quad.set_array(ti.data)
        self.time_text.set_text(self.data.time_str[i].item())
        return self.quad


def make_image_animation(path, save_path=None, speedup='auto'):

    # set the paths to external animation binaries
    utils.set_external_animation_paths()

    # concatenate and work on files
    flist = glob.glob(os.path.join(path, '*.jpg'))
    
    # sometimes they are messed up
    flist = sorted(flist)
    
    if speedup == 'auto':
        speedfac = int(len(flist) / 500)
    else:
        speedfac = speedup
    flist = flist[::speedfac]
    
    dates = [dt.datetime.strptime(os.path.basename(s), '%Y-%m-%d_%H-%M.jpg')
             for s in flist]
    data = [xr.open_rasterio(f) for f in flist]
    try:
        conc = xr.concat(data, dim='time')
    except MemoryError:
        log.info('Experienced MemoryError')
        return
    conc = conc.reindex(time=np.array(dates))
    conc = conc.reindex(y=conc.y[::-1])
    conc['time_str'] = (['time'], [d.strftime('%Y-%m-%d %H:%M') for d in
                                   dates])
    conc = conc.transpose('time', 'y', 'x', 'band')
    conc.attrs['station'] = os.path.basename(path)

    # make actual animation
    fig, ax = plt.subplots()
    
    # try and switch interactive mode off so that the plot does not open
    plt.ioff()
    
    ud = UpdateQuad(ax, conc)
    anim = animation.FuncAnimation(fig, ud, init_func=ud.init,
                                   frames=len(conc.time), blit=False,
                                   interval=2)

    if save_path is not None:
        if save_path.endswith('mp4'):
            anim.save(save_path, writer='ffmpeg', fps=24)
        elif save_path.endswith('gif'):
            anim.save(save_path, writer='imagemagick', fps=24)
        else:  # try generic
            anim.save(save_path, fps=24)


