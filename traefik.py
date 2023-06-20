import yaml
from kubernetes import client, config
import os


class ConfigUpdater:
    def __init__(self, configdir_path, output_dir):
        self.configdir_path = configdir_path
        self.output_dir = output_dir
        self.routes = self.fetch_ingress_routes()
        self.updated = {}

        # delete config.yml if exists
        if os.path.exists(os.path.join(self.output_dir, "config.yml")):
            os.remove(os.path.join(self.output_dir, "config.yml"))

    def fetch_ingress_routes(self) -> list:
        """Fetches all the IngressRoutes from the cluster

        Returns:
            list: list with all the IngressRoutes
        """
        config.load_incluster_config()
        v1 = client.CustomObjectsApi()

        # Fetch all IngressRoutes
        response = v1.list_cluster_custom_object(group="traefik.containo.us", version="v1alpha1", plural="ingressroutes")
        return response.get('items', [])

    def save_config(self, config_file: str, config: dict):
        """Saves the config to the updated dict

        Args:
            config_file (str): the name of the config file
            config (dict): the config to save
        """
        # replace spaces with underscores
        config_file = config_file.replace(" ", "_")
        self.updated[config_file] = config

    def load_static_config(self, config_file: str) -> dict:
        """Loads a config file from the configdir_path. If the file has already a newer version in the updated dict, it will return that version

        Args:
            config_file (str): name of config file

        Returns:
            dict: config of the file
        """
        config_file = config_file.replace(" ", "_")

        # check if config file already in updated
        if config_file in self.updated:
            return self.updated[config_file]
        
        try:
            with open(os.path.join(self.configdir_path, config_file), 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return None
       

    def update_homer_config(self):
        """Updates the Homer configuration based on the IngressRoutes. The annotations are used to update the Homer configuration.
        """

        for ingress_route in self.routes:
            homer_config = self.load_static_config('config.yml')

            new_service = {
                'name': ingress_route['metadata']['annotations'].get('homer/name', ingress_route['metadata'].get('name')),
                'url': ingress_route['spec']['routes'][0]['match'].split("`")[1],
                'logo': ingress_route['metadata']['annotations'].get('homer/logo', 'assets/tools/sample-logo.png'),
                'tag': 'router',
            }

            homer_page = ingress_route['metadata']['annotations'].get('homer/page', None)
            if homer_page:
                # check if page in links
                if "links" not in homer_config:
                    homer_config["links"] = []

                for link in homer_config["links"]:
                    if link["name"] == homer_page:
                        break
                else:
                    homer_config["links"].append({
                        "name": homer_page,
                        "icon": "assets/tools/sample-logo.png",
                        "url": f"#{homer_page.replace(' ', '_')}"
                    })
            
            # save the homer config
            self.save_config('config.yml', homer_config)

            # get the page config
            page = "config.yml"
            page_config = self.load_static_config(f'config.yml')
            if homer_page:
                page = f'{homer_page}.yml'
                page_config = self.load_static_config(f'{homer_page}.yml')
                if not page_config:
                    page_config = {
                        'services': []
                    }

            homer_group = ingress_route['metadata']['annotations'].get('homer/group', ingress_route['metadata']['namespace'])

            # check if group already in services
            group_index = -1
            for i,service in enumerate(page_config['services']):
                if service['name'] == homer_group:
                    group_index = i
                    break
            else:
                page_config['services'].append({
                    'name': homer_group,
                    'items': []
                })

            page_config['services'][group_index]['items'].append(new_service)
            self.save_config(page, page_config)

    def export_config(self):
        """Save the updated dictionary to the output_dir as yaml files
        """
        for config_file, config in self.updated.items():
            with open(os.path.join(self.output_dir, config_file), 'w') as file:
                yaml.dump(config, file)

if __name__ == '__main__':
    configdir_path = os.environ.get('CONFIGDIR_PATH', '.')
    output_dir = os.environ.get('OUTPUT_DIR', '/www/assets')
    updater = ConfigUpdater(configdir_path, output_dir)
    updater.update_homer_config()
    updater.export_config()