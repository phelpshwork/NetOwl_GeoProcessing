"""MVO to create NetOwl integration GP tool."""

import time
import arcpy
import json
import os
import string
import requests

# from netowlmodels import RDFitem, RDFitemGeo, RDFlinkItem, RDFeventItem, OrgDoc  # NOQA
# import netowlfuncts as nof

# ----------------------------------
#  Models for Netowl link application.
# ----------------------------------


class RDFitem:
    """Model to hold non-geo or ready to geocode items."""

    def __init__(self, rdfid, rdfvalue, timest, orgdoc, ontology, rdflinks=None):  # noqa: E501
        """Docstring."""
        self.id = rdfid
        self.links = [] if rdflinks is None else rdflinks  # list - optional
        self.value = rdfvalue
        self.timest = timest
        self.orgdoc = orgdoc
        self.type = ontology

    def set_head(self, head=""):
        """Docstring."""
        self.head = head

    def set_tail(self, tail=""):
        """Docstring."""
        self.tail = tail


class RDFitemGeo(RDFitem):
    """Model to hold objs with lat/long already assigned."""

    def __init__(self, rdfid, rdfvalue, longt, latt, timest,
                 orgdoc, rdflinks=None):
        """Docstring."""
        self.id = rdfid
        self.links = [] if rdflinks is None else rdflinks  # list - optional
        self.value = rdfvalue
        self.lat = latt
        self.long = longt
        self.timest = timest
        self.orgdoc = orgdoc

    def set_type(self, typeofgeo):
        """Docstring."""
        self.type = typeofgeo

    def set_subtype(self, subtypegeo):
        """Docstring."""
        self.subtype = subtypegeo

    def set_link_details(self, details):
        """Docstring."""
        self.linkdetails = details


class RDFlinkItem():
    """Model to hold link objs."""

    def __init__(self, linkid, fromid, toid, fromvalue, tovalue,
                 fromrole, torole, fromroletype, toroletype, timest):
        """Docstring."""
        self.linkid = linkid
        self.fromid = fromid
        self.toid = toid
        self.fromvalue = fromvalue
        self.tovalue = tovalue
        self.fromrole = fromrole
        self.torole = torole
        self.fromroletype = fromroletype
        self.toroletype = toroletype
        self.timest = timest


class RDFeventItem():
    """Model to hold event objs."""

    def __init__(self, eventvalue, eventid, fromid, toid, fromvalue, tovalue,
                 fromrole, torole, orgdoc, uniquets):
        """Docstring."""
        self.eventvalue = eventvalue
        self.eventid = eventid
        self.fromid = fromid
        self.toid = toid
        self.fromvalue = fromvalue
        self.tovalue = tovalue
        self.fromrole = fromrole
        self.torole = torole
        self.orgdoc = orgdoc
        self.timest = uniquets


class OrgDoc():
    """Model to maintain org docs written to graph."""

    def __init__(self, orgdoc):
        """Docstring."""
        self.orgdoc = orgdoc

# ----------------------------------
#  Functions for Netowl link application.
# ----------------------------------


def cleanup_text(intext):
    """Function to remove funky chars."""
    printable = set(string.printable)
    p = ''.join(filter(lambda x: x in printable, intext))
    g = p.replace('"', "")
    return g


def geocode_address(address):
    """Use World Geocoder to get XY for one address at a time."""
    querystring = {
        "f": "json",
        "singleLine": address}
    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"  # noqa: E501
    response = requests.request("GET", url, params=querystring)
    p = response.text
    j = json.loads(p)
    location = j['candidates'][0]['location']  # returns first location as X, Y
    return location


