# =================================================================
#
# Authors: Francesco Martinelli <francesco.martinelli@ingv.it>
#
# Copyright (c) 2024 Francesco Martinelli
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
import re
import copy

from pathlib import Path

from pygeoapi.process.base import (
    ProcessorExecuteError,
)
from ingv_plugin_pygeoapi.process.base_remote_execution import (
    BaseRemoteExecutionProcessor,
    validate_json,
    CHART_SCHEMA,
)

LOGGER = logging.getLogger(__name__)

INPUT_SCHEMA = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/conduit_plugin_schema.json",
  "title": "Conduit Input Schema",
  "description": "Schema for Conduit plugin inputs",
  "type": "object",
  "required": ["components"],
  "additionalProperties": False,
  "properties": {
    "components": {
      "title": "Model parameters", # opzional
      "description":
        "Parameters to calculate the multiphase, multicomponent flow "
        "of magma along the volcanic conduit. Values must be in scientific "
        "notation (e.g., 1.E3). ", # opzional
      "type": "object",
      "oneOf": [
        {
          "description":
            "Search for the mass flow rate at costant conduit "
            "diameter/fissure thickness.",
          "required": [
            "p", "t", "d", "l", "sio2", "tio2", "al2o3",
            "fe2o3", "feo", "mno", "mgo", "cao", "na2o", "k2o",
            "h2o", "co2", "fe", "pd", "dp", "ds", "dc", "c", "den"
          ],
          "additionalProperties": False,
          "properties": {
            "fg": {
              # opzional
              "type": "number",
              "title": "Mass flow rate [kg/s]",
              "description": "Initial guess for the mass flow rate, "
                "along a cylindrical conduit (optional, default value: 1.0E8). "
                "If the code does not converge, you "
                "can play around with this value.",
              "exclusiveMinimum": 0.0
            },
            "p": {
              "type": "number",
              "title": "Pressure [Pa]",
              "description": "Pressure in the magma chamber.",
              "exclusiveMinimum": 101325.0
            },
            "t": {
              "type": "number",
              "title": "Temperature [K]",
              "description": "Magma temperature",
              "exclusiveMinimum": 273.15
            },
            "d": {
              "type": "number",
              "title": "Conduit diameter [m]",
              "description": "Diameter of the cylindrical conduit",
              "exclusiveMinimum": 0.0
            },
            "l": {
              "type": "number",
              "title": "Conduit length [m]",
              "description": "Length of the cylindrical conduit",
              "exclusiveMinimum": 0.0
            },
            "sio2": {
              "type": "number",
              "title": "SiO2",
              "description": "Melt composition: Weight fraction of SiO2.",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "tio2": {
              "type": "number",
              "title": "TiO2",
              "description": "Melt composition: Weight fraction of TiO2",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "al2o3": {
              "type": "number",
              "title": "Al2O3",
              "description": "Melt composition: Weight fraction of Al2O3",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "fe2o3": {
              "type": "number",
              "title": "Fe2O3",
              "description": "Melt composition: Weight fraction of Fe2O3",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "feo": {
              "type": "number",
              "title": "FeO",
              "description": "Melt composition: Weight fraction of FeO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "mno": {
              "type": "number",
              "title": "MnO",
              "description": "Melt composition: Weight fraction of MnO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "mgo": {
              "type": "number",
              "title": "MgO",
              "description": "Melt composition: Weight fraction of MgO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "cao": {
              "type": "number",
              "title": "CaO",
              "description": "Melt composition: Weight fraction of CaO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "na2o": {
              "type": "number",
              "title": "Na2O",
              "description": "Melt composition: Weight fraction of Na2O",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "k2o": {
              "type": "number",
              "title": "K2O",
              "description": "Melt composition: Weight fraction of K2O",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "h2o": {
              "type": "number",
              "title": "H2O",
              "description": "Volatiles: Weight fraction of total H2O",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "co2": {
              "type": "number",
              "title": "CO2",
              "description": "Volatiles: Weight fraction of total CO2",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "fe": {
              "type": "number",
              "title": "Fragmentation efficiency",
              "description": "Parameter for fragmentation efficiency",
              "minimum": 0.2,
              "maximum": 1.0
            },
            "pd": {
              "type": "number",
              "title": "Pumice degassing",
              "description": "Parameter for pumice degassing",
              "minimum": 0.0,
              "maximum": 1.0
            },
            "dp": {
              "type": "number",
              "title": "Diameter of the pumices [m]",
              "description": "Average diameter of the pumices at fragmentation",
              "exclusiveMinimum": 0.0,
            },
            "ds": {
              "type": "number",
              "title": "Diameter of the shards [m]",
              "description": "Average diameter of the shards at fragmentation",
              "exclusiveMinimum": 0.0,
            },
            "dc": {
              "type": "number",
              "title": "Diameter of the crystals [m]",
              "description":
                "Average diameter of the crystals at fragmentation",
              "exclusiveMinimum": 0.0,
            },
            "c": {
              "type": "number",
              "title": "Crystal volume fraction",
              "description":
                "Volume fraction of crystals relative to a degassed magma.",
              "exclusiveMinimum": 0.0,
              "maximum": 0.7
            },
            "den": {
              "type": "number",
              "title": "Crystal density [kg/m^3]",
              "description": "Average density of the crystal phase.",
              "exclusiveMinimum": 0.0,
            }
          }
        },
        {
          "description":
            "Search for the conduit diameter at costant mass flow rate.",
          "required": ["f", "p", "t", "l", "sio2", "tio2", "al2o3", "fe2o3",
            "feo", "mno", "mgo", "cao", "na2o", "k2o", "h2o", "co2",
            "fe", "pd", "dp", "ds", "dc", "c", "den"
          ],
          "additionalProperties": False,  # non permettere chiavi extra
          "properties": {
            "f": {
              "type": "number",
              "title": "Mass flow rate [kg/s]",
              "description": "Mass flow rate along a cylindrical conduit.",
              "exclusiveMinimum": 0.0
            },
            "p": {
              "type": "number",
              "title": "Pressure [Pa]",
              "description": "Pressure in the magma chamber.",
              "exclusiveMinimum": 101325.0
            },
            "t": {
              "type": "number",
              "title": "Temperature [K]",
              "description": "Magma temperature",
              "exclusiveMinimum": 273.15
            },
            "dg": {
              # opzionale
              "type": "number",
              "title": "Conduit diameter [m]",
              "description": 
                "Initial guess for conduit diameter "
                "(optional, default value: 80.E0). "
                "If the code does not converge, "
                "you can play around with this value.",
              "exclusiveMinimum": 0.0
            },              
            "l": {
              "type": "number",
              "title": "Conduit length [m]",
              "description": "Length of the cylindrical conduit",
              "exclusiveMinimum": 0.0
            },
            "sio2": {
              "type": "number",
              "title": "SiO2",
              "description": "Melt composition: Weight fraction of SiO2.",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "tio2": {
              "type": "number",
              "title": "TiO2",
              "description": "Melt composition: Weight fraction of TiO2",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "al2o3": {
              "type": "number",
              "title": "Al2O3",
              "description": "Melt composition: Weight fraction of Al2O3",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "fe2o3": {
              "type": "number",
              "title": "Fe2O3",
              "description": "Melt composition: Weight fraction of Fe2O3",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "feo": {
              "type": "number",
              "title": "FeO",
              "description": "Melt composition: Weight fraction of FeO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "mno": {
              "type": "number",
              "title": "MnO",
              "description": "Melt composition: Weight fraction of MnO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "mgo": {
              "type": "number",
              "title": "MgO",
              "description": "Melt composition: Weight fraction of MgO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "cao": {
              "type": "number",
              "title": "CaO",
              "description": "Melt composition: Weight fraction of CaO",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "na2o": {
              "type": "number",
              "title": "Na2O",
              "description": "Melt composition: Weight fraction of Na2O",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "k2o": {
              "type": "number",
              "title": "K2O",
              "description": "Melt composition: Weight fraction of K2O",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "h2o": {
              "type": "number",
              "title": "H2O",
              "description": "Volatiles: Weight fraction of total H2O",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "co2": {
              "type": "number",
              "title": "CO2",
              "description": "Volatiles: Weight fraction of total CO2",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "fe": {
              "type": "number",
              "title": "Fragmentation efficiency",
              "description": "Parameter for fragmentation efficiency",
              "minimum": 0.2,
              "maximum": 1.0
            },
            "pd": {
              "type": "number",
              "title": "Pumice degassing",
              "description": "Parameter for pumice degassing",
              "exclusiveMinimum": 0.0,
              "exclusiveMaximum": 1.0
            },
            "dp": {
              "type": "number",
              "title": "Diameter of the pumices [m]",
              "description": "Average diameter of the pumices at fragmentation",
              "exclusiveMinimum": 0.0
            },
            "ds": {
              "type": "number",
              "title": "Diameter of the shards [m]",
              "description": "Average diameter of the shards at fragmentation",
              "exclusiveMinimum": 0.0
            },
            "dc": {
              "type": "number",
              "title": "Diameter of the crystals [m]",
              "description":
                "Average diameter of the crystals at fragmentation",
              "exclusiveMinimum": 0.0
            },
            "c": {
              "type": "number",
              "title": "Crystal volume fraction",
              "description":
                  "Volume fraction of crystals relative to a degassed magma.",
              "exclusiveMinimum": 0.0,
              "maximum": 0.7,
            },
            "den": {
              "type": "number",
              "title": "Crystal density [kg/m^3]",
              "description": "Average density of the crystal phase.",
              "exclusiveMinimum": 0.0
            }
          }
        },
      ]
    }
  }
}

#: Process metadata and description
PROCESS_METADATA = {
  '$defs': {
    'chart': CHART_SCHEMA
  },    

  # process.yaml -> processSummary.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

  # Required properties:
  # ####################

  'id': 'conduit',
  # type string

  'version': '2.1.0',
  # type string

  # Optional properties:
  # ####################

  'jobControlOptions': [
    'async-execute',
    'sync-execute'
  ],
  # type: array,
  #   items: {type: string, enum: ['sync-execute', 'async-execute', 'dismiss']}
  
  'outputTransmission': [
    'value'
  ],
  # type: array, 
  #   items: {type: string, enum: ['value', 'reference'], default: 'value'}

  'links': [{
    # Required:
    'href': 'https://example.org/process',
    # Optional:
    'rel': 'about',
    'type': 'text/html',
    'hreflang': 'en-US',
    'title': 'information'
  }],
  # type: array, 
  #   items: {type: object, required: 'href', properties:
  #       href: type: string, rel: type: string,
  #       type: type: string, hreflang: type: string,
  #       title: type: string }

  # process.yaml -> processSummary.yaml -> descriptionType.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

  # Optional properties:
  # ####################

  'title': 'CONDUIT',
  # type: string

  'description':
    'Fortran code to calculate the multiphase, multicomponent steady flow of '
    'magma along the volcanic conduit '
    '(Papale, P., J. Geophys. Res. 106, 11043–11065, 2001).',
  # type: string
  
  'keywords': ['Fortran code', 'conduit flow'],
  # type: array
  #   items: type: string

  # 'metadata':
  # type: array
  #   items: {type: object, title: string, role: string, href: string}

  # additionalParameters (metadata.yaml + parameters [additionalParameter.yaml]) 


  # process.yaml
  # >>>>>>>>>>>>
  'inputs': {
    # inputDescription.yaml
    'components': {
      'title': INPUT_SCHEMA['properties']['components']['title'],
      'description': INPUT_SCHEMA['properties']['components']['description'],
      'schema': INPUT_SCHEMA['properties']['components'],
      'minOccurs': 1,
      'maxOccurs': 1
    }
  },

  'outputs': {
    'chart_1': {
      'title': 'Gas volume fraction',
      'description': 'Profile of gas volume fraction along the conduit.',
      'schema': {
        '$ref': '#/$defs/chart',
        'contentMediaType': 'application/json'
      }
    },
    'chart_2': {
      'title': 'Velocity',
      'description': 'Velocity profile along the conduit.',
      'schema': {
        '$ref': '#/$defs/chart',
        'contentMediaType': 'application/json'
      }
    },
    'chart_3': {
      'title': 'Pressure',
      'description': 'Pressure profile along the conduit.',
      'schema': {
          '$ref': '#/$defs/chart',
          'contentMediaType': 'application/json'
      }
    },
    'outfile': {
      'title': 'Text file for model outputs',
      'description':
        'Model outputs: '
        '1) conduit length, '
        '2) volume % gas in pumice?, '
        '3) volume % gas before fragmentation, '
        '4) gas velocity, '
        '5) liquid velocity, '
        '6) pressure, '
        '7) dissolved % H2O, '
        '8) dissolved % CO2, '
        '9) gas H2O, '
        '10) gas CO2, '
        '11) mass % gas, '
        '12) volume $ crystals, '
        '13) mass % crystals, '
        '14) liquid+crystals+gas viscosity, '
        '15) liquid+crystals viscosity, '
        '16) liquid viscosity, '
        '17) liquid+crystals+gas density, '
        '18) liquid+crystals density, '
        '19) liquid density, '
        '20) gas density, '
        '21) volume $ crystals, '
        '22) mass % crystals, '
        '23) rate of strain',
      'schema': {
        'type': 'string',
        'contentMediaType': 'text/csv'
      }
    }
  },

  # not defined in process.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>
  'examples': [
    {
      'payload_example': {
        'inputs': {
          'components': {
            'value': {
              'fg': 1.0E8, 'p': 1.0E8, 't': 1050, 'd': 60, 'l': 4000,
              'sio2': 0.7669, 'tio2': 0.0012, 'al2o3': 0.1322,
              'fe2o3': 0.0039, 'feo': 0.0038, 'mno': 0.0007, 'mgo': 0.0006,
              'cao': 0.0080, 'na2o': 0.0300, 'k2o': 0.0512, 'h2o': 0.0500,
              'co2': 0.0200, 'fe': 0.9, 'pd': 0.9, 'dp': 200e-6, 'ds': 200e-6,
              'dc': 200e-6, 'c': 0.1, 'den': 2800
            }
          }
        },
        'outputs': {
          'chart_1': {
            'transmissionMode': 'value'
          },
          'chart_2': {
            'transmissionMode': 'value'
          }
        }
      }
    },
    {
      'curl_example': (
        "curl -k -L -X POST "
        "\"https://epos_geoinquire.pi.ingv.it/epos_pygeoapi/processes/conduit/execution\" "
        "-H \"Content-Type: application/json\" "
        "-d '{\"inputs\":"
              "{\"conponents\":"
                "{\"value\":"
                  "{\"fg\":1.0e8,\"p\":1.0e8,\"t\":1050,"
                    "\"d\":60,\"l\":4000,\"sio2\":0.7669,\"tio2\":0.0012,"
                    "\"al2o3\":0.1322,\"fe2o3\":0.0039,\"feo\":0.0038,"
                    "\"mno\":0.0007,\"mgo\":0.0006,\"cao\":0.0080,"
                    "\"na2o\":0.0300,\"k2o\":0.0512,\"h2o\":0.0500,"
                    "\"co2\":0.0200,\"fe\":0.9,\"pd\":0.9,\"dp\":200e-6,"
                    "\"ds\":200e-6,\"dc\":200e-6,\"c\":0.1,\"den\":2800"
                  "}"
                "}"
              "},"
            "\"outputs\":[\"chart_1\",\"chart_2\"]}'"
      )
    }
  ]
  # curl localhost:5000/processes/conduit/execution -H 'Content-Type: application/json' -d '{ "inputs" : { "components" : { "value" : {"fg": 1.0e8, "p": 1.0e8, "t": 1050.0e0, "d": 60.0e0, "l": 4000.0e0, "sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512, "h2o": 0.0500e0, "co2": 0.0200e0, "fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6, "dc": 200e-6, "c": 0.1, "den": 2800.0e0 } } }, "outputs" : { "chart_1" : { "transmissionMode": "value" }, "chart_2" : { "transmissionMode": "value" } } }'
  # curl localhost:5000/processes/conduit/execution -H 'Content-Type: application/json' -H 'Prefer: respond-async' -d '{ "inputs" : { "components" : { "value" : {"fg": 1.0e8, "p": 1.0e8, "t": 1050.0e0, "d": 60.0e0, "l": 4000.0e0, "sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512, "h2o": 0.0500e0, "co2": 0.0200e0, "fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6, "dc": 200e-6, "c": 0.1, "den": 2800.0e0 } } }, "outputs" : { "chart_1" : { "transmissionMode": "value" }, "chart_2" : { "transmissionMode": "value" } } }'
  # curl -k -L -X POST "https://epos_geoinquire.pi.ingv.it/epos_pygeoapi/processes/conduit/execution" -H "Content-Type: application/json" -d '{ "inputs" : { "components" : { "value" : {"fg": 1.0e8, "p": 1.0e8, "t": 1050.0e0, "d": 60.0e0, "l": 4000.0e0, "sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512, "h2o": 0.0500e0, "co2": 0.0200e0, "fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6, "dc": 200e-6, "c": 0.1, "den": 2800.0e0 } } }, "outputs" : { "chart_1" : { "transmissionMode": "value" }, "chart_2" : { "transmissionMode": "value" } } }'
  #
}


class ConduitProcessor(BaseRemoteExecutionProcessor):
    """Conduit Processor example"""
    def __init__(self, processor_def):
        """
        Initialize object
        :param processor_def: provider definition

        :returns: pygeoapi.process.conduit.ConduitProcessor
        """
        super().__init__(processor_def, PROCESS_METADATA)
        self.supports_outputs = True


    def prepare_output(self, info, working_dir, outputs):
        # Checks for error on outputs request performed by prepare_input().

        possible_outputs = self.metadata['outputs']
        if not bool(outputs):
            requested_outputs = possible_outputs
        else:
            requested_outputs = outputs

        # Prepare outputs
        # ###############
        produced_outputs = {}

        # The code produce an output file: the file name is fixed by the code:
        out_file_name = 'conduit.out'
        # Load values returned by the program
        x_vals = []
        not_used = []
        gas_volume_fraction = []
        gas_velocity = []
        liquid_velocity = []
        pressure = []
        try:
            with open(str(Path(working_dir) / out_file_name)) as output_file:
                for line in output_file:
                    # Remove spaces and split values
                    parts = line.split()
            
                    # If needed convert 'D' in 'E'
                    # (scientific Python notation: should not happen)
                    values = [float(p.replace('D', 'E')) for p in parts]

                    # Add values to elements
                    x_vals.append(values[0])
                    not_used.append(values[1])
                    gas_volume_fraction.append(values[2])
                    gas_velocity.append(values[3])
                    liquid_velocity.append(values[4])
                    pressure.append(values[5])
        except OSError as e:
            LOGGER.error(f"Errore apertura file: {e}")
            raise ProcessorExecuteError(
                f"Program error: please report to the service provider "
                "for this job_id: {info['job_id']}."
            )

        if 'chart_1' in requested_outputs:
            produced_outputs['chart_1'] = {
                'value': {
                    'chartType': 'line',
                    'domain': {
                        'key': 'Conduit length',
                        'label': 'Conduit length',
                        'unit': 'm',
                        'values': x_vals
                    },
                    'series': [
                        {
                            'key': 'Gas volume fraction',
                            'label': 'Gas volume fraction',
                            'unit': '-',
                            'values': gas_volume_fraction
                        }
                    ]
                },
                'mediaType': 'application/json'
            }

        if 'chart_2' in requested_outputs:
            produced_outputs['chart_2'] = {
                'value': {
                    'chartType': 'line',
                    'domain': {
                        'key': 'Conduit length',
                        'label': 'Conduit length',
                        'unit': 'm',
                        'values': x_vals
                    },
                    'series': [
                        {
                            'key': 'Gas velocity',
                            'label': 'Gas velocity',
                            'unit': 'm/s',
                            'values': gas_velocity
                        },
                        {
                            'key': 'Liquid velocity',
                            'label': 'Liquid velocity',
                            'unit': 'm/s',
                            'values': liquid_velocity
                        },
                    ]
                },
                'mediaType': 'application/json'
            }

        if 'chart_3' in requested_outputs:
            produced_outputs['chart_3'] = {
                'value': {
                    'chartType': 'line',
                    'domain': {
                        'key': 'Conduit length',
                        'label': 'Conduit length',
                        'unit': 'm',
                        'values': x_vals
                    },
                    'series': [
                        {
                            'key': 'Pressure',
                            'label': 'Pressure',
                            'unit': 'Mpa',
                            'values': pressure
                        },
                    ]
                },
                'mediaType': 'application/json'
            }
        
        if 'outfile' in requested_outputs:
            with open(str(Path(working_dir) / out_file_name), mode='r') as f:
                contenuto = f.read()

            produced_outputs['outfile'] = {
                'value': contenuto,
                'mediaType': 'text/csv'
            }

        return self.format_output(produced_outputs, outputs)

    def prepare_input(self, data, working_dir, outputs):
        # check for error on outputs request:
        if bool(outputs):
            requested_output = set(
                outputs.keys() if isinstance(outputs, dict) else outputs
            )
            if requested_output - set(self.metadata['outputs']):
                err_msg = 'Outputs contains unexpected parameters.'
                raise ProcessorExecuteError(err_msg)

        try:
            components = data['components']['value']
        except (KeyError, TypeError) as err:
            err_msg = 'Input not correctly formatted: ' + str(err) + '.'
            raise ProcessorExecuteError(err_msg)
        
        # Verify parameters matching definitions.
        LOGGER.debug(f'Validating input')
        validation_errors = validate_json(
            INPUT_SCHEMA['properties']['components'], components
        )
        if validation_errors:
            raise ProcessorExecuteError(validation_errors)

        # Create the dictionary with the properties to be passed to the 'code'
        # where property_name=parameter_name, property_value=parameter_value
        # ###############################################
        code_input_param = {}
        for name in components:
            param_value = components[name]

            # Add as input parameter
            input_flag = '-' + name
            code_input_param[input_flag] = param_value
        
        return code_input_param

    def __repr__(self):
        return f'<ConduitProcessor> {self.name}'
