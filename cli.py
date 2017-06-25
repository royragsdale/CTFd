import click
import requests
import os.path
import json
from bs4 import BeautifulSoup

Conf_dir = os.path.join(os.path.expanduser("~"), ".ctfd")
Instance_path = os.path.join(Conf_dir, "instance.json")


class CTFd_instance:
    session = None
    request = None
    url = None

    def request(self, method, path, data=None):
        """Utility to simplify making API requests to CTFd"""
        if self.session is None:
            self.session = requests.Session()
        endpoint = "{}/{}".format(self.url, path)
        if method == "POST":
            # first make a post request to extract the CSRF nonce
            self.request = self.session.get(endpoint)
            nonce = self.extract_nonce()
            data["nonce"] = nonce
            # actual request to endpoint to take action
            self.request = self.session.post(endpoint, data=data)
        elif method == "GET":
            self.request = self.session.get(endpoint, params=data)

    def extract_nonce(self):
        """Given the result of a GET request to an endpoint extract the returned
        CSRF nonce from the hidden input tag ex:
            <input type="hidden" name="nonce" value="c19d...
        This is required to make POST requests"""
        soup = BeautifulSoup(self.request.text, 'html.parser')
        return soup.find('input', {'name': 'nonce'}).get('value')

    def request_error(self):
        """Given the result of a request, check that the response did not contain
        errors"""
        if self.request.status_code != 200:
            click.echo("HTTP Error Code: {}".format(self.request.status_code))
            return True
        else:
            soup = BeautifulSoup(self.request.text, 'html.parser')
            alert = extract_error_message(soup.find('div', {'role': 'alert'}))
            if alert:
                click.echo("Error Message in HTML: {}".format(alert))
                return True
        return False

    def save(self):
        create_config_if_not_exists()
        save_data = {"url": self.url,
                     "cookies": self.session.cookies.get_dict()}
        save_json(Instance_path, save_data)

    def load(self):
        load_data = load_json(Instance_path)
        self.url = load_data["url"]
        self.session = requests.Session()
        self.session.cookies = requests.utils.add_dict_to_cookiejar(self.session.cookies, load_data["cookies"])


def extract_error_message(div):
    """Parse the HTML of a CTFd admin page and extract the error message if
    there is one, otherwise return None"""
    if div:
        lines = div.text.split("\n")
        if len(lines) >= 3:
            return lines[2].strip()
    else:
        return None

###
# Configuration
###


def check_config_dir():
    """Check if a configuration directory exists"""
    return os.path.isdir(Conf_dir)


def create_config_dir():
    """Ensure a configuration directory exists"""
    try:
        os.mkdir(Conf_dir)
        return check_config_dir()
    except:
        click.echo("Error creating directory: {}".format(Conf_dir))


def create_config_if_not_exists():
    return True if check_config_dir() else create_config_dir()


def save_json(json_path, data):
    try:
        with open(json_path, 'w') as outfile:
            json.dump(data, outfile)
    except:
        click.echo("Error saving json: {}".format(json_path))


def load_json(json_path):
    try:
        with open(json_path) as in_file:
            return json.load(in_file)
    except:
        click.echo("Error loading json: {}".format(json_path))



pass_instance = click.make_pass_decorator(CTFd_instance, ensure=True)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--url', required=True,
              help='CTFd web address, ex: http://localhost:8000')
@click.option('--user', required=True, help='The user to login as.')
@click.option('--password', prompt=True, hide_input=True,
              help='The password to login with. Leave blank for prompt.')
def login(url, user, password):
    """Authenticate to a CTFd interface"""
    ctfd = CTFd_instance()
    ctfd.url = url
    click.echo("Login to  {} as {}".format(url, user))
    data = {"name": user, "password": password}
    ctfd.request("POST", "login", data)
    if ctfd.request_error():
        click.echo("Error logging in")
        exit(-1)
    else:
        ctfd.save()
        click.echo("Sucessful login. Session saved.")


@cli.command()
@pass_instance
def stats(ctfd):
    """Get the statistics from a CTFd instance"""
    ctfd.load()
    ctfd.request("GET", "admin/statistics")
    if ctfd.request_error():
        click.echo("Error getting statistics")
        exit(-1)
    else:
        soup = BeautifulSoup(ctfd.request.text, 'html.parser')
        h3 = soup.find_all('h3')
        for line in h3:
            print line


if __name__ == '__main__':
    cli()