def netowl_curl(infile, outpath, outextension):
    """Do James Jones code to query NetOwl API."""
    headers = {
        'accept': 'application/json',  # 'application/rdf+xml',
        'Authorization': 'netowl ff5e6185-5d63-459b-9765-4ebb905affc8',
    }

    if infile.endswith(".txt"):
        headers['Content-Type'] = 'text/plain'
    elif infile.endswith(".pdf"):
        headers['Content-Type'] = 'application/pdf'
    elif infile.endswith(".docx"):
        headers['Content-Type'] = 'application/msword'

    # params = (
    #     ('language', 'english')
    # )

    params = {"language": "english", "text": "", "mentions": ""}

    data = open(infile, 'rb').read()
    response = requests.post('https://api.netowl.com/api/v2/_process',
                             headers=headers, params=params, data=data,
                             verify=False)

    r = response.text
    outpath = outpath
    filename = os.path.split(infile)[1]
    if os.path.exists(outpath) is False:
        os.mkdir(outpath, mode=0o777, )
    outfile = os.path.join(outpath, filename + outextension)
    open(outfile, "w", encoding="utf-8").write(r)


def make_link_list(linklist):
    """Turn linklist into string."""
    l = ""
    for u in linklist:
        l = l + " " + u
        # check size isn't bigger than 255
    o = l[1:len(l)]
    if len(o) > 255:
        o = o[:254]
    return o  # l[1:len(l)]


def create_dict_for_json(objs, listvalues):
    """Write to data dictionary for json insertion."""
    datadict = {}
    i = 0

    while i < len(listvalues):
        d = {listvalues[i]: objs[i]}
        datadict.update(d)
        i = i + 1

    return datadict


def get_head(text, headpos, numchars):
    """Return text before start of entity."""
    wheretostart = headpos - numchars
    if wheretostart < 0:
        wheretostart = 0
    thehead = text[wheretostart: headpos]
    return thehead


def get_tail(text, tailpos, numchars):
    """Return text at end of entity."""
    wheretoend = tailpos + numchars
    if wheretoend > len(text):
        wheretoend = len(text)
    thetail = text[tailpos: wheretoend]
    return thetail

# ----------------------------------
#  # vars and setup
# ----------------------------------

# docsPath = r'C:/temp/input'
# rdfOutDir = r'C:/temp/output/'
# wk = arcpy.env.workspace = r"C:\Users\heat3463\Documents\ArcGIS\Projects\Jeff\test.gdb"  # noqa: E501)

wk = arcpy.env.workspace = arcpy.GetParameterAsText(2)
docsPath = arcpy.GetParameterAsText(0)
rdfOutDir = arcpy.GetParameterAsText(1) + r"/"

rdfOutExt = ".json"

# get the docs
docs = []
for root, dirs, files in os.walk(docsPath):
    for f in files:
        filePath = os.path.join(root, f)
        docs.append(filePath)

# build the JSON we work with
for d in docs:
    # nof.netowl_curl(d, rdfOutDir, rdfOutExt)
    netowl_curl(d, rdfOutDir, rdfOutExt)

# create empty lists for objects
rdfobjs = []
rdfobjsGeo = []
linkobjs = []
eventobjs = []
orgdocs = []

haslinks = False
bigstring = ""  # keeps track of what was sent
numchars = 100  # number of characters to retrieve for head/tail
newhead = ""  # empty string to catch empty head/tail
newtail = ""

if numchars > 255:
    numchars = 254

for j in os.listdir(rdfOutDir):  # go through each file in output dir

    fn = j[:-5]  # original filename to use as attribute
    od = OrgDoc(fn)  # use to create nodes later
    orgdocs.append(od)

    with open(rdfOutDir + j, 'r', encoding="utf-8") as f:
        rdfstring = json.load(f)
        uniquets = str(time.time())  # unique time stamp for each doc
        doc = rdfstring['document'][0]  # gets main part

        if 'text' in doc:
            v = doc['text'][0]
            if 'content' in v:
                bigstring = v['content']

        if 'entity' not in doc:
            print("ERROR: Nothing returned from NetOwl, or other unspecified error.")  # NOQA E501
            break

        ents = (doc['entity'])  # gets all entities in doc

