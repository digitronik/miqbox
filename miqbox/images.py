import logging
import os
import socket

import click
import requests
from bs4 import BeautifulSoup

from miqbox.configuration import Configuration

logger = logging.getLogger(__name__)


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
            logger.warning(f"repository not set for {self.stream}")
            click.echo(click.style(f"repository not set for {self.stream}", fg="red"))
            exit(1)

        if self.stream == "downstream":
            base_version = ".".join(self.version.split(".")[:2])
            repo = f"{repo}/builds/cfme/{base_version}/stable"

        logger.debug(f"Repository link: {repo}")
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
                logger.warning(f"Unable to request: '{self.repo_link}'")
                click.echo(click.style("Check Network connection", fg="red"))
                exit(1)

            soup = BeautifulSoup(page, "html.parser")

            for node in soup.find_all("a"):
                img = node.get("href")
                if img and img.endswith(self.extension) and self.version in img:
                    imgs.append(img)
        logger.debug(f"Available images: {imgs}")
        return imgs

    def download(self, name):
        """Download image with click progress bar

        Args:
            name (str): name of image
        """
        url = f"{self.repo_link}/{name}"
        logger.info(f"Downloading image '{name}' from url '{url}'")

        try:
            r = requests.get(url=url, stream=True)
        except requests.exceptions.ConnectionError:
            logger.warning(f"Unable to request {url}")
            click.echo(click.style("Check network connection; try again...", fg="red"))
            exit(1)

        if r.status_code != requests.codes.ok:
            logger.warning(f"Unable to connect {self.repo_link}/{name}")
            click.echo(click.style(f"Unable to connect {self.repo_link}/{name}", fg="red"))
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
        try:
            os.remove(os.path.join(self.image_path, name))
            logger.info(f"'{name}' deleted from '{self.image_path}'")
        except FileNotFoundError:
            logger.error(f"{name} File not found in {self.image_path}")

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
    logger.info("miqbox images command")

    if remote or local:
        streams = list(conf.repositories.keys())
        stream = click.prompt("stream:", default=streams[0], type=click.Choice(streams))

        versions = conf.repositories.get(stream).versions
        version = click.prompt("Version:", default=versions[-1], type=click.Choice(versions))

        img = Images(stream=stream, version=version)
        images = img.images(local=not remote)
    else:
        images = [img for img in os.listdir(conf.image_path)]

    logger.debug(f"Images found: {images}")

    for img in images:
        if filter:
            logger.info(f"Filtering images: '{filter}'")
            click.echo(click.style(img, fg="green")) if filter in img else 0
        else:
            click.echo(click.style(img, fg="green"))


@click.command(help="Download Image")
@click.argument("image_name")
def pull(image_name):
    """Pull image available on remote repository"""

    logger.info("miqbox pull command")
    images = Images.instantiate_with_image(image_name)

    if image_name not in images.images(local=True):
        images = Images.instantiate_with_image(image_name)
        images.download(image_name)
        click.echo(click.style(f"{image_name} download successfully", fg="green"))
    else:
        click.echo(click.style(f"{image_name} already available", fg="red"))


@click.command(help="Remove local Images")
@click.argument("image_names", nargs=-1)
def rmi(image_names):
    """Remove local images"""

    logger.info("miqbox rmi command")
    conf = Configuration()

    for image in image_names:
        if image in os.listdir(conf.image_path):
            os.remove(os.path.join(conf.image_path, image))
            logger.debug(f"'{image}' removed")
            click.echo(click.style(f"'{image}' removed", fg="green"))
        else:
            logger.debug(f"'image' not available in '{conf.image_path}'")
            click.echo(click.style(f"'{image}' not available", fg="red"))
