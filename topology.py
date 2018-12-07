#!/usr/bin/python3
import json
from routing.router import Router

update_time = 5


def start(topology_path):
    with open(topology_path) as topology_file:
        topology = json.load(topology_file)

    routers = list()
    routers_data = topology.get('routers', [])
    for router in routers_data:
        routers.append(
            Router(router.get('name', ''), update_time, router.get('ports', []))
        )

    for router in routers:
        router.start()

    return routers


def stop(routers):
    for router in routers:
        router.stop()