# ----------------------------------
#       Build entities objects
# ----------------------------------
        for e in ents:

            # gather data from each entity
            # rdfvalue = nof.cleanup_text(e['value'])  # value (ie name)
            rdfvalue = cleanup_text(e['value'])  # value (ie name)
            rdfid = e['id']
            rdfid = rdfid + str(uniquets)  # unique to each entity

            # test for geo (decide which type of obj to make - geo or non-geo)
            if 'geodetic' in e:

                if 'link-ref' in e:
                    refrels = []
                    linkdescs = []
                    haslinks = True
                    for k in e['link-ref']:  # every link-ref per entity
                        refrels.append(k['idref'])  # keep these - all references  # noqa: E501
                        if 'role-type' in k:  # test the role type is source  # noqa: E501
                            if k['role-type'] == "source":
                                linkdesc = rdfvalue + " is a " + k['role'] + " in " + k['entity-arg'][0]['value']  # noqa: E501
                                linkdescs.append(linkdesc)
                            else:
                                linkdescs.append("This item has parent links but no children")  # noqa: E501
                else:
                    haslinks = False

                if 'entity-ref' in e:
                    isGeo = False  # already plotted, relegate to rdfobj list  # noqa: E501
                else:
                    lat = float(e['geodetic']['latitude'])
                    longg = float(e['geodetic']['longitude'])
                    isGeo = True

            else:
                isGeo = False

            # check for addresses
            if e['ontology'] == "entity:address:mail":
                address = e['value']
                # location = nof.geocode_address(address)  # returns x,y
                location = geocode_address(address)  # returns x,y
                isGeo = True
                # set lat long
                lat = location['y']
                longg = location['x']
                # check for links
                if 'link-ref' in e:
                    refrels = []
                    linkdescs = []
                    haslinks = True
                    for k in e['link-ref']:  # every link-ref per entity
                        refrels.append(k['idref'])  # keep these - all references  # noqa: E501
                        if 'role-type' in k:  # test the role type is source  # noqa: E501
                            if k['role-type'] == "source":
                                linkdesc = rdfvalue + " is a " + k['role'] + " in " + k['entity-arg'][0]['value']  # noqa: E501
                                linkdescs.append(linkdesc)
                            else:
                                linkdescs.append("This item has parent links but no children")  # noqa: E501
                else:
                    haslinks = False

            # set up head and tail
            if 'entity-mention' in e:
                em = e['entity-mention'][0]
                if 'head' in em:
                    newhead = get_head(bigstring, int(em['head']), numchars)
                if 'tail' in em:
                    newtail = get_tail(bigstring, int(em['tail']), numchars)

            # build the objects
            if isGeo:

                if haslinks:
                    # add refrels to new obj
                    rdfobj = RDFitemGeo(rdfid, rdfvalue, longg, lat, uniquets, fn,  # noqa: E501
                                        refrels)
                    ld = str(linkdescs)
                    if len(ld) > 255:
                        ld = ld[:254]  # shorten long ones
                    rdfobj.set_link_details(ld)
                else:
                    rdfobj = RDFitemGeo(rdfid, rdfvalue, longg, lat, uniquets, fn)  # noqa: E501
                    rdfobj.set_link_details("No links for this point")

                # set type for symbology
                rdfobj.set_type("placename")  # default
                rdfobj.set_subtype("unknown")  # default
                if e['ontology'] == "entity:place:city":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("city")
                if e['ontology'] == "entity:place:country":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("country")
                if e['ontology'] == "entity:place:province":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("province")
                if e['ontology'] == "entity:place:continent":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("continent")
                if e['ontology'] == "entity:numeric:coordinate:mgrs":
                    rdfobj.set_type("coordinate")
                    rdfobj.set_subtype("MGRS")
                if e['ontology'] == "entity:numeric:coordinate:latlong":  # noqa: E501
                    rdfobj.set_type("coordinate")
                    rdfobj.set_subtype("latlong")
                if e['ontology'] == "entity:address:mail":
                    rdfobj.set_type("address")
                    rdfobj.set_subtype("mail")
                if e['ontology'] == "entity:place:other":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("descriptor")
                if e['ontology'] == "entity:place:landform":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("landform")
                if e['ontology'] == "entity:organization:facility":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("facility")
                if e['ontology'] == "entity:place:water":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("water")
                if e['ontology'] == "entity:place:county":
                    rdfobj.set_type("placename")
                    rdfobj.set_subtype("county")

                rdfobj.set_head(newhead)
                rdfobj.set_tail(newtail)

                rdfobjsGeo.append(rdfobj)

            else:  # not geo
                ontology = e['ontology']
                if haslinks:
                    rdfobj = RDFitem(rdfid, rdfvalue, uniquets, fn, ontology, refrels)  # noqa: E501
                else:  # has neither links nor address
                    rdfobj = RDFitem(rdfid, rdfvalue, uniquets, fn, ontology)

                rdfobj.set_head(newhead)
                rdfobj.set_tail(newtail)

                rdfobjs.append(rdfobj)

