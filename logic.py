import threading
import time
from uuid import uuid4

from flask import Flask, Response, request
from sendblue import Sendblue

from dbs.mongo import mongo_read, mongo_upsert

# from flask_socketio import emit

# from application import socketio

MAX_WAIT_TIME_SECS = 5
