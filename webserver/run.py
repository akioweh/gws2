"""
Run the webserver.
This file should be able to run the webserver from anywhere (any cwd).
Alternatively, run run_server.py (in the parent (project) directory).

To execute directly from the terminal, use uvicorn::

    $ uvicorn webserver:app

from the project root directory.
"""

from os.path import dirname, abspath, join as path_join

import uvicorn

__all__ = ['run']


def run(working_dir: str = None, reload: bool = True):
    """Runs the webserver.
    ``working_dir`` shouldn't ever need setting.
    """
    uvicorn.run(
        'webserver:app',
        reload=reload,
        log_level='debug',
        loop='asyncio',
        app_dir=working_dir,
        reload_dirs=abspath(dirname(__file__)),
        reload_excludes=[
            'files/**/*.*',
            'files/*.*'
        ]  # changes to resources should not trigger a reload
    )


if __name__ == '__main__':
    print('Direct execution of ``run.py`` in webserver package.')
    # in order for Python's relative imports to work, we need to set the working directory
    # to the project root directory (the directory containing the webserver package)
    target_cwd = abspath(path_join(dirname(__file__), '..'))

    run(target_cwd)

    input('Press enter to exit')
