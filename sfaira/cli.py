import logging
import os
import sys

import click
import rich
import rich.logging
from rich import traceback
from rich import print

from sfaira.commands.annotate_dataloader import DataloaderAnnotater
from sfaira.commands.cache_control import CacheControl
from sfaira.commands.utils import doi_lint
from sfaira.commands.validate_dataloader import DataloaderValidator
from sfaira.commands.validate_h5ad import H5adValidator
from sfaira.commands.test_dataloader import DataloaderTester
from sfaira.commands.submit_pullrequest import PullRequestHandler

from sfaira import __version__
from sfaira.commands.create_dataloader import DataloaderCreator
from sfaira.commands.upgrade import UpgradeCommand

WD = os.path.dirname(__file__)
log = logging.getLogger()


def set_paths(loader=None, data=None, cache=None):
    env_loader_path = os.getenv('SFAIRA_LOADER_PATH')
    env_data_path = os.getenv('SFAIRA_DATA_PATH')
    env_cache_path = os.getenv('SFAIRA_CACHE_PATH')
    if env_loader_path:
        if not os.getenv('SFAIRA_DOCKER'):  # Skip print if running in sfaira docker where env variables are always set
            print('[bold blue]SFAIRA_LOADER_PATH environment variable detected. Ignoring --path-loader if supplied.')
        loader = env_loader_path
    if env_data_path:
        if not os.getenv('SFAIRA_DOCKER'):  # Skip print if running in sfaira docker where env variables are always set
            print('[bold blue]SFAIRA_DATA_PATH environment variable detected. Ignoring --path-data if supplied.')
        data = env_data_path
    if env_cache_path:
        if not os.getenv('SFAIRA_DOCKER'):  # Skip print if running in sfaira docker where env variables are always set
            print('[bold blue]SFAIRA_CACHE_PATH environment variable detected. Ignoring --path-cache if supplied.')
        cache = env_cache_path
    return loader, data, cache


def check_paths(pathlist):
    for p in pathlist:
        if p is None or not os.path.isdir(p):
            print(f"Error: Path {p} does not exist.")
            sys.exit()


def main():
    traceback.install(width=200, word_wrap=True)
    print(r"""[bold blue]
███████ ███████  █████  ██ ██████   █████ 
██      ██      ██   ██ ██ ██   ██ ██   ██ 
███████ █████   ███████ ██ ██████  ███████ 
     ██ ██      ██   ██ ██ ██   ██ ██   ██ 
███████ ██      ██   ██ ██ ██   ██ ██   ██ 
                                           
        """)

    print('[bold blue]Run [green]sfaira --help [blue]for an overview of all commands\n')

    # Is the latest sfaira version installed? Upgrade if not!
    if not UpgradeCommand.check_sfaira_latest():
        print('[bold blue]Run [green]sfaira upgrade [blue]to get the latest version.')
    sfaira_cli()


@click.group()
@click.version_option(__version__, message=click.style(f'sfaira Version: {__version__}', fg='blue'))
@click.option('-v', '--verbose', is_flag=True, default=False, help='Enable verbose output (print debug statements).')
@click.option("-l", "--log-file", help="Save a verbose log to a file.")
@click.pass_context
def sfaira_cli(ctx, verbose, log_file):
    """
    Create and manage sfaira dataloaders.
    """
    # Set the base logger to output DEBUG
    log.setLevel(logging.DEBUG)

    # Set up logs to the console
    log.addHandler(
        rich.logging.RichHandler(
            level=logging.DEBUG if verbose else logging.INFO,
            console=rich.console.Console(file=sys.stderr),
            show_time=True,
            markup=True,
        )
    )

    # Set up logs to a file if we asked for one
    if log_file:
        log_fh = logging.FileHandler(log_file, encoding="utf-8")
        log_fh.setLevel(logging.DEBUG)
        log_fh.setFormatter(logging.Formatter("[%(asctime)s] %(name)-20s [%(levelname)-7s]  %(message)s"))
        log.addHandler(log_fh)


@sfaira_cli.command()
def cache_clear() -> None:
    """Clears sfaira cache, including ontology and genome cache."""
    ctrl = CacheControl()
    ctrl.clear()


@sfaira_cli.command()
def cache_reload() -> None:
    """Downloads new ontology versions into cache."""
    ctrl = CacheControl()
    ctrl.reload()


@sfaira_cli.command()
@click.option('--path-data',
              default="./",
              type=click.Path(exists=False),
              help='Absolute path of the desired location of the raw data directory.')
@click.option('--path-loader',
              default="sfaira/data/dataloaders/loaders/",
              type=click.Path(exists=False),
              help='Relative path from the current directory to the desired location of the dataloader.')
def create_dataloader(path_data, path_loader) -> None:
    """
    Interactively create a new sfaira dataloader.
    """
    path_loader, path_data, _ = set_paths(loader=path_loader, data=path_data)
    check_paths([path_loader, path_data])
    dataloader_creator = DataloaderCreator(path_loader)
    dataloader_creator.create_dataloader(path_data)


