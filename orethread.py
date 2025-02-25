import os
import datetime
import random

import orekit
from orekit.pyhelpers import datetime_to_absolutedate, absolutedate_to_datetime
from org.hipparchus.geometry.euclidean.threed import Vector3D
from org.hipparchus.linear import RealMatrix
from org.orekit.propagation import StateCovariance
from org.orekit.frames import FramesFactory
from org.orekit.orbits import PositionAngleType, CartesianOrbit, KeplerianOrbit, CircularOrbit, EquinoctialOrbit, OrbitType
from org.orekit.ssa.metrics import ProbabilityOfCollision 
from org.orekit.ssa.collision.shorttermencounter.probability.twod import Patera2005
from org.orekit.utils import PVCoordinates
from org.orekit.utils import Constants
from org.hipparchus.linear import MatrixUtils
from org.orekit.utils import IERSConventions, PVCoordinates
from org.hipparchus.linear import MatrixUtils
from orekit.pyhelpers import setup_orekit_curdir
from org.orekit.propagation.analytical.tle import TLE, TLEPropagator
from org.orekit.time import TimeScalesFactory, AbsoluteDate
from datetime import datetime, timedelta
from typing import Any

import subprocess
import multiprocessing
import time
import uuid

from dataclasses import dataclass

def _check_collisions(sat_prop, debris_props, current_date, collision_threshold_km):
    current_date = datetime_to_absolutedate(current_date)
    found_collision = False
    current_state = sat_prop.propagate(current_date)
    position = current_state.getPVCoordinates().getPosition()
    positions_debris = [prop.propagate(current_date).getPVCoordinates().getPosition() for prop in debris_props]
    collisions = [pos for pos in positions_debris if Vector3D.distance(position, pos) / 1000 <= collision_threshold_km]
    collision_count = 0
    if len(collisions) > 0:
        print(f"Time: {absolutedate_to_datetime(current_date)} CollisionCount: {len(collisions)} Position: {position}")
        collision_count += len(collisions)
        found_collision = True
    return collision_count

def handle_task_queue(task_queue, result_queue, sat_tle, potential_debris_tles, collision_threshold_km):

    vm = orekit.initVM()
    setup_orekit_curdir()

    sat_tle = TLE(sat_tle[0], sat_tle[1])  # Replace with our sat actual TLE
    potential_debris_tles = [TLE(sat[0], sat[1]) for sat in potential_debris_tles]  # File containing debris TLEs
    
    # Initialize propagators
    sat_propagator = TLEPropagator.selectExtrapolator(sat_tle)
    debris_propagators = [TLEPropagator.selectExtrapolator(tle) for tle in potential_debris_tles]

    random_uuid_str = str(uuid.uuid4())

    job_count = 0
    while True:
        current_date = task_queue.get()
        if current_date is None:
            break
        collisions = _check_collisions(sat_propagator, debris_propagators, current_date, collision_threshold_km)
        if collisions > 0:
            [result_queue.put(current_date) for i in range(0, collisions)]
        job_count += 1
        if job_count % 100 == 0:
            print(f"Thread: {random_uuid_str} has processed {job_count} jobs.", flush=True)