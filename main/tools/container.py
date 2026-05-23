from typing import Any

import docker
import os
import time
from pathlib import Path

from docker.models.containers import Container
from docker.types             import Mount
from docker                   import DockerClient

from smolagents import Tool

def wait_for_startup(container):
    # Poll status until 'running' with a 10-second timeout
    timeout = 10
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        container.reload()  # Clear cache, fetch fresh state
        if container.status == "running":
            break
        time.sleep(0.5)
    
    if container.status != "running":
        return f"Aborting: Container is in '{container.status}' state, expected 'running'."

def restart_if_stopped(container):
    if container.status != "running":
        print(f"Container is '{container.status}'. Starting it...")
        container.start()
        container.reload() 
        print(f"Container state updated to: {container.status}")

def get_clean_container_id(container_id: str):
    if not container_id:
        return "Error: No container ID provided."
        
    clean_id = container_id.strip("<>").replace("Container: ", "").strip()

class ContainerStatus(Tool):
    name = "check_container_status"
    description = "This tool can be used to check the status of a Docker container using its name or ID string."
    output_type = "string"

    def __init__(self, client):
        super().__init__()
        self.client = client

    @property
    def inputs(self):
        return {
            "container_id_or_container": {
                "type": "any",
                "description": "The name or ID string of the Docker container."
            }
        }
    
    def forward(self, container_id_or_container: Any) -> str:
        # Check if framework passed Container instance or container_id string
        if hasattr(container_id_or_container, 'id'):
            clean_id = container_id_or_container.id
        else:
            clean_id = get_clean_container_id(str(container_id_or_container))
        try:
            container = self.client.containers.get(clean_id)
            container.reload()
            return f"Status of container \"{container.name}\": {container.status}"
        except docker.errors.NotFound:
            return f"Error: Container '{clean_id}' could not be found."


class RemoveContainer(Tool):
    name = "remove_container"
    description = "This tool can be used to remove a container using its container name or ID string."
    output_type = "string"

    def __init__(self, client: docker.DockerClient):
        super().__init__()
        self.client = client

    @property
    def inputs(self):
        return {
            "container_id_or_container": {
                "type": "any",
                "description": "The container or ID string of the container to remove (e.g., 'alpine')."
            }
        }
    
    def forward(self, container_id_or_container: Any) -> str:
        try:
            # Clean up framework string wrapping if passed verbatim
            if hasattr(container_id_or_container, 'id'):
                clean_id = container_id_or_container.id
            else:
                clean_id = get_clean_container_id(str(container_id_or_container))       
            container = self.client.containers.get(clean_id)
            container.stop()
            container.remove()
            return f"Container removed: {clean_id}"
        except docker.errors.NotFound:
            return f"Error: Container '{clean_id}' not found."
        except Exception as e:
            return f"Error removing container: {str(e)}"


class InstallUtilities(Tool):
    name = "install_utilities"
    description = "This tool can be used to install utilities like git inside a running container."
    output_type = "string"

    def __init__(self, client: docker.DockerClient):
        super().__init__()
        self.client = client

    @property
    def inputs(self):
        return {
            "container_id_or_container": {
                "type": "any",
                "description": "The container or ID of the container into which utilities should be installed."
            },
            "utility_name": {
                "type": "string",
                "description": "The utility to install. Only the program git is allowed."
            }
        }

    def forward(self, container_id_or_container: str, utility_name: str) -> str:
        try:
            if hasattr(container_id_or_container, 'id'):
                clean_id = container_id_or_container.id
            else:
                clean_id = get_clean_container_id(str(container_id_or_container))       
            container = self.client.containers.get(clean_id)
            wait_for_startup(container)
            exit_code, output = container.exec_run(f"apk add --no-cache {utility_name}")
            if exit_code == 0:
                return f"Utility {utility_name} successfully installed"
            else:
                return f"Installation of {utility} failed."
        except Exception as e:
                    return f"Error executing installation: {str(e)}"


class StartContainer(Tool):
    name = "start_container"
    description = (
        "This tool can be used to start a container with a suitable runtime."
        "The runtime provided by this container can be used for executing and testing code."
        "The tool returns a reference of the container for use in other tools."
    )
    output_type = "object"

    def __init__(self, client: DockerClient):
        super().__init__()
        self.client = client

    @property
    def inputs(self):
        return {
            "image": {
                "type": "string",
                "description": """
                    The Docker image of the runtime to start.
                    You have exactly one Docker image provided to you for spinning up containers.
                    The image is alpine:3.19
                """
            },
            "volume_mounts_data": {
                "type": "array",
                "description": "The volume mounts (list of objects) to store data such as code. Each object specifies a 'target', 'source', and 'type'."
            }
        }
    
    def forward(self, image: str, volume_mounts_data: list[dict]) -> Container:
        """Start a Docker container of the specified image and mount a volume.

        Args:
            image (str): The image to build.
            volume_mounts_data (list[dict]): A list of dictionaries representing Mount volumes.

        Returns:
            dict: A dictionary containing the created Docker container
        """

        # TODO: Maybe the LLM should decide the name itself
        container_name = image.split("/")[-1].split(":")[0]

        try:
            print("Pulling image...")
            self.client.images.pull(image)
        except Exception as e:
            print(f"Pulling image failed: {e}")
        
        # TODO: Simplify logic to determine if the container exists already
        container = None
        try:
            container = self.client.containers.get(container_name)
            restart_if_stopped(container)
            return container
        except docker.errors.NotFound as e:
            print("Container not found, creating new...")

            volumes = {}
            for m in volume_mounts_data:
                volumes[m['source']] = {'bind': m['target'], 'mode': 'rw'}
            
            container = self.client.containers.run(
                image=image,
                name=container_name,
                detach=True,
                tty=True,
                remove=False,
                volumes=volumes                
            )        
            return container


class CreateVolume(Tool):
    name = "create_volume"
    description = (
        "This tool can be used to create a volume."
        "For API compatibility reasons, a list of Mount objects is returned."
        "The list contains only one Mount object which can be used to mount a volume in a container."
        "The volume can be used as the target for data such as cloning a code repository."
        "The tool returns a reference of the volume to use in other tools."
    )
    output_type = "array"

    def __init__(self, source: str, target: str):
        super().__init__()
        self.source = source
        self.target = target

    @property
    def inputs(self):
        return {}
    
    def forward(self):
        return [{'target': self.target, 'source': self.source, 'type': 'bind', 'read_only': False}]




if __name__ == "__main__":
    client = docker.from_env()
    start_container_tool = StartContainer(client)
