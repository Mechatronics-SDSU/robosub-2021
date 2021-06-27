import docker
CLIENT = docker.from_env()
import os


class run():
	def __init__(self):
		containers_list = CLIENT.containers.list(all=True)
		if not containers_list:
		    self.container = False
		else:
		    self.container = True	
		self.spawn()
		
		
	def spawn(self):
		if self.container == False:
			CLIENT.containers.run(name="server", command="sleep infinity", image="ubuntu:latest", detach=True)
		os.system('python3 server.py')


if __name__ == "__main__":
	containers_list = CLIENT.containers.list(all=True)
	for cont in containers_list:
		cont.remove(force=True)
	run()