# ----------------------------------
#        Build links objects
# ----------------------------------

        if 'link' in doc:
            linksys = (doc['link'])
            for l in linksys:
                linkid = l['id'] + str(uniquets)
                if 'entity-arg' in l:
                    fromid = l['entity-arg'][0]['idref'] + str(uniquets)
                    toid = l['entity-arg'][1]['idref'] + str(uniquets)
                    fromvalue = l['entity-arg'][0]['value']
                    tovalue = l['entity-arg'][1]['value']
                    fromrole = l['entity-arg'][0]['role']
                    torole = l['entity-arg'][1]['role']
                    fromroletype = l['entity-arg'][0]['role-type']
                    toroletype = l['entity-arg'][1]['role-type']
                # build link objects
                linkobj = RDFlinkItem(linkid, fromid, toid, fromvalue, tovalue,
                                      fromrole, torole, fromroletype,
                                      toroletype, uniquets)
                linkobjs.append(linkobj)

# ----------------------------------
#        Build events objects
# ----------------------------------

        if 'event' in doc:
            events = doc['event']
            for e in events:
                evid = e['id']
                evvalue = e['value']
                if 'entity-arg' in e:
                    fromid = e['entity-arg'][0]['idref'] + str(uniquets)
                    fromvalue = e['entity-arg'][0]['value']
                    fromrole = e['entity-arg'][0]['role']
                    if len(e['entity-arg']) > 1:
                        toid = e['entity-arg'][1]['idref'] + str(uniquets)
                        tovalue = e['entity-arg'][1]['value']
                        torole = e['entity-arg'][1]['role']
                    # if len(e['entity-arg']) > 2:
                        # not sure what to do here - TODO
                    else:
                        toid = None
                        tovalue = None
                        torole = None
                # build link objects
                eventobj = RDFeventItem(evvalue, evid, fromid, toid,
                                        fromvalue, tovalue, fromrole,
                                        torole, fn, uniquets)
                eventobjs.append(eventobj)

# ------------------------------------------------------------
# second part - write to items in ArcGIS Pro
# ------------------------------------------------------------

arcpy.env.workspace = wk
sr = arcpy.SpatialReference(4326)  # TODO: this may not be the correct sr

# ----------------------------------
#         Build featureclass
# # ----------------------------------

fcname = "netowl_output"
# # check to see if fc already exists
if arcpy.Exists(fcname) is False:
    arcpy.CreateFeatureclass_management(wk, fcname, "POINT", spatial_reference=sr)  # NOQA

arcpy.management.AddFields(fcname, [["RDFVALUE", "TEXT", "RDFVALUE", 255],  # NOQA
                                    ["RDFLINKS", 'TEXT', "RDFLINKS", 255],  # NOQA
                                    ['TYPE', 'TEXT', 'TYPE', 50],
                                    ["SUBTYPE", 'TEXT', "SUBTYPE", 50],
                                    ["ORGDOC", 'TEXT', "ORGDOC", 255],
                                    ["UNIQUEID", 'TEXT', "UNIQUEID", 50],
                                    ["LINKDETAILS", 'TEXT', "LINKDETAILS", 255], # NOQA
                                    ["HEAD", 'TEXT', "HEAD", 255],
                                    ["TAIL", 'TEXT', "TAIL", 255]])

entslist = ["RDFVALUE", "RDFLINKS", "TYPE", "SUBTYPE", "ORGDOC", "UNIQUEID", "LINKDETAILS", "HEAD", "TAIL", "SHAPE@XY"]   # noqa: E501

