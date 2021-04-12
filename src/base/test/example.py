import docker
host = docker.from_env()

fullsystem-img = host.images.build(path=".",
                         tag="example-buld",
                         rm=True)