@sfaira_cli.command()
@click.option('--doi', type=str, default=None, help="The doi of the paper that the dataloader refers to.")
@click.option('--path-loader',
              default="sfaira/data/dataloaders/loaders/",
              type=click.Path(exists=False),
              help='Relative path from the current directory to the desired location of the dataloader.')
def validate_dataloader(doi, path_loader) -> None:
    """
    Verifies the dataloader against sfaira's requirements.
    """
    path_loader, _, _ = set_paths(loader=path_loader)
    check_paths([path_loader])
    if doi is None or doi_lint(doi):
        dataloader_validator = DataloaderValidator(path_loader, doi)
        dataloader_validator.validate()
    else:
        print('[bold red]The supplied DOI is malformed!')  # noqa: W605


@sfaira_cli.command()
@click.option('--doi', type=str, default=None, help="The doi of the paper that the dataloader refers to.")
@click.option('--path-data',
              default="./",
              type=click.Path(exists=False),
              help='Absolute path of the location of the raw data directory.')
@click.option('--path-loader',
              default="sfaira/data/dataloaders/loaders/",
              type=click.Path(exists=False),
              help='Relative path from the current directory to the location of the dataloader.')
def annotate_dataloader(doi, path_data, path_loader) -> None:
    """
    Annotates a dataloader.
    """
    path_loader, path_data, _ = set_paths(loader=path_loader, data=path_data)
    check_paths([path_loader, path_data])
    if doi is None or doi_lint(doi):
        dataloader_validator = DataloaderValidator(path_loader, doi)
        dataloader_validator.validate()
        dataloader_annotater = DataloaderAnnotater()
        dataloader_annotater.annotate(path_loader, path_data, dataloader_validator.doi)
    else:
        print('[bold red]The supplied DOI is malformed!')  # noqa: W605


@sfaira_cli.command()
@click.option('--doi', type=str, default=None, help="The doi of the paper that the dataloader refers to.")
@click.option('--path-data',
              default="./",
              type=click.Path(exists=False),
              help='Absolute path of the location of the raw data directory.')
@click.option('--path-loader',
              default="sfaira/data/dataloaders/loaders/",
              type=click.Path(exists=False),
              help='Relative path from the current directory to the location of the dataloader.')
def finalize_dataloader(doi, path_data, path_loader) -> None:
    """
    Runs a dataloader integration test.
    """
    path_loader, path_data, _ = set_paths(loader=path_loader, data=path_data)
    check_paths([path_loader, path_data])
    if doi is None or doi_lint(doi):
        dataloader_validator = DataloaderValidator(path_loader, doi)
        dataloader_validator.validate()
        dataloader_tester = DataloaderTester(path_loader, path_data, doi)
        dataloader_tester.test_dataloader()
    else:
        print('[bold red]The supplied DOI is malformed!')  # noqa: W605


@sfaira_cli.command()
@click.option('--doi', type=str, default=None, help="DOI of data sets to export")
@click.option('--schema', type=str, default=None, help="Schema to streamline to, e.g. 'cellxgene'")
@click.option('--path-out',
              type=click.Path(exists=True),
              help='Absolute path of the location of the streamlined output h5ads.')
@click.option('--path-data',
              default="./",
              type=click.Path(exists=True),
              help='Absolute path of the location of the raw data directory.')
@click.option('--path-cache',
              type=click.Path(exists=True),
              default=None,
              help='The optional absolute path to cached data library maintained by sfaira. Using such a cache speeds '
                   'up loading in sequential runs but is not necessary.')
def export_h5ad(doi, schema, path_out, path_data, path_cache) -> None:
    """Creates a collection of streamlined h5ad object for a given DOI."""
    raise NotImplementedError()
    # _, path_data, path_cache = set_paths(data=path_data, cache=path_cache)
    # check_paths([path_data, path_cache])


@sfaira_cli.command()
@click.option('--h5ad', type=click.Path(exists=True))
@click.option('--schema', type=str, default=None)
def validate_h5ad(h5ad, schema) -> None:
    """Runs a component test on a streamlined h5ad object.

    h5ad is the absolute path of the .h5ad file to test.
    schema is the schema type ("cellxgene",) to test.
    """
    h5ad_tester = H5adValidator(h5ad, schema)
    h5ad_tester.test_schema()
    h5ad_tester.test_numeric_data()


@sfaira_cli.command()
def publish_loader() -> None:
    """
    Interactively create a GitHub pullrequest for a newly created dataloader.
    This only works when called in the sfaira CLI docker container.
    """
    path_loader, _, _ = set_paths()
    pullrequest_handler = PullRequestHandler(path_loader)
    pullrequest_handler.submit_pr()


if __name__ == "__main__":
    traceback.install()
    sys.exit(main())  # pragma: no cover
