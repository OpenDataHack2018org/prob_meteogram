import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange
from netCDF4 import Dataset
from matplotlib.ticker import FormatStrFormatter
import datetime
from matplotlib import gridspec

# READ DATA
path = "git/prob_meteogram/data/"
DAT = Dataset(path+"forecast.nc")

# grid
lat = DAT.variables["latitude"][:]
lon = DAT.variables["longitude"][:]
time = DAT.variables["time"][:]

# convert time to datetime objects
datetime0 = datetime.datetime(1900,1,1)
dates = [datetime0 + datetime.timedelta(hours=int(t)) for t in time]

# FUNCTIONS
def find_closest(x,a):
    """ Finds the closest index in x to a given value a."""
    return np.argmin(abs(x-a))

# PICK LOCATION
lat0 = 51.5      # in degrees
lon0 = 0

lati = find_closest(lat,lat0)   # index for given location
loni = find_closest(lon,lon0)
loc = (lat[lati],lon[loni])

# extract data for given location
t = DAT.variables["t2m"][:,:,lati,loni]-273.15
u = DAT.variables["u10"][:,:,lati,loni]
v = DAT.variables["v10"][:,:,lati,loni]
lcc = DAT.variables["lcc"][:,:,lati,loni]
mcc = DAT.variables["mcc"][:,:,lati,loni]
hcc = DAT.variables["hcc"][:,:,lati,loni]


##  axes formatting
def cloud_ax_format(ax,loc):
    #TODO make city automatic?
    ax.set_title("Meteogram London ({:.1f}°N, {:.1f}°E)".format(loc[0],loc[1]),loc="left",fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    
def rain_ax_format(ax):
    ax.set_xticks([])
    ax.set_yticks([])

def temp_ax_format(ax,dates):
    ax.text(0.02,0.94,"sun up/down",fontsize=8,transform=ax.transAxes)
    ax.set_yticks(np.arange(0,30,3))    #TODO make automatic
    ax.set_ylim(4,28)                   #TODO make automatic
    ax.yaxis.set_major_formatter(FormatStrFormatter('%d°C'))
    
    # x axis lims, ticks, labels
    ax.set_xlim(dates[0],dates[-1])
    ax.xaxis.set_minor_locator(HourLocator(np.arange(0, 25, 6)))    # minor
    ax.xaxis.set_minor_formatter(DateFormatter("%Hh"))
    ax.get_xaxis().set_tick_params(which='minor', direction='in',pad=-10,labelsize=6)
    ax.grid(alpha=0.1)
    
    ax.xaxis.set_major_locator(DayLocator())                        # major
    ax.xaxis.set_major_formatter(DateFormatter(" %a\n %d %b"))
    for tick in ax.xaxis.get_majorticklabels():
        tick.set_horizontalalignment("left")
    
    # remove labels at edges
    ax.get_xticklabels()[-1].set_visible(False)
    ax.get_xticklabels(which="minor")[-1].set_visible(False)
    ax.get_xticklabels(which="minor")[0].set_visible(False)
    

# PLOTTING
fig = plt.figure(figsize=(10,4))

# subplots adjust
all_ax = gridspec.GridSpec(3, 1, height_ratios=[1,1,10],hspace=0)
cloud_ax = plt.subplot(all_ax[0])
rain_ax = plt.subplot(all_ax[1])
temp_ax = plt.subplot(all_ax[2])

plt.tight_layout(rect=[0.02,.03,1,0.97])

# do axes formatting
cloud_ax_format(cloud_ax,loc)
rain_ax_format(rain_ax)
temp_ax_format(temp_ax,dates)


temp_ax.plot(dates,t,"C1",lw=0.5)

plt.show()




