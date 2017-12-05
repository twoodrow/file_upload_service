from falcon import HTTP_201
from falcon import HTTP_202
from falcon import HTTP_404
from falcon import API
#import boto3
import uuid
import time
import traceback
import requests

from sets import Set
from collections import defaultdict


# cors
from falcon_cors import CORS
cors = CORS(allow_all_origins=True, allow_all_methods=True)
public_cors = CORS(allow_all_origins=True)

def do_something(guid, data):
    print "GUID", guid
    print "DATA: ", data

# dict for maintaining guids
allowed_guids = Set()
guid_details = {}
guid_files = defaultdict(lambda: "")


class UploadHandler:
    cors = public_cors

    def on_post(self, req, resp, guid):
        # check headers for correct content type?
        if guid in allowed_guids:
            print "adding to file"
            guid_files[guid] += req.stream.read()
            resp.status = HTTP_202
        else:
            print "GUID WAS MISSING: %s" % guid
            resp.status = HTTP_404
            resp.body = "Supplied GUID does not have permission from master."


class MasterNotifyHandler:
    cors = public_cors

    def on_put(self, req, resp, guid, size):
        print "adding guid %s of size %s" % (guid, size)
        allowed_guids.add(guid)
        resp.status = HTTP_201


class FinishUploadHandler:
    cors = public_cors

    def on_get(self, req, resp, guid):
        if guid in allowed_guids:
            print "file received was: %s" % guid_files[guid]
            allowed_guids.discard(guid)
            do_something(guid, guid_files[guid])
            # keep memory small
            del guid_files[guid]
            # notify master that upload is complete
            resp.status = HTTP_201
        else:
            resp.status = HTTP_404
            resp.body = "Supplied GUID does not have permission from master."


api = API(middleware=[cors.middleware])
api.add_route("/upload/{guid:uuid}", UploadHandler())
api.add_route("/upload_finish/{guid:uuid}", FinishUploadHandler())
api.add_route("/upload_notify/{guid:uuid}/{size:int}", MasterNotifyHandler())


####################################
####    handle updating master  ####
####################################
import signal
import sys
from json import loads

# open config
config = None
with open("./worker_conf.json") as f:
    config = loads(f.read())

host = config["host"]
port = config["port"]
update_workers_time = config["update_master_seconds"]

print "starting master: ", host, port

def update_master(signum, frame):
    # update master
    requests.put("http://0.0.0.0:4000/workers/%s/%s" % (host, port))
    signal.setitimer(signal.ITIMER_REAL, update_workers_time)


# start timer
signal.signal(signal.SIGALRM, update_master)
signal.setitimer(signal.ITIMER_REAL, update_workers_time)