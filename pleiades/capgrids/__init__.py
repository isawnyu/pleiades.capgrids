import csv
from itertools import islice
import os

from zope.dublincore.interfaces import ICMFDublinCore
from zope.interface import implements
from zgeo.geographer.interfaces import IGeoreferenced

def mapcols(mapid):
    # "i" and "o" are omitted from barrington atlas columns in maps 100-102
    if int(mapid) in (100, 101, 102):
        return 'abcdefghjklmnpqrstuvwxyz'
    else:
        return 'abcdefghijklmnopqrstuvwxyz'

scales = {'10000': 5.0, '5000': 5.0, '1000': 1.0, '500': 0.5, '150': 0.25}
f = open(os.path.join(os.path.dirname(__file__), 'maps.csv'))
reader = csv.reader(f)

data = {}
for r in islice(reader, 1, None):
    key = r[0]
    value = data.get(key, [])
    value.append(r)
    data[key] = value

def box(mapid, gridsquare=None):
    alphanums = mapcols(mapid)
    if gridsquare is not None and gridsquare.lower() == "inset":
        inset = data[mapid][0][-2]
        return tuple(eval(inset))
    for rec in data[mapid]:
        assert rec[0] == mapid
        try:
            bbox = float(rec[3]), float(rec[5]), float(rec[4]), float(rec[6])
            cols = [alphanums[i] for i in range(
                alphanums.index(rec[7].lower()), 
                alphanums.index(rec[8].lower())+1)]
            rows = [k for k in range(int(rec[9]), int(rec[10])+1)]
            if gridsquare is None:
                return bbox
            a = []
            b = []
            c = []
            d = []
            for gs in gridsquare.split('+'):
                row = int(gs[1:])
                col = gs[0].lower()
                assert row in rows
                assert col in cols
                dx = (bbox[2] - bbox[0])/len(cols)
                dy = (bbox[3] - bbox[1])/len(rows)
                minx = bbox[0] + cols.index(col)*dx
                maxy = bbox[3] - rows.index(row)*dy
                a.append(minx)
                b.append(maxy-dy)
                c.append(minx+dx)
                d.append(maxy)
            return (min(a), min(b), max(c), max(d))
        except AssertionError:
            pass
        except:
            raise
    raise IndexError, "No gridsquare %s in map %s" % (gridsquare, mapid)

def parseURL(url):
    assert url.startswith('http://atlantides.org/capgrids')
    s = url.rstrip('/')
    vals = s.split('/')[4:]
    if len(vals) == 2:
        return vals
    elif len(vals) == 1:
        return vals[0], None
    else:
        raise ValueError, "Invalid map or grid identifier"


class Map(object):

    def __init__(self, rec):
        self.id = rec[0]
        self.title = rec[1]
        self.scale = rec[2]
        alphanums = mapcols(self.id)
        self.cols = [alphanums[i] for i in range(alphanums.index(rec[7].lower()), alphanums.index(rec[8].lower())+1)]
        self.rows = [k for k in range(int(rec[9]), int(rec[10])+1)]
        self._keys = ['%s%s' % (i, j) for j in self.rows for i in self.cols]
        self._items = dict([(k, Grid(self.id, k)) for k in self._keys])
        
        # insets
        try:
            field = eval(rec[11])
            if type(field[0]) in [type(1.0), type(1)]:
                self.insets_bounds = [tuple(field)]
            else:
                self.insets_bounds = [tuple(x) for x in field]
        except SyntaxError:
            self.insets_bounds = []
        except:
            import pdb; pdb.set_trace()
            raise

    def keys(self):
        return self._keys

    def values(self):
        return self._items.values()

    def items(self):
        return self._items

    def __getitem__(self, key):
        return self._items[key]


class Grid(object):
    
    """Context for surfacing grid squares in KML, Atom, JSON
    """
    implements(ICMFDublinCore, IGeoreferenced)
    
    def __init__(self, mapid, gridsquare=None):
        self.mapid = mapid
        self.gridsquare = None
        if gridsquare:
            self.gridsquare = gridsquare.lower()

    def __repr__(self):
        return 'Barrington Atlas map %s, grid square %s' % (
            self.mapid, self.gridsquare.upper())
    
    def _params(self):
        if self.gridsquare:
            return (self.mapid, self.gridsquare)
        else:
            return (self.mapid,)

    @property
    def id(self):
        params = self._params()
        return "http://atlantides.org/capgrids/" + '/'.join(params)
    
    @property
    def bounds(self):
        return box(self.mapid, self.gridsquare)
    
    def Title(self):
        return repr(self)
    
    def Description(self):
        return 'Footprint and attributes of %s' % repr(self)
    
    def Creator(self):
        return 'Classical Atlas Project, edited by R. Talbert'
    
    @property
    def type(self):
        return 'Polygon'
    
    @property
    def coordinates(self):
        l, b, r, t = self.bounds
        return (((l, b), (l, t), (r, t), (r, b), (l, b)),)
    
    @property
    def __geo_interface__(self):
        return dict(type=self.type, coordinates=self.coordinates)
