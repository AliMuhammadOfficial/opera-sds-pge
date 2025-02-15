#!/usr/bin/env python3
#
# Copyright 2021, by the California Institute of Technology.
# ALL RIGHTS RESERVED.
# United States Government sponsorship acknowledged.
# Any commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
# This software may be subject to U.S. export control laws and regulations.
# By accepting this document, the user agrees to comply with all applicable
# U.S. export laws and regulations. User has the responsibility to obtain
# export licenses, or other export authority as may be required, before
# exporting such information to foreign countries or providing access to
# foreign persons.
#

"""
=================
test_main_pge.py
=================

Unit tests for the pge/base_pge.py module.
"""
import os
import tempfile
import unittest
from os.path import abspath, join

from pkg_resources import resource_filename

from opera.pge import PgeExecutor, RunConfig
from opera.scripts.pge_main import load_run_config_file
from opera.scripts.pge_main import open_log_file
from opera.scripts.pge_main import pge_start
from opera.util import PgeLogger


class PgeMainTestCase(unittest.TestCase):
    """Base test class using unittest"""

    @classmethod
    def setUpClass(cls) -> None:
        """
        Set up directories for testing
        initialize config yamele file

        """
        cls.starting_dir = abspath(os.curdir)
        cls.test_dir = resource_filename(__name__, "")
        cls.data_dir = join(cls.test_dir, "data")
        cls.scripts_dir = abspath(join(os.pardir, os.pardir, 'scripts'))

        os.chdir(cls.test_dir)

        cls.working_dir = tempfile.TemporaryDirectory(
            prefix="test_pge_main_", suffix='temp', dir=os.curdir)
        cls.config_file = join(cls.data_dir, "test_base_pge_config.yaml")

    @classmethod
    def tearDownClass(cls) -> None:
        """
        At completion re-establish starting directory
        -------
        """
        cls.working_dir.cleanup()
        os.chdir(cls.starting_dir)

    def setUp(self) -> None:
        """
        Use the temporary directory as the working directory
        -------
        """
        os.chdir(self.working_dir.name)

    def tearDown(self) -> None:
        """
        Return to starting directory
        -------
        """
        os.chdir(self.test_dir)

    def test_open_log_file(self):
        """
        This test calls the open_log_file() function and verifies that a logger
        was created properly

        """
        logger = None

        # check that logger is not instantiated
        self.assertIsNone(logger)

        # Instantiate a logger
        logger = open_log_file()

        # Check that the logger were instantiated as expected
        self.assertIsInstance(logger, PgeLogger)

    def test_load_run_config_file(self):
        """
        This test calls the load_run_config_file() function.
        It them verifies the successful creation of a RunConfig instance
        It then checks that the proper directories were created

        """
        # Verify we start with no run_config file
        run_config = None
        self.assertIsNone(run_config)

        #  New logger to pass to load_run_config_file
        logger = open_log_file()

        # run the function to be tested
        run_config = load_run_config_file(logger, self.config_file)

        # Verify the instance of a RunConfig object
        self.assertIsInstance(run_config, RunConfig)

    def test_pge_start_functionality(self):
        """
        Test follows the function calls of pge_start()
        A logger and a config file are created then used in instantiating a PgeExecutor class.
        Instances and paths are checked.
        Finally a 'hello world' string in the log file is verified to be there.
        """
        #  New logger to pass to load_run_config_file
        logger = open_log_file()

        # run the function to be tested
        run_config = load_run_config_file(logger, self.config_file)

        pge = PgeExecutor(run_config.pge_name, self.config_file)

        pge.run()

        # Check that runconfig and logger were instantiated as expected
        self.assertIsInstance(pge.runconfig, RunConfig)
        self.assertIsInstance(pge.logger, PgeLogger)

        # Check that directories were created according to RunConfig
        self.assertTrue(os.path.isdir(pge.runconfig.output_product_path))
        self.assertTrue(os.path.isdir(pge.runconfig.scratch_path))

        # Check that a RunConfig for the SAS was isolated within the scratch directory
        expected_sas_config_file = join(pge.runconfig.scratch_path, 'test_base_pge_config_sas.yaml')
        self.assertTrue(os.path.exists(expected_sas_config_file))

        # Check that the log file was created and moved into the output directory
        expected_log_file = join(pge.runconfig.output_product_path, pge.logger.get_file_name())
        self.assertTrue(os.path.exists(expected_log_file))

        # Open the log file, and check that "SAS" output was captured
        with open(expected_log_file, 'r') as infile:
            log_contents = infile.read()

        self.assertIn('hello world', log_contents)

    def test_pge_start_args(self):
        """
        Verifies the pge_start() function call with a proper argument
        Verifies proper error is seen when a bad file is passed to pge_start()

        """
        # Verify the function call returns None
        self.assertIsNone(pge_start(self.config_file))

        # Verify that a bad filename raises an error
        self.assertRaises(FileNotFoundError, pge_start, "abc")


if __name__ == "__main__":
    unittest.main()
