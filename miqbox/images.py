import os
import socket

import click
import requests
from bs4 import BeautifulSoup

from miqbox.configuration import Configuration


class Images(Configuration):
    """MiqBox images

    Args:
        stream (str): upstream or downstream
        version (str): build version
        ssl_verify (bool): verify ssl
    """

    def __init__(self, stream="upstream", version=None, ssl_verify=False, **kwargs):
        self.stream = stream
        self.version = version
        self.ssl_verify = ssl_verify
        self.extension = "qc2" if stream == "upstream" else "qcow2"

        super(Images, self).__init__(**kwargs)

    @property
    def repo_link(self):
        """Repository link as per stream and version"""
        repo = self.repositories.get(self.stream).url

        if not repo:
            print(f"repository not set for {self.stream}")
            exit(1)

        if self.stream == "downstream":
            base_version = ".".join(self.version.split(".")[:2])
            repo = f"{repo}/builds/cfme/{base_version}/stable"
        return repo

    def images(self, local=False):
        """Get all available images as per stream and version

        Args:
            local (bool): local or remote

        Returns:
            list: return local images if local else remote
        """
        imgs = []

        if local:
            for img in os.listdir(self.image_path):
                if self.stream == "upstream" and "manageiq" in img and self.version in img:
                    imgs.append(img)
                elif self.stream == "downstream" and self.version in img:
                    imgs.append(img)
        else:
            try:
                page = requests.get(self.repo_link, verify=self.ssl_verify).text
            except (socket.gaierror, requests.exceptions.ConnectionError):
                click.echo("Check Network connection")
                exit(1)

            soup = BeautifulSoup(page, "html.parser")

            for node in soup.find_all("a"):
                img = node.get("href")
                if img and img.endswith(self.extension) and self.version in img:
                    imgs.append(img)
        return imgs

    def download(self, name):
        """Download image with click progress bar

        Args:
            name (str): name of image
        """
        url = f"{self.repo_link}/{name}"
        try:
            r = requests.get(url=url, stream=True)
        except requests.exceptions.ConnectionError:
            print(f"Unable to connect {url}")
            print("Check network connection; try again...")
            exit(1)

        if r.status_code != requests.codes.ok:
            click.echo(f"Unable to connect {self.repo_link}/{name}")
            r.raise_for_status()

        total_size = int(r.headers.get("Content-Length"))
        local_img_path = os.path.join(self.image_path, name)

        with click.progressbar(r.iter_content(1024), length=total_size) as bar, open(
            local_img_path, "wb"
        ) as file:
            for chunk in bar:
                file.write(chunk)
                bar.update(len(chunk))

    def delete(self, name):
        """Delete image

        Args:
            name (str): name of image
        """
        os.remove(os.path.join(self.image_path, name))

    @classmethod
    def instantiate_with_image(cls, image):
        """Instantiate with image name

        Args:
            image (str): name of image
        """
        stream, prov, version, *_ = image.split("-")
        stream = "upstream" if stream == "manageiq" else "downstream"
        return cls(stream=stream, version=version)


@click.command(help="Check available images")
@click.option("-l", "--local", is_flag=True, help="Local images as per stream and version")
@click.option("-r", "--remote", is_flag=True, help="Remote images as per stream and version")
@click.option("-f", "--filter", type=str, help="Filter specific image")
def images(local, remote, filter):
    """Display images"""

    conf = Configuration()

    if remote or local:
        streams = list(conf.repositories.keys())
        stream = click.prompt("stream:", default=streams[0], type=click.Choice(streams))

        versions = conf.repositories.get(stream).versions
        version = click.prompt("Version:", default=versions[-1], type=click.Choice(versions))

        img = Images(stream=stream, version=version)
        images = img.images(local=not remote)
    else:
        images = [img for img in os.listdir(conf.image_path)]

    for img in images:
        if filter:
            click.echo(click.style(img, fg="green")) if filter in img else 0
        else:
            click.echo(click.style(img, fg="green"))


@click.command(help="Download Image")
@click.argument("image_name")
def pull(image_name):
    """Pull image available on remote repository"""

    images = Images.instantiate_with_image(image_name)

    if image_name not in images.images(local=True):
        images = Images.instantiate_with_image(image_name)
        images.download(image_name)

    else:
        click.echo(click.style(f"{image_name} already available", fg="red"))


@click.command(help="Remove local Images")
@click.argument("image_names", nargs=-1)
def rmi(image_names):
    """Remove local images"""

    conf = Configuration()

    for image in image_names:
        if image in os.listdir(conf.image_path):
            os.remove(os.path.join(conf.image_path, image))
            click.echo(click.style(f"'{image}' removed", fg="green"))
        else:
            click.echo(click.style(f"'{image}' not available", fg="red"))
