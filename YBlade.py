#Author-Jan Mrázek
#Description-

import math
import sys 
from copy import deepcopy
import numpy as np
from scipy.spatial.transform import Rotation as R
import svgwrite

handlers = []

# Values here in mm
RIB_WIDTH = 4
BEAM_HEIGHT = 6
BEAM_WIDTH = 40
CONNECTION_SIZE = 5
RIB_SPACING = 50
HANDLE = 140
POSTFIX = 10

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

def drawProfile(dwg, profileData, chordLength, twist, threadAxisOffset, zoffset, id):
    pointSet = profilePoints(profileData, chordLength, twist, threadAxisOffset, zoffset)
    spline = dwg.g(id=id, stroke='green', fill='none', stroke_width=0.1)
    points = [(vec[0], vec[1]) for vec in pointSet]
    spline.add(dwg.polyline(points + [points[0]]))
    drawTally(dwg, spline, id, 0.015*chordLength, twist, center=(-0.3*chordLength, -0.04*chordLength))
    vent_hole = dwg.rect(insert=(-0.25*chordLength, -0.01*chordLength), size=(0.02*chordLength, 0.02*chordLength), fill='none', stroke='green', stroke_width=0.1)
    vent_hole.rotate(twist)
    spline.add(vent_hole)
    spline.add(dwg.rect(insert=(-BEAM_WIDTH/2 + CONNECTION_SIZE, -BEAM_HEIGHT/2), size=(BEAM_WIDTH, BEAM_HEIGHT), fill='none', stroke='green', stroke_width=0.1))
    return spline


def drawTally(dwg, spline, n, size, twist, center=[0, 0]):
    if n == 0: return
    x = 0
    last = (0, 0)
    lines = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0], [1, 1]])
    while True:
        curr = min(n, 5)
        if curr == 0: break
        currLines = lines[:curr+1]
        points = (currLines*size + center + [x, 0]).tolist()
        tally = dwg.polyline(points=points, stroke='red')
        tally.rotate(twist)
        spline.add(tally)
        n -= curr
        x += 1.3 * size
    return

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
    g = dwg.g(id='profiles')
    for i, b in enumerate(blade):
        if abs(b.len - prevLen) < 1 and abs(b.twist - prevTwist) < 1 and i != len(blade) - 1:
            continue
        spline = drawProfile(dwg, profiles[b.profile], b.len, b.twist, b.thread, b.offset, i)
        spline.translate(0, i * 100)
        g.add(spline)
    g.translate(100, 100)
    dwg.add(g)
    dwg.save()

    # Create Main Beam
    dwg = svgwrite.Drawing('beam.svg', profile='tiny')
    g = dwg.g(id='beam')
    points = [(0, 0)]
    for i in range(len(blade)):
        points.append((HANDLE + i * RIB_SPACING - RIB_WIDTH/2, 0))
        points.append((HANDLE + i * RIB_SPACING - RIB_WIDTH/2, CONNECTION_SIZE))
        points.append((HANDLE + i * RIB_SPACING + RIB_WIDTH/2, CONNECTION_SIZE))
        points.append((HANDLE + i * RIB_SPACING + RIB_WIDTH/2, 0))
    points.append((HANDLE + (len(blade)-1) * RIB_SPACING + POSTFIX, 0))
    points.append((HANDLE + (len(blade)-1) * RIB_SPACING + POSTFIX, BEAM_WIDTH))
    points.append((0, BEAM_WIDTH))
    points.append((0, 0))
    g.add(dwg.polyline(points, fill='none', stroke='green', stroke_width=1))

    # Create connectors
    points = [(0, 0), (RIB_WIDTH + 6, 0), (RIB_WIDTH + 6, CONNECTION_SIZE), (3, CONNECTION_SIZE), (3, CONNECTION_SIZE + 3), (0, CONNECTION_SIZE + 3), (0, 0)]
    for i in range(len(blade)):
        obj = dwg.polyline(points, fill='none', stroke='green', stroke_width=1)
        obj.translate(20 * i, BEAM_WIDTH + 10)
        g.add(obj)
    dwg.add(g)
    dwg.save()

if __name__ == '__main__':
    main()