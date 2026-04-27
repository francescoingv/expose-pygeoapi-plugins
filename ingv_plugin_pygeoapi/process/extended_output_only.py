# =================================================================
#
# Authors: Francesco Martinelli <francesco.martinelli@ingv.it>
#
# Copyright (c) 2026 Francesco Martinelli
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import logging

from pygeoapi.process.base import BaseProcessor, GenericError, ProcessorExecuteError
from jsonschema.validators import Draft202012Validator

LOGGER = logging.getLogger(__name__)

#: Process metadata and description
PROCESS_METADATA = {
  'id': 'extended_output_only',
  'title': 'Extended Output-only Process',
  'description': 'Testable process with multiple outputs, no input.',
  'version': '1.0.0',
  'jobControlOptions': [
    'async-execute',
    'sync-execute'
  ],
  'outputTransmission': [
    'value',
    'reference'
  ],
  'inputs': {
  },
  'outputs': {
    'simpleNumberOutput': {
      'title': '',
      'description': 'Returns a simple number (5).',
      'schema': {
        'type': 'number',
      }
    },
    'multipleNumberOutput': {
      'title': '',
      'description': 'Returns two numbers (6, 7) in an array, can be requested either as csv, or as json.',
      'schema': {
        'oneOf': [
          {
            'type': 'array',
            'items': {
              'type': 'number',
            },
            'contentMediaType': "text/csv"
            # expected to return:
            # 6, 7
          },
          {
            'type': 'array',
            'items': {
              'type': 'number',
            },
            'contentMediaType': "application/json"
            # expected to return:
            # [6, 7]
          }
        ]
      }
    },
    'stringOutput': {
      'title': '',
      'description': 'Returns a string (\'this is a test\'), can be requested either as plain text, or as json.',
      'schema': {
        'oneOf': [
          {
            'type': 'string',
            'contentMediaType': "text/plain"
          },
          {
            'type': 'string',
            'contentMediaType': "application/json"
          }
        ]
      }
    },
    'echoBinaryOutput': {
      'schema': {
        'type': 'string',
        'contentEncoding': 'binary',
        'contentMediaType': "application/octet-stream"
      }
    }
  }
}


