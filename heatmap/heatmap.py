# -*- coding: utf-8 -*-
"""
    :py:mod:`heatmap.heatmap` -- Heatmap Interface
    ==============================================

    Provides the :py:mod:`heatmap` package public interface via the
    :py:class:`~heatmap.heatmap.Heatmap`  class.


    .. todo::

        Docs on *extendability*.


    .. todo::

        Research the implemented bbox behaviour. Seems counter-intuitive for
        geo-positioning applications to use
        ``(south-west_latlong, north-east_latlong)`` bounds.

        (As opposed to ``(north-west_latlong, south-east_latlong)``.)


    .. todo::

        When not providing :py:method:`~heatmap.heatmap.Heatmap.heatmap` method
        with area explicitly, it crops output heatmap without taking dotsize
        into account. It would be nice to have an option to include margins for
        dotsize -- thus preserving smooth gradients toward *transparent* around
        the entire image.


    .. todo::

        Update :py:class:`~heatmap.heatmap.Heatmap` interface docstring to
        detail projection used.

        Assuming we're using *Web Mercator* EPSG:3857, that would mean
        :py:method:`~heatmap.heatmap.Heatmap.save_kml` output will overlay
        incorrectly, since it's using the PNG output without converting to
        *geodetic* EPSG:4326.


    .. todo::

        GDAL integration, e.g. using ``gdal_translate`` to re-project heatmap
        and/or generating GeoTIFF output.


"""

import os
import sys
import ctypes
import platform

import colorschemes

from PIL import Image


__all__ = ['Heatmap']


_KML_TPL = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Folder>
    <GroundOverlay>
      <Icon>
        <href>%s</href>
      </Icon>
      <LatLonBox>
        <north>%2.16f</north>
        <south>%2.16f</south>
        <east>%2.16f</east>
        <west>%2.16f</west>
        <rotation>0</rotation>
      </LatLonBox>
    </GroundOverlay>
  </Folder>