iCur = arcpy.da.InsertCursor(fcname, entslist)

tups = {}  # empty dict
datatuple = {}
datatuple[fcname] = []

for r in rdfobjsGeo:

    fieldobjs = []
    # fieldobjs.append(r.id)
    fieldobjs.append(r.value)
    # fieldobjs.append(r.timest)
    ll = make_link_list(r.links)
    fieldobjs.append(ll)
    fieldobjs.append(r.type)
    fieldobjs.append(r.subtype)
    fieldobjs.append(r.orgdoc)
    fieldobjs.append(r.id)  # + str(r.timest))
    fieldobjs.append(r.linkdetails)
    fieldobjs.append(r.head)
    fieldobjs.append(r.tail)
    fieldobjs.append((r.long, r.lat))

    iCur.insertRow(fieldobjs)

    tups = create_dict_for_json(fieldobjs, entslist)
    # tups = nof.create_dict_for_json(fieldobjs, entslist)
    datatuple[fcname].append(tups)

del iCur

# ----------------------------------
#   Build non-geo entities table
# ----------------------------------

nongeotablename = "netowl_entities"

if arcpy.Exists(nongeotablename) is False:
    arcpy.CreateTable_management(wk, nongeotablename)  # noqa: E501

arcpy.management.AddFields(nongeotablename, [["RDFVALUE", "TEXT", "RDFVALUE", 255],  # NOQA
                                ["RDFLINKS", 'TEXT', "RDFLINKS", 255],  # NOQA
                                ["ORGDOC", 'TEXT', "ORGDOC", 255],
                                ["UNIQUEID", 'TEXT', "UNIQUEID", 50],
                                ['TYPE', 'TEXT', 'TYPE', 50],
                                ["HEAD", 'TEXT', "HEAD", 255],
                                ["TAIL", 'TEXT', "TAIL", 255]])

listvalues = ["RDFVALUE", "RDFLINKS", "ORGDOC", "UNIQUEID", "TYPE", "HEAD", "TAIL"]  # noqa: E501

iCur_links = arcpy.da.InsertCursor(nongeotablename, listvalues)  # noqa: E501

tups = {}  # empty dict
datatuple = {}
datatuple[nongeotablename] = []

for d in rdfobjs:  # used for tables in ArcGIS Pro

    fieldobjs = []
    fieldobjs.append(d.value)
    ll = make_link_list(d.links)
    # ll = nof.make_link_list(d.links)
    fieldobjs.append(ll)
    fieldobjs.append(d.orgdoc)
    fieldobjs.append(d.id)
    fieldobjs.append(d.type)
    fieldobjs.append(d.head)
    fieldobjs.append(d.tail)
    iCur_links.insertRow(fieldobjs)

    # tups = nof.create_dict_for_json(fieldobjs, listvalues)
    tups = create_dict_for_json(fieldobjs, listvalues)
    datatuple[nongeotablename].append(tups)

del iCur_links

# ----------------------------------
#   Build relationship links table
# ----------------------------------

linktablename = "netowl_links"

tups = {}  # empty dict
datatuple = {}
datatuple[linktablename] = []

if arcpy.Exists(linktablename) is False:
    arcpy.CreateTable_management(wk, linktablename)

arcpy.management.AddFields(linktablename, [["NAME", "TEXT", "NAME", 255],  # NOQA
                            ["LINKID", "TEXT", "LINKID", 50],  # NOQA
                            ["FROMID", 'TEXT', "FROMID", 50],
                            ["TOID", 'TEXT', "TOID", 50],
                            ["FROMVALUE", 'TEXT', "FROMVALUE", 255],
                            ["TOVALUE", 'TEXT', "TOVALUE", 255],
                            ["FROMROLE", 'TEXT', "FROMROLE", 255],
                            ["TOROLE", 'TEXT', "TOROLE", 255],
                            ["FROMROLETYPE", 'TEXT', "FROMROLETYPE", 255],
                            ["TOROLETYPE", 'TEXT', "TOROLETYPE", 255]])  # NOQA