class ExtendedEchoProcessor(BaseProcessor):
    """Echo Processor example"""
    def __init__(self, processor_def):
        """
        Initialize object

        :param processor_def: provider definition

        :returns: pygeoapi.process.echo.EchoProcessor
        """

        super().__init__(processor_def, PROCESS_METADATA)

    def _resolve_input_data(self, inputData: dict) -> dict:
        """
        Resolve alternative ways to pass input parameters and check the values.
        """

        result = {}
        for key, occurrences in inputData.items():
            # Checks for valid input keywords:
            if key not in self.metadata['inputs']:
                err_msg = (f"unexpected input parameter: {key}")
                raise ProcessorExecuteError(err_msg)

            # Get expected multiplicity and schema:
            maxOccurs = self.metadata['inputs'][key].get('maxOccurs', 1)
            minOccurs = self.metadata['inputs'][key].get('minOccurs', 1)
            schema =  self.metadata['inputs'][key]['schema']

            if maxOccurs > 1:
                # An array of input occurrences is expected:
                if not isinstance(occurrences, list):
                    err_msg = (f"Expected array for input parameter: {key} .")
                    raise ProcessorExecuteError(err_msg)
                
                # Check for valid number of occurrences:
                n = len(occurrences)
                if not (minOccurs <= n <= maxOccurs):
                    err_msg = (
                        f"Invalid number of occurrences for input parameter '{key}': "
                        f"expected between {minOccurs} and {maxOccurs}, got {n}."
                    )
                    raise ProcessorExecuteError(err_msg)

                input = []
                for occurrence in occurrences:
                # For every input occurrence:
                    # Load value:
                    instance = self._resolve_single_occurrence(key, occurrence)

                    # Check schema:
                    validation_errors = self._validate_json(schema, key, instance)
                    if validation_errors:
                        raise ProcessorExecuteError(validation_errors)

                    # Add the occurrence to the array of input data:
                    input.append(instance)
                
                # Add the array of occurrences to the input:
                result[key] = input
                
            else:
                # Input is a single occurrence, not an array of occurrences:

                # Load value:
                instance = self._resolve_single_occurrence(key, occurrences)

                # Check schema:
                validation_errors = self._validate_json(schema, key, instance)
                if validation_errors:
                    raise ProcessorExecuteError(validation_errors)
                
                # Add the occurrence to the input:
                result[key] = instance

        return result

    def _resolve_single_occurrence(self, key: str, occurrence):
        """
        Resolve alternative ways to pass a single occurrence of input parameter.
        
        Possibly additional checks on ContentMediaType and/or ContentEncoding.
        """

        if not isinstance(occurrence, dict):
            # Occurrence is a simple value, return it:
            return occurrence
        else:
            # Occurrence is a qualified value:
            if "value" in occurrence:
                # Occurrence passed as qualified value: return the value.
                return occurrence["value"]

            elif "href" in occurrence:
                # Occurrence passed by reference
                return self._resolve_by_reference(key, occurrence)

            elif "bbox" in occurrence:
                err_msg = "bbox handling not implemented"
                raise GenericError(err_msg)

            elif "collection" in occurrence:
                err_msg = "collection handling not implemented"
                raise GenericError(err_msg)

            else:
                err_msg = f"Invalid object format"
                raise GenericError(err_msg)

    def _resolve_by_reference(self, key: str, reference):
        """
        Resolve by reference.

        :param key: 'str' of input key, required for specific resolution techincs:
        e.g. depending on the key, the reference may be a link, or a
        service access point, and different approaches are required.
        """

        allowed_attrs = {"href", "rel", "type", "hreflang", "title"}

        # Check for unexpected reference attributes:
        extra_keys = set(reference.keys()) - allowed_attrs
        if extra_keys:
            err_msg = (
                f"Invalid attributes for href object: {extra_keys}"
            )
            raise GenericError(err_msg)

        # Not implemented yet.
        err_msg = f"href handling not implemented for key {key}"
        raise GenericError(err_msg)

    def _validate_json(schema: dict, key: str, instance: dict) -> list:
        """
        Helper function to validate JSON against a JSON Schema

        :param schema: `dict` of JSON Schema
        :param key: 'str' of input key: use to possibly skip validation
        in specific cases.
        :paran instance: `dict` of request instance

        :returns: `list` of valiation errors
        """

        validation_errors = []
        LOGGER.debug('Validating input against schema')
        LOGGER.debug(f'Input: {instance}')
        LOGGER.debug(f'Schema: {schema}')
        validator = Draft202012Validator(schema)

        for error in validator.iter_errors(instance):
            LOGGER.debug(f'{error.json_path}: {error.message}')
            validation_errors.append(f'{error.json_path}: {error.message}')

        return validation_errors

    def _resolve_requested_output(self, requested_output) -> dict:
        allowed_transmission_modes = self.metadata.get("outputTransmission", [])

        result = {}
        # No outputs parameter means all outputs are requested:
        if not requested_output:
           requested_output = set(self.metadata.get("outputs", []))

        if isinstance(requested_output, dict):
            # requested_output is a dictionary, items possibly containing
            # "transmissionMode" attribute, otherwise set transmissionMode
            # to default:
            for output_id, output_info in requested_output.items():
                transmission_mode = output_info.get(
                    "transmissionMode", "value"
                )

                if transmission_mode not in allowed_transmission_modes:
                    raise ProcessorExecuteError(
                        f"Invalid transmissionMode for {output_id}: "
                        f"{transmission_mode}. Allowed values: "
                        f"{allowed_transmission_modes}."
                    )
                
                output_info["transmissionMode"] = transmission_mode
                result[output_id] = output_info
        else:
            # requested_output is a list, transmissionMode = default value
            if "value" not in allowed_transmission_modes:
                raise ProcessorExecuteError(
                    f"Invalid transmissionMode (default = 'value'). "
                    f"Allowed values: {allowed_transmission_modes}."
                )
            
            for output_id in requested_output:
                output_info= {"transmissionMode": "value"}
                result[output_id] = output_info
            

        # Check for unexpected requested outputs:
        if set(requested_output) - set(self.metadata['outputs']):
            err_msg = 'Outputs contains unexpected parameters.'
            raise ProcessorExecuteError(err_msg)
        
        return result
        

    def execute(self, data, outputs=None):

        inputData = self._resolve_input_data(data)

        requestedOutputs = self._resolve_requested_output(outputs)

        produced_outputs = {}

        if 'echoNumberOutput' in requestedOutputs:
            produced_outputs['echoNumberOutput'] = {'mediaType': 'text/plain'}
            
            transmission_mode = requestedOutputs['echoNumberOutput'].get(
                'transmissionMode', ''
            )
            # Note: inputData['echoNumberInput'] is a Number
            if transmission_mode == "value":
                produced_outputs['echoNumberOutput']['value'] = inputData['echoNumberInput']
            elif (transmission_mode == "reference"):
                err_msg = f"output by reference not yet implemented."
                raise GenericError(err_msg)
            else: # should never happen: resolved in resolve_requested_output()
                raise ProcessorExecuteError("Program error.")

        if 'echoMultipleNumberOutput' in requestedOutputs:
            produced_outputs['echoMultipleNumberOutput'] = {'mediaType': 'application/json'}

            transmission_mode = requestedOutputs['echoMultipleNumberOutput'].get(
                'transmissionMode', ''
            )
            # Note: inputData['echoMultipleNumberInput'] is an array of Numbers
            if transmission_mode == "value":
                produced_outputs['echoMultipleNumberOutput']['value'] = inputData['echoMultipleNumberInput']
            elif (transmission_mode == "reference"):
                err_msg = f"output by reference not yet implemented."
                raise GenericError(err_msg)
            else: # should never happen: resolved in resolve_requested_output()
                raise ProcessorExecuteError("Program error.")

        if 'echoNumberArrayOutput' in requestedOutputs:
            produced_outputs['echoNumberArrayOutput'] = {'mediaType': 'application/json'}

            transmission_mode = requestedOutputs['echoNumberArrayOutput'].get(
                'transmissionMode', ''
            )
            # Note: inputData['echoNumberArrayInput'] is an array of Numbers
            if transmission_mode == "value":
                produced_outputs['echoNumberArrayOutput']['value'] = inputData['echoNumberArrayInput']
            elif (transmission_mode == "reference"):
                err_msg = f"output by reference not yet implemented."
                raise GenericError(err_msg)
            else: # should never happen: resolved in resolve_requested_output()
                raise ProcessorExecuteError("Program error.")

        if 'echoMultipleNumberArrayOutput' in requestedOutputs:
            produced_outputs['echoMultipleNumberArrayOutput'] = {'mediaType': 'application/json'}

            transmission_mode = requestedOutputs['echoMultipleNumberArrayOutput'].get(
                'transmissionMode', ''
            )
            # Note: inputData['echoMultipleNumberArrayInput'] is a two dimentional array of Numbers
            if transmission_mode == "value":
                produced_outputs['echoMultipleNumberArrayOutput']['value'] = inputData['echoMultipleNumberArrayInput']
            elif (transmission_mode == "reference"):
                err_msg = f"output by reference not yet implemented."
                raise GenericError(err_msg)
            else: # should never happen: resolved in resolve_requested_output()
                raise ProcessorExecuteError("Program error.")

        if 'echoStringOutput' in requestedOutputs:
            produced_outputs['echoStringOutput'] = {'mediaType': 'text/plain'}

            transmission_mode = requestedOutputs['echoStringOutput'].get(
                'transmissionMode', ''
            )
            # Note: inputData['echoStringInput'] is a string
            if transmission_mode == "value":
                produced_outputs['echoStringOutput']['value'] = inputData['echoStringInput']
            elif (transmission_mode == "reference"):
                err_msg = f"output by reference not yet implemented."
                raise GenericError(err_msg)
            else: # should never happen: resolved in resolve_requested_output()
                raise ProcessorExecuteError("Program error.")

        if 'echoBinaryOutput' in requestedOutputs:
            produced_outputs['echoBinaryOutput'] = {'mediaType': 'application/octet-stream'}

            transmission_mode = requestedOutputs['echoBinaryOutput'].get(
                'transmissionMode', ''
            )
            # Note: inputData['echoBinaryInput'] is a binary stream represented by a string encoded base64
            if transmission_mode == "value":
                produced_outputs['echoBinaryOutput']['value'] = inputData['echoStringInput']
                produced_outputs['echoBinaryOutput']['encoding'] = "base64"
            elif (transmission_mode == "reference"):
                err_msg = f"output by reference not yet implemented."
                raise GenericError(err_msg)
            else: # should never happen: resolved in resolve_requested_output()
                raise ProcessorExecuteError("Program error.")

        if len(produced_outputs) == 0:
            # --- CASE 0: NO OUTPUT ---
            # Probably:
            # - http code = 204
            # - mimetype = None
            # - body = empty: None or "" ?
            pass

        else:
            # The followings:
            # - http code
            # - media type
            # - body content
            # are affected by:
            # - number of produced_outputs
            # - transmission mode (value/reference)
            # - type of response (raw/document)
            pass

        # NOTE: What should it be returned??
        return mimetype, returned_outputs

    def __repr__(self):
        return f'<EchoProcessor> {self.name}'
