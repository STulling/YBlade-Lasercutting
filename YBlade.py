import math
from copy import deepcopy
import numpy as np
from scipy.spatial.transform import Rotation as R
import svgwrite

handlers = []

# Values here in mm
BEAM_HEIGHT = 9
RIB_WIDTH = 3.5
BEAM_WIDTH = 40
CONNECTION_SIZE = 5
HANDLE = 140
POSTFIX = 10
KERF = -0.04

def readProfile(profileFile):
    points = []
    for l in profileFile.readlines()[1:]:
        p = l.split()
        points.append((float(p[0]), float(p[1])))
    return points

class Struct(object): pass

def readBlade(bladeFile):
    sections = []
    for l in bladeFile.readlines()[3:]:
        x = l.split()
        s = Struct()
        s.pos = float(x[0]) * 1000 # Convert to cm
        s.len = float(x[1]) * 1000 # Convert to cm 
        s.twist = float(x[2])
        s.offset = float(x[3]) * 1000 # Convert to cm
        s.thread = float(x[4])
        s.profile = x[5]
        sections.append(s)
    return sections

def findClosest(target, l):
    """
    Find value in l closest target. Return index of such a value
    """
    minVal = l[0]
    minIdx = 0
    for i, e in enumerate(l):
        if abs(target - minVal) > abs(target - e):
            minVal = e
            minIdx = i
    return minIdx

def deduceOffset(blade, profiles):
    positives = list([(x, y) for profile in profiles for x, y in profile if y > 0])
    posIdx = findClosest(blade[0].thread, [x for x, y in positives])
    negatives = list([(x, y) for profile in profiles for x, y in profile if y < 0])
    negIdx = findClosest(blade[0].thread, [x for x, y in negatives])

    mid = (positives[posIdx][1] + negatives[negIdx][1]) / 2

    for b in blade:
        b.offset = -mid * b.len

def profilePoints(profileData, chordLength, twist, threadAxisOffset, zoffset):
    pointSet = []
    for profilePoint in profileData:
        p = np.array([profilePoint[0] * chordLength, profilePoint[1] * chordLength, 0])
        p = p + np.array([-chordLength * threadAxisOffset, zoffset, 0])
        m = R.from_euler('z', math.radians(twist), degrees=False)
        p = m.apply(p)
        pointSet.append(p)
    return pointSet

def drawProfile(dwg, profileData, chordLength, twist, threadAxisOffset, zoffset, id, kerf=0):
    pointSet = profilePoints(profileData, chordLength, twist, threadAxisOffset, zoffset)
    spline = dwg.g(id=id, stroke='green', fill='none')
    points = [(vec[0], vec[1]) for vec in pointSet]
    spline.add(dwg.polyline(points + [points[0]]))
    drawTally(dwg, spline, id, 0.02*chordLength, twist, center=(-0.28*chordLength, -0.04*chordLength))
    vent_hole = dwg.rect(insert=(0.33*chordLength, -0.01*chordLength), size=(0.02*chordLength, 0.02*chordLength), fill='none', stroke='green')
    vent_hole.rotate(twist)
    spline.add(vent_hole)
    spline.add(dwg.rect(insert=(-BEAM_WIDTH/2 + CONNECTION_SIZE - 0.5*kerf, -BEAM_HEIGHT/2 - 0.5*kerf), size=(BEAM_WIDTH + kerf, BEAM_HEIGHT + kerf), fill='none', stroke='green'))
    return spline


def drawTally(dwg, spline, n, size, twist, center=[0, 0]):
    if n == 0: return
    x = 0
    y = 0
    lines = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0], [1, 1]])
    amount = -1
    while True:
        curr = min(n, 5)
        if curr == 0: break
        amount+=1
        currLines = lines[:curr+1]
        points = (currLines*size + center + [x, y]).tolist()
        tally = dwg.polyline(points=points, stroke='red', stroke_width=0.2)
        tally.rotate(twist)
        spline.add(tally)
        n -= curr
        x += 1.4 * size
        if amount % 4 == 3:
            x = 0
            y += 1.4 * size
    return

