import falcon
from falcon import HTTP_404
from falcon import HTTP_200
from uuid import uuid4
from json import dumps
from time import time
import traceback
import requests
from collections import defaultdict
from random import choice

# cors
from falcon_cors import CORS
cors = CORS(allow_all_origins=True)
public_cors = CORS(allow_all_origins=True)

available_workers = []
worker_heartbeat = defaultdict(lambda: 0)

def select_worker():
    if len(available_workers) is 0:
        return None
    return choice(available_workers)


class StartUploadHandler:
    cors = public_cors

    def on_get(self, req, resp, size):
        # generate uuid
        guid = uuid4().hex
        # select worker
        worker_hostandport = select_worker()
        if worker_hostandport is None:
            resp.status = HTTP_404
            resp.body = "No workers available"
        else:
            # update load statistics for selected worker
            # inform worker that uploader is coming
            inform_url = "http://%s/upload_notify/%s/%s" % (worker_hostandport,
                                                    guid,
                                                    size)
            requests.put(inform_url)
            # return params
            params = {
                "target_url": worker_hostandport,
                "guid": guid,
                "parameters": {
                    "chunk_size": 10 ** 5
                }
            }
            resp.body = dumps(params)
            resp.status = falcon.HTTP_200


class FinishUploadHandler:
    cors = public_cors

    def on_get(self, req, resp, guid):
        # update load statistics for the worker
        print guid, "finished uploading!"


class WorkersHandler:
    cors = public_cors

    def on_put(self, req, resp, host, port):
        # add worker to those available to be selected for upload
        host_str = "%s:%s" % (host, port)
        if host_str not in available_workers:
            print "host added:", host, port
            available_workers.append(host_str)
        worker_heartbeat[host_str] = time()
        print "%s count is %s" % (host_str, worker_heartbeat[host_str])
        
    
    def on_delete(self, req, resp, host, port):
        # remove worker from possibility of being scheduled
        host_str = "%s:%s" % (host, port)
        if host_str in available_workers:
            print "worker removed: ", host, port
            available_workers.remove(host_str)
        else:
            resp.body = "%s isn't registered" % (host_str)
            resp.status = HTTP_404


api = falcon.API(middleware=[cors.middleware])
api.add_route("/start_upload/{size:int}", StartUploadHandler())
api.add_route("/finish_upload/{guid}", FinishUploadHandler())
api.add_route("/workers/{host}/{port:int}", WorkersHandler())


####################################
####    handle updating workers ####
####################################
import signal
import sys
from json import loads

# open config
config = None
with open("./master_conf.json") as f:
    config = loads(f.read())

host = config["host"]
port = config["port"]
update_workers_time = config["update_workers_seconds"]

print "starting master: ", host, port

def update_workers(signum, frame):
    worker_str = dir(available_workers)
    for worker in available_workers:
        last_heartbeat = worker_heartbeat[worker]
        current_time = time()
        delta_t = current_time - last_heartbeat
        print "checking in on %s -- %s since last heartbeat" % (worker, delta_t)
        if 10.0 < delta_t:
            print "worker timeout: %s" % worker
            available_workers.remove(worker)
        else:
            print "worker OK: %s" % worker

    signal.setitimer(signal.ITIMER_REAL, 1.0)


# start timer
signal.signal(signal.SIGALRM, update_workers)
signal.setitimer(signal.ITIMER_REAL, update_workers_time)