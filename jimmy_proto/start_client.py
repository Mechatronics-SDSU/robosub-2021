import docker
CLIENT = docker.from_env()
import os


class run():
	def __init__(self):
		self.spawn()
		
		
	def spawn(self):
		CLIENT.containers.run(name="client", command="sleep infinity", image="ubuntu:latest", detach=True)
		os.system('python3 client.py')


if __name__ == "__main__":
	run()
