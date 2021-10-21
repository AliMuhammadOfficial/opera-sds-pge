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
===========
base_pge.py
===========

Module defining the Base PGE interfaces from which all other PGEs are derived.

"""

import yaml

from os.path import basename, join, splitext, exists

from yamale import YamaleError

from .runconfig import RunConfig
from opera.util.error_codes import ErrorCode
from opera.util.logger import PgeLogger
from opera.util.run_utils import time_and_execute


class PreProcessorMixin:
    """
    Mixin class which is responsible for handling all pre-processing steps for
    the PGE. The pre-processing phase is defined as all steps necessary prior
    to SAS execution.

    This class is intended for use as a Mixin for use with the PgeExecutor
    class and its inheritors, and as such, this class assumes access to the
    instance attributes defined by PgeExecutor.

    Inheritors of PreProcessorMixin may provide overloaded implementations
    for any of the exiting pre-processing steps, and even provide additional
    steps as necessary.

    """
    def _initialize_logger(self):
        """
        Creates the logger object used by the PGE.

        The logger is created using a default name, as the proper filename
        cannot be determined until the RunConfig is parsed and validated.
        """
        self.logger = PgeLogger()

        self.logger.info(self.name, ErrorCode.LOG_FILE_CREATED,
                         f'Log file initialized to {self.logger.get_file_name()}')

    def _load_runconfig(self):
        """
        Loads the RunConfig file provided to the PGE into an in-memory
        representation.
        """
        self.logger.info(self.name, ErrorCode.LOADING_RUN_CONFIG_FILE,
                         f'Loading RunConfig file {self.runconfig_path}')

        self.runconfig = RunConfig(self.runconfig_path)

    def _validate_runconfig(self):
        """
        Validates the parsed RunConfig against the appropriate schema(s).

        Raises
        ------
        RuntimeError
            If the RunConfig fails validation.

        """
        self.logger.info(self.name, ErrorCode.VALIDATING_RUN_CONFIG_FILE,
                         f'Validating RunConfig file {self.runconfig.filename}')

        try:
            self.runconfig.validate()
        except YamaleError as error:
            error_msg = (f'Validation of RunConfig file {self.runconfig.filename} '
                         f'failed, reason(s): \n{str(error)}')

            self.logger.critical(
                self.name, ErrorCode.RUN_CONFIG_VALIDATION_FAILED,
                error_msg
            )

            raise RuntimeError(error_msg)

    def _configure_logger(self):
        """
        Configures the logger used by the PGE using information from the
        parsed and validated RunConfig.
        """
        self.logger.error_code_base = self.runconfig.error_code_base

        # since there is a brace before the variable in braces the whole statement has to be in {}
        self.logger.workflow = f'{{self.runconfig.pge_name::{basename(__file__)}}}'

        # TODO: can (or should) the log move/rename step be performed here?

        self.logger.info(self.name, ErrorCode.LOG_FILE_INIT_COMPLETE,
                         f'Log file configuration complete')

    def _setup_directories(self):
        """
        Creates the output/scratch directory locations referenced by the
        RunConfig if they don't exist already.
        """
        # TODO
        pass

    def run_preprocessor(self, **kwargs):
        """
        Executes the pre-processing steps for PGE initialization.

        Inheritors of this Mixin may override this function to tailor the
        order of pre-processing steps.

        Parameters
        ----------
        kwargs : dict
            Any keyword arguments needed by the pre-processor

        """
        # TODO: better way to handle trace statements before logger has been created?
        print(f'Running preprocessor for PreProcessorMixin')

        self._initialize_logger()
        self._load_runconfig()
        self._validate_runconfig()
        self._configure_logger()
        self._setup_directories()


class PostProcessorMixin:
    """
    Mixin class which is responsible for handling all post-processing steps for
    the PGE. The post-processing phase is defined as all steps necessary after
    SAS execution has completed.

    This class is intended for use as a Mixin for use with the PgeExecutor
    class and its inheritors, and as such, this class assumes access to the
    instance attributes defined by PgeExecutor.

    Inheritors of PostProcessorMixin may provide overloaded implementations
    for any of the exiting pre-processing steps, and even provide additional
    steps as necessary.

    """

    def _run_sas_qa_executable(self):
        # TODO
        pass

    def _create_catalog_metadata(self):
        # TODO
        pass

    def _create_iso_metadata(self):
        # TODO
        pass

    def _stage_output_files(self):
        # TODO
        pass

    def run_postprocessor(self, **kwargs):
        """
        Executes the post-processing steps for PGE job completion.

        Inheritors of this Mixin may override this function to tailor the
        order of post-processing steps.

        Parameters
        ----------
        kwargs : dict
            Any keyword arguments needed by the pre-processor

        """
        print(f'Running postprocessor for PostProcessorMixin')

        self._run_sas_qa_executable()
        self._create_catalog_metadata()
        self._create_iso_metadata()
        self._stage_output_files()


class PgeExecutor(PreProcessorMixin, PostProcessorMixin):
    """
    Main class for execution of a PGE, including the SAS layer.

    The PgeExecutor class is primarily responsible for defining the interface
    for PGE execution and managing the actual execution of the SAS executable
    within a subprocess. PGE's also define pre- and post-processing stages,
    which are invoked by PgeExecutor, but whose implementations are defined
    by use of Mixin classes.

    The use of Mixin classes allows for flexibility of PGE design, where
    inheritors of PgeExecutor can compose a custom PGE by providing overloaded
    implementations of the Mixin classes to tailor the behavior of the pre-
    and post-processing phases, where necessary, while still inheriting any
    common functionality from this class.

    """
    NAME = "PgeExecutor"

    def __init__(self, pge_name, runconfig_path, **kwargs):
        """
        Creates a new instance of PgeExecutor

        Parameters
        ----------
        pge_name : str
            Name to associate with this PGE.
        runconfig_path : str
            Path to the RunConfig to be used with this PGE.
        kwargs : dict
            Any additional keyword arguments needed by the PGE.

        """
        self.name = PgeExecutor.NAME
        self.pge_name = pge_name
        self.runconfig_path = runconfig_path
        self.runconfig = None
        self.logger = None

    def _isolate_sas_runconfig(self):
        """
        Isolates the SAS-specific portion of the RunConfig into its own
        YAML file so it may be fed into the SAS executable without unneeded
        PGE configuration settings.

        """
        sas_config = self.runconfig.sas_config

        pge_runconfig_filename = basename(self.runconfig.filename)
        pge_runconfig_fileparts = splitext(pge_runconfig_filename)

        sas_runconfig_filename = f'{pge_runconfig_fileparts[0]}_sas{pge_runconfig_fileparts[1]}'
        sas_runconfig_filepath = join(self.runconfig.scratch_path, sas_runconfig_filename)

        try:
            with open(sas_runconfig_filepath, 'w') as outfile:
                yaml.dump(sas_config, outfile)
        except OSError as err:
            self.logger.critical(self.name, ErrorCode.SAS_CONFIG_CREATION_FAILED,
                                 f'Failed to create SAS config file {sas_runconfig_filepath}, '
                                 f'reason: {str(err)}')

        self.logger.info(self.name, ErrorCode.CREATED_SAS_CONFIG,
                         f'SAS RunConfig created at {sas_runconfig_filepath}')

        return sas_runconfig_filepath

    def run_sas_executable(self, **kwargs):
        """
        Kicks off a SAS executable as defined by the RunConfig provided to
        the PGE.

        Execution time for the SAS is collected and logged by this method.

        Parameters
        ----------
        kwargs : dict
            Any keyword arguments needed for SAS execution.

        """
        sas_program_path = self.runconfig.sas_program_path
        sas_program_options = self.runconfig.sas_program_options
        sas_runconfig_filepath = self._isolate_sas_runconfig()

        # TODO: detect and support absolute paths in addition to python module names
        if not exists(sas_program_path):
            print("Path in Runconfig does not exist.")
            command_line = ['python3', '-q', '/Users/jehofman/Documents/opera_pge/src/opera/test/pge/data/hello.py']
        else:
            command_line = ['python3', '-m', sas_program_path]

        if sas_program_options:
            command_line.extend(sas_program_options.split())

        command_line.extend(['--', sas_runconfig_filepath])

        self.logger.debug(self.name, ErrorCode.SAS_EXE_COMMAND_LINE,
                          f'SAS EXE command line: {" ".join(command_line)}')

        # Before starting the SAS program, flush the log file to keep the
        # contents properly time ordered, since the SAS program will also write
        # to the same log file.
        self.logger.flush()

        self.logger.info(self.name, ErrorCode.SAS_PROGRAM_STARTING,
                         'Starting SAS executable')

        elapsed_time = time_and_execute(command_line, self.logger)

        self.logger.info(self.name, ErrorCode.SAS_PROGRAM_COMPLETED,
                         'SAS executable complete')

        self.logger.log_one_metric(self.name, 'sas.elapsed_seconds', elapsed_time)

    def run(self, **kwargs):
        """
        Main entry point for PGE execution.

        The pre-processor stage is run to initialize the PGE, followed by
        SAS execution, then completed with the post-processing steps to complete
        the job.

        """
        self.run_preprocessor(**kwargs)

        self.run_sas_executable(**kwargs)

        # self.run_postprocessor(**kwargs)
