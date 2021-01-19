# -*- coding: utf-8 -*-
# A Conducto Pipeline
# Visit https://www.conducto.com for more information.
import os
import conducto as co
from inspect import cleandoc


def pipeline() -> co.Serial:
    """
    Define our Full Conducto Pipeline
    """
    os.chdir(os.path.dirname(__file__))
    context = '.'
    dockerfiles = (
        # Define our Containers
        ("Python 3.9", os.path.join('.conducto', 'Dockerfile.py39')),
        ("Python 3.8", os.path.join('.conducto', 'Dockerfile.py38')),
        ("Python 3.7", os.path.join('.conducto', 'Dockerfile.py37')),
        ("Python 3.6", os.path.join('.conducto', 'Dockerfile.py36')),
        ("Python 3.5", os.path.join('.conducto', 'Dockerfile.py35')),
        ("Python 2.7", os.path.join('.conducto', 'Dockerfile.py27')),
    )

    # find generated coverage filename and store it in the pipeline
    set_coverage_template = cleandoc('''
        find . -mindepth 1 -maxdepth 1 -type f \\
            -name '.coverage.*' -exec \\
                conducto-data-pipeline put \\
                    --name "coverage.{tick}" --file {{}} \;''')

    # pull generated file from the pipeline and place it back into
    # our working directory
    get_coverage_template = cleandoc('''
        id=0

        while [ $id < {ticks} ]; do
            conducto-data-pipeline get --name coverage.$id --file .coverage.$id
            let id+=1
        done

        coverage combine && coverage report''')

    # Our base image is always the first entry defined in our dockerfiles
    base_image = co.Image(dockerfile=dockerfiles[0][1], context=context)

    with co.Serial() as pipeline:
        # Code Styles
        co.Exec(
            'flake8 . --count --show-source --statistics',
            name="Style Guidelines", image=base_image)

        with co.Parallel(name="Tests"):
            for no, entry in enumerate(dockerfiles):
                name, dockerfile = entry
                image = co.Image(dockerfile=dockerfile, context=context)
                # Unit Tests
                # These produce files that look like:
                # .coverage.{userid}.{hostname}.NNNNNN.NNNNNN where:
                #  - {userid} becomes the user that ran the test
                #  - {hostname} identifies the hostname it was built on
                #  - N gets replaced with a number

                # The idea here is that the .coverage.* file is unique
                # from others being built in other containers
                co.Exec(
                    'coverage run --parallel -m pytest && ' +
                    set_coverage_template.format(tick=no),
                    name="{} Coverage".format(name), image=image)

        # Coverage Reporting
        co.Exec(
            get_coverage_template.format(ticks=len(dockerfiles)),
            name="Test Code Coverage", image=base_image)

    return pipeline


if __name__ == "__main__":
    """
    Execute our pipeline
    """
    exit(co.main(default=pipeline))