linkslinks = ["NAME", "LINKID", "FROMID", "TOID", "FROMVALUE", "TOVALUE", "FROMROLE", "TOROLE", "FROMROLETYPE", "TOROLETYPE"]  # NOQA 
iCur_links = arcpy.da.InsertCursor(linktablename, linkslinks)

for lo in linkobjs:

    fieldobjs = []
    fieldobjs.append(lo.fromvalue + " to " + lo.tovalue)  # for label
    fieldobjs.append(lo.linkid)  # + str(lo.timest))
    fieldobjs.append(lo.fromid)  # + str(lo.timest))
    fieldobjs.append(lo.toid)  # + str(lo.timest))
    fieldobjs.append(lo.fromvalue)
    fieldobjs.append(lo.tovalue)
    fieldobjs.append(lo.fromrole)
    fieldobjs.append(lo.torole)
    fieldobjs.append(lo.fromroletype)
    fieldobjs.append(lo.toroletype)
    # fieldobjs.append(lo.timest)

    iCur_links.insertRow(fieldobjs)

    tups = create_dict_for_json(fieldobjs, linkslinks)
    datatuple[linktablename].append(tups)

del iCur_links

# ----------------------------------
#         Build events table
# ----------------------------------

eventtablename = "netowl_events"
if arcpy.Exists(eventtablename) is False:
    # arcpy.CreateTable_management(wk, eventtablename, "netowl_template_events")  # noqa: E501
    arcpy.CreateTable_management(wk, eventtablename)  # noqa: E501

arcpy.management.AddFields(eventtablename, [["NAME", "TEXT", "NAME", 255],  # NOQA
                            ["LINKID", "TEXT", "LINKID", 50],  # NOQA
                            ["FROMID", 'TEXT', "FROMID", 50],
                            ["TOID", 'TEXT', "TOID", 50],
                            ["FROMVALUE", 'TEXT', "FROMVALUE", 255],
                            ["TOVALUE", 'TEXT', "TOVALUE", 255],
                            ["FROMROLE", 'TEXT', "FROMROLE", 255],
                            ["TOROLE", 'TEXT', "TOROLE", 255],
                            ["ORGDOC", 'TEXT', "ORGDOC", 255],
                            ["EVENTVALUE", 'TEXT', "EVENTVALUE", 255]])  # NOQA      

tups = {}  # empty dict
datatuple = {}
datatuple[eventtablename] = []

eventsfields = ["NAME", "LINKID", "FROMID", "TOID", "FROMVALUE", "TOVALUE", "FROMROLE", "TOROLE", "ORGDOC", "EVENTVALUE"]  # noqa: E501

iCur_events = arcpy.da.InsertCursor(eventtablename, eventsfields)  # noqa: E501

for ev in eventobjs:

    fieldobjs = []
    if ev.tovalue is not None:
        fieldobjs.append(ev.fromvalue + " " + ev.eventvalue + " " + ev.tovalue)  # for labeling # NOQA
    else:
        fieldobjs.append(ev.fromvalue + " " + ev.eventvalue)
    fieldobjs.append(ev.eventid + str(ev.timest))
    fieldobjs.append(ev.fromid)
    if ev.toid is not None:  # account for events with no relationships
        fieldobjs.append(ev.toid)
    else:
        fieldobjs.append("None")
    if len(ev.fromvalue) > 100:
        p = ev.fromvalue[:99]  # shorten long ones
        fieldobjs.append(p)
    else:
        fieldobjs.append(ev.fromvalue)
    fieldobjs.append(ev.tovalue)
    fieldobjs.append(ev.fromrole)
    fieldobjs.append(ev.torole)
    fieldobjs.append(ev.orgdoc)
    fieldobjs.append(ev.eventvalue)

    iCur_events.insertRow(fieldobjs)

    tups = create_dict_for_json(fieldobjs, eventsfields)
    # tups = nof.create_dict_for_json(fieldobjs, eventsfields)
    datatuple[eventtablename].append(tups)

del iCur_events
