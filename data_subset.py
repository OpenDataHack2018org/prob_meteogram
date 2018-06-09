import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, HourLocator, DateFormatter, drange
from netCDF4 import Dataset
import datetime

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

# extract data for given location
t = DAT.variables["t2m"][:,:,lati,loni]
u = DAT.variables["u10"][:,:,lati,loni]
v = DAT.variables["v10"][:,:,lati,loni]
lcc = DAT.variables["lcc"][:,:,lati,loni]
mcc = DAT.variables["mcc"][:,:,lati,loni]
hcc = DAT.variables["hcc"][:,:,lati,loni]

## PLOTTING

fig,ax = plt.subplots()

ax.plot(dates,u)

ax.xaxis.set_major_locator(DayLocator())
ax.xaxis.set_minor_locator(HourLocator(np.arange(0, 25, 6)))
ax.xaxis.set_major_formatter(DateFormatter('%m-%d'))

plt.show()