def drawBeam(dwg, blades):
    g = dwg.g(id='beam')
    x = HANDLE
    y = 0
    points = [(0, BEAM_WIDTH), (0, 0)]
    prev = 0
    bladez = deepcopy(blades)
    while len(bladez) > 0:
        b = bladez.pop(0)
        diff = b.pos - prev
        prev = b.pos
        if x + diff - RIB_WIDTH/2 < 800:
            x += diff - RIB_WIDTH/2
            points.append((x, y))
            y += CONNECTION_SIZE
            points.append((x, y))
            x += RIB_WIDTH  
            points.append((x, y))
            y -= CONNECTION_SIZE
            points.append((x, y))
        else:
            # first part of dovetail
            half = (diff - RIB_WIDTH/2) - 20
            x += 20
            points.append((x, y))
            y += BEAM_WIDTH/3
            points.append((x, y))
            x -= BEAM_WIDTH
            y -= BEAM_WIDTH/6
            points.append((x, y))
            y += BEAM_WIDTH * 2/3
            points.append((x, y))
            x += BEAM_WIDTH
            y -= BEAM_WIDTH/6
            points.append((x, y))
            y += BEAM_WIDTH/3
            points.append((x, y))
            x = 0
            points.append((x, y))
            y -= BEAM_WIDTH
            points.append((x, y))
            g.add(dwg.polyline(points, fill='none', stroke='green', stroke_width=1))

            # second part of dovetail
            y += 10 + BEAM_WIDTH*2
            points = [(x, y)]
            y -= BEAM_WIDTH/3
            points.append((x, y))
            x -= BEAM_WIDTH
            y += BEAM_WIDTH/6
            points.append((x, y))
            y -= BEAM_WIDTH  * 2/3
            points.append((x, y))
            x += BEAM_WIDTH
            y += BEAM_WIDTH/6
            points.append((x, y))
            y -= BEAM_WIDTH/3
            points.append((x, y))
            x += half
            points.append((x, y))
            y += CONNECTION_SIZE
            points.append((x, y))
            x += RIB_WIDTH  
            points.append((x, y))
            y -= CONNECTION_SIZE
            points.append((x, y))

    x += POSTFIX
    points.append((x, y))
    y += BEAM_WIDTH
    points.append((x, y))
    x = 0
    points.append((x, y))
    g.add(dwg.polyline(points, fill='none', stroke='green', stroke_width=1))
    return g

def main(): 
    # Create Ribs
    dwg = svgwrite.Drawing('ribs.svg', profile='tiny')
    with open("bladeExample2/Bladetable.txt") as f:
        blade = readBlade(f)

    profileNames = [x.profile for x in blade]
    profiles = {}
    for profileName in profileNames:
        with open(f"bladeExample2/{profileName}.dat") as f:
            profileData = readProfile(f)
            profiles[profileName] = profileData
        
    deduceOffset(blade, profiles.values())

    prevLen = -1000
    prevTwist = -1000
    j = -200
    g = dwg.g(id='profiles')
    for i, b in enumerate(blade):
        if i % 5 == 0:
            j += 300
        if abs(b.len - prevLen) < 1 and abs(b.twist - prevTwist) < 1 and i != len(blade) - 1:
            continue
        spline = drawProfile(dwg, profiles[b.profile], b.len, b.twist, b.thread, b.offset, i)
        spline.translate(j, i % 5 * 100)
        g.add(spline)
    g.translate(100, 100)
    dwg.add(g)
    dwg.save()

    # Create Main Beam
    dwg = svgwrite.Drawing('beam.svg', profile='tiny')
    beamgroup = drawBeam(dwg, blade)
    beamgroup.translate(50, 20)
    #dwg.add(beamgroup)

    # Create connectors
    g = dwg.g(id='connectors')
    points = [(0, 0), (RIB_WIDTH + 6, 0), (RIB_WIDTH + 6, CONNECTION_SIZE - 20*KERF), (3, CONNECTION_SIZE - 20*KERF), (3, CONNECTION_SIZE + 3), (0, CONNECTION_SIZE + 3), (0, 0)]
    for i in range(len(blade)):
        obj = dwg.polyline(points, fill='none', stroke='green', stroke_width=1)
        obj.translate(20 * i)
        g.add(obj)
    dwg.add(g)
    dwg.save()

    # Kerf tests
    dwg = svgwrite.Drawing('kerftest.svg', profile='tiny')
    g = dwg.g(id='kerftest')
    b = blade[-1]
    for i in range(11):
        kerf = i * 0.1 - 0.5
        spline = drawProfile(dwg, profiles[b.profile], b.len, b.twist, b.thread, b.offset, i, kerf=kerf)
        spline.translate(40, 40 + i * 20)
        g.add(spline)
    dwg.add(g)
    dwg.save()

    # Test Beam
    dwg = svgwrite.Drawing('testbeam.svg', profile='tiny')
    g = dwg.g(id='beam')
    points = [(0, 0)]
    points.append((100 - RIB_WIDTH/2, 0))
    points.append((100 - RIB_WIDTH/2, CONNECTION_SIZE))
    points.append((100 + RIB_WIDTH/2, CONNECTION_SIZE))
    points.append((100 + RIB_WIDTH/2, 0))
    points.append((120, 0))
    points.append((120, BEAM_WIDTH))
    points.append((0, BEAM_WIDTH))
    points.append((0, 0))
    g.add(dwg.polyline(points, fill='none', stroke='green', stroke_width=1))

    # Add one connector
    points = [(0, 0), (RIB_WIDTH + 6, 0), (RIB_WIDTH + 6, CONNECTION_SIZE - 8*KERF), (3, CONNECTION_SIZE - 8*KERF), (3, CONNECTION_SIZE + 3), (0, CONNECTION_SIZE + 3), (0, 0)]
    obj = dwg.polyline(points, fill='none', stroke='green', stroke_width=1)
    obj.translate(0, BEAM_WIDTH + 10)
    g.add(obj)
    dwg.add(g)
    dwg.save()




if __name__ == '__main__':
    main()