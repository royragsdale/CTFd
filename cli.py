import click
import requests
from bs4 import BeautifulSoup

Session = None
Url = None


def request(method, path, data):
    """Utility to simplify making API requests to CTFd"""
    global Session
    if Session is None:
        Session = requests.Session()
    s = Session
    endpoint = "{}/{}".format(Url, path)
    if method == "POST":
        # first make a post request to the endpoint to extract the CSRF nonce
        r = s.get(endpoint)
        nonce = extract_nonce(r)
        data["nonce"] = nonce
        return s.post(endpoint, data=data)
    elif method == "GET":
        return s.get(endpoint, params=data)


def extract_nonce(request):
    """Given the result of a GET request to an endpoint extract the returned
    CSRF nonce from the hidden input tag ex:
        <input type="hidden" name="nonce" value="c19d...
    This is required to make POST requests"""
    soup = BeautifulSoup(request.text, 'html.parser')
    nonce = soup.find('input', {'name': 'nonce'}).get('value')
    return nonce


def extract_error_message(div):
    if div:
        lines = div.text.split("\n")
        if len(lines) >= 3:
            return lines[2].strip()
    else:
        return ""


def request_error(request):
    """Given the result of a request, check that the response did not contain
    errors"""
    if request.status_code != 200:
        click.echo("HTTP Error Code: {}".format(request.status_code))
        return True
    else:
        soup = BeautifulSoup(request.text, 'html.parser')
        alert = extract_error_message(soup.find('div', {'role': 'alert'}))
        if alert:
            click.echo("Error Message in HTML: {}".format(alert))
            return True
    return False


@click.group()
def cli():
    pass


@click.command()
@click.option('--url', help='CTFd web address (including port.')
@click.option('--user', help='The user to login as.')
@click.option('--password', help='The password to login with.')
def login(url, user, password):
    """Authenticate to a CTFd interface"""
    global Url
    Url = url
    click.echo("Login to  {} as {}".format(url, user))
    data = {"name": user, "password": password}
    r = request("POST", "login", data)
    if request_error(r):
        exit(-1)


@click.command()
def status():
    """Get the status of a CTFd instance"""
    click.echo("CTFd Status")


cli.add_command(login)
cli.add_command(status)

if __name__ == '__main__':
    cli()
