import docker
from docker.errors import ContainerError

def run_docker_container(image: str, command: list, volumes: dict, working_dir: str = "/app"):
    client = docker.from_env()
    try:
        return client.containers.run(
            image=image,
            command=command,
            volumes=volumes,
            working_dir=working_dir,
            remove=True
        )
    except ContainerError as e:
        raise RuntimeError(f"Docker failed: {str(e)}")