</kml>"""


class Heatmap:
    """Create heatmaps from a list of 2D coordinates.

    Heatmap requires the Python Imaging Library and Python 2.5+ for ctypes.

    Coordinates auto-scale to fit within the image dimensions, so if there are
    anomalies or outliers in your dataset, results won't be what you expect. You
    can override the auto-scaling by using the area parameter to specify the
    data bounds.

    The output is a PNG with transparent background, suitable alone or to
    overlay another image or such. You can also save a KML file to use in Google
    Maps if x/y coordinates are lat/long coordinates. Make your own wardriving
    maps or visualize the footprint of your wireless network.

    Most of the magic starts in heatmap(), see below for description of that
    function.
    """

    # TODO: Document libpath usage.
    def __init__(self, libpath=None):

        self.img = None
        # If you're reading this, it's probably because this hacktastic garbage
        # failed. Sorry. I deserve a jab or two via @jjguy.

        self.points = None
        self.dotsize, self.opacity, self.size, self.area, self.override = \
            None, None, None, None, None

        self._schemes = colorschemes.SCHEMES

        if libpath:
            self._heatmap = ctypes.cdll.LoadLibrary(libpath)

        else:
            # Establish the right library name, based on platform and arch.
            # Windows are pre-compiled binaries; Linux machines are compiled
            # during setup.
            self._heatmap = None
            libname = "cHeatmap.so"
            if "cygwin" in platform.system().lower():
                libname = "cHeatmap.dll"
            if "windows" in platform.system().lower():
                libname = "cHeatmap-x86.dll"
                if "64" in platform.architecture()[0]:
                    libname = "cHeatmap-x64.dll"
            # Now rip through everything in sys.path to find 'em. Should be in
            # site-packages or local dir.
            for d in sys.path:
                if os.path.isfile(os.path.join(d, libname)):
                    self._heatmap = ctypes.cdll.LoadLibrary(
                        os.path.join(d, libname))

        if not self._heatmap:
            raise Exception("Heatmap shared library not found in PYTHONPATH.")

    # TODO: Document range for opacity arg.
    def heatmap(self, points, dotsize=150, opacity=128, size=(1024, 1024),
                scheme="classic", area=None):
        """Create PIL heatmap image.

        Tweak the *dotsize* and *opacity* arguments to adjust appearance of the
        resulting heatmap.

        :param list points: list of tuples, where the contents are the *(x, y)*
                            coordinates to plot, e.g.
                            ``[(1, 1), (2, 2), (3, 3)]``
        :param int dotsize: pixel size of a single coordinate in the output
                            image in (defaults to 150 px.)
        :param int opacity: strength of a single coordinate in the output image
        :param tuple size: *(width, height)* 2-tuple for heatmap PNG output
                           (defaults to 1024x1024 px.)
        :param str scheme: name of color scheme to use for output image
                           (defaults to *classic*)
        :param tuple area: bounding box for input *points* -- a
                           *(bottom_left_xy, top_right_xy)* 2-tuple, e.g.
                           ``((-1, -2), (3, 2))``
        :returns PIL.Image: heatmap PNG image

        :raises ValueError: on invalid *scheme* input
        :raises Exception: on heatmap processing failure
        """

        # Store image output args.
        self.dotsize, self.opacity, self.size = dotsize, opacity, size

        self.points = points

        if area is None:
            self.area = (0, 0), (0, 0)
            self.override = 0
        else:
            self.area = area
            self.override = 1

        if scheme not in self.get_scheme_names():
            raise ValueError("Unknown color scheme %r (available schemes: %r)."
                             % (scheme, self.get_scheme_names()))

        arr_points = self._convert_points(points)
        arr_scheme = self._convert_scheme(self._schemes[scheme])
        arr_final_image = self._alloc_output_buffer(size[0], size[1], 4)

        ret = self._heatmap.tx(
            arr_points, len(points) * 2, size[0], size[1], dotsize,
            arr_scheme, arr_final_image, opacity, self.override,
            ctypes.c_float(self.area[0][0]), ctypes.c_float(self.area[0][1]),
            ctypes.c_float(self.area[1][0]), ctypes.c_float(self.area[1][1]))

        if not ret:
            raise Exception("Unexpected error during processing.")

        self.img = Image.frombuffer('RGBA', (self.size[0], self.size[1]),
                                    arr_final_image, 'raw', 'RGBA', 0, 1)
        return self.img

    @staticmethod
    def _alloc_output_buffer(width, height, bands):
        """Return heatmap output buffer.

        :param int width: image width
        :param int height: image height
        :param int bands: image channels, e.g. 4 for RGBA output
        :returns: ctypes.c_ubyte array
        """

        return (ctypes.c_ubyte * (width * height * bands))()

    @staticmethod
    def _convert_points(points):
        """Flatten *pts* list of coordinates and convert into ctypes array.

        :param list points: list of 2-tuples with *(x, y)* coordinates
        :returns: ctypes.c_float array

        :raises TypeError: on invalid/mal-formatted *points* input
        """

        # TODO: Is there a better way to do this??
        flat = []
        for x, y in points:
            flat.extend([x, y])

        # Build array of input points.
        return (ctypes.c_float * (len(points) * 2))(*flat)

    @staticmethod
    def _convert_scheme(scheme):
        """Flatten list of RGB tuples in *scheme* and convert into ctypes array.

        :param list scheme: list of 8-bit RGB 3-tuples for heatmap colorization
        :returns: ctypes.c_int array

        :raises TypeError: on invalid/mal-formatted *scheme* argument
        """

        # TODO: Is there a better way to do this??
        flat = []
        for rgb in scheme:
            if min(rgb) < 0x00 or max(rgb) > 0xFF or len(rgb) != 3:
                raise TypeError("Invalid RGB input %r." % str(rgb))
            flat.extend(rgb)

        return (ctypes.c_int * (len(scheme) * 3))(*flat)

    @staticmethod
    def _create_bbox(points):
        """Walk the list of points and return the max/min x & y coordinates in
        the set as inverted bounding box.

        :returns tuple: *(bottom_left_xy, top_right_xy)* 2-tuple
        """

        min_x, min_y = points[0][0], points[0][1]
        max_x, max_y = min_x, min_y
        for x, y in points:
            min_x, min_y = min(x, min_x), min(y, min_y)
            max_x, max_y = max(x, max_x), max(y, max_y)

        return (min_x, min_y), (max_x, max_y)

    def get_bounds(self):
        """Return heatmap bbox (inverted).

        :returns tuple: *(bottom_left_xy, top_right_xy)* 2-tuple
        """

        if self.override:
            (min_x, min_y), (max_x, max_y) = self.area
        else:
            (min_x, min_y), (max_x, max_y) = self._create_bbox(self.points)

        return (min_x, min_y), (max_x, max_y)

    def save_kml(self, kml_file):
        """Save KML and raster PNG files for use with Google Earth. Assumes x/y
        coordinates are lat/long, and creates an overlay to display the heatmap
        within Google Earth.

        :param str kml_file: KML output filename
        :returns None:
        """

        if self.img is None:
            raise Exception("Must first run heatmap() to generate image file.")

        raster_path = os.path.splitext(kml_file)[0] + ".png"
        self.img.save(raster_path)

        (east, south), (west, north) = self.get_bounds()

        with open(kml_file, 'wb') as output:
            output.write(_KML_TPL % (raster_path, north, south, east, west))

    #: Duplicates :py:method:`~Heatmap.save_kml`, to provide backward
    #: compatibility for versions <= 2.2.1.
    saveKML = save_kml

    def get_scheme_names(self):
        """Return available color schemes.

        :returns list: list of color scheme names
        """

        return self._schemes.keys()

    #: Duplicates :py:method:`~Heatmap.get_scheme_names`, to provide backward
    #: compatibility for versions <= 2.2.1.
    schemes = get_scheme_names
