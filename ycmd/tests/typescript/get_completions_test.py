# encoding: utf-8
#
# Copyright (C) 2015-2018 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       has_entries,
                       has_item,
                       matches_regexp )
from nose.tools import eq_
import pprint
import requests

from ycmd.tests.typescript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    CombineRequest,
                                    CompletionEntryMatcher,
                                    WaitForDiagnosticsToBeReady,
                                    UnixOnly,
                                    LocationMatcher )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  WaitForDiagnosticsToBeReady( app,
                               test[ 'request' ][ 'filepath' ],
                               contents,
                               'typescript' )
  app.post_json(
    '/event_notification',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'typescript',
      'event_name': 'BufferVisit'
    } )
  )

  response = app.post_json(
    '/completions',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'typescript',
      'force_semantic': True
    } )
  )

  print( 'completer response: {0}'.format( pprint.pformat( response.json ) ) )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_Basic_test( app ):
  RunTest( app, {
    'description': 'Extra and detailed info when completions are methods',
    'request': {
      'line_num': 17,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.ts' )
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher(
            'methodA',
            '(method) Foo.methodA(): void',
            extra_params = {
              'kind': 'Method',
              'detailed_info': 'methodA\n\nUnicode string: 说话'
            }
          ),
          CompletionEntryMatcher(
            'methodB',
            '(method) Foo.methodB(): void',
            extra_params = {
              'kind': 'Method',
              'detailed_info': 'methodB\n\n'
            }
          ),
          CompletionEntryMatcher(
            'methodC',
            '(method) Foo.methodC(a: {\n    foo: string;'
            '\n    bar: number;\n}): void',
            extra_params = {
              'kind': 'Method',
              'detailed_info': 'methodC\n\n'
            }
          )
        )
      } )
    }
  } )


@SharedYcmd
def GetCompletions_AfterRestart_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  app.post_json( '/run_completer_command',
                BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'RestartServer' ],
                              filetype = 'typescript',
                              filepath = filepath ) )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 17,
                                  column_num = 6 )
  app.post_json( '/event_notification',
                 BuildRequest(
                   filepath = filepath,
                   event_name = 'FileReadyToParse',
                   filetype = 'typescript' ) )
  WaitForDiagnosticsToBeReady( app, filepath, contents, 'typescript' )
  assert_that(
    app.post_json( '/completions', completion_data ).json,
    has_entries( {
      'completions': contains_inanyorder(
          CompletionEntryMatcher(
            'methodA',
            '(method) Foo.methodA(): void',
            extra_params = {
              'kind': 'Method',
              'detailed_info': 'methodA\n\nUnicode string: 说话'
            }
          ),
          CompletionEntryMatcher(
            'methodB',
            '(method) Foo.methodB(): void',
            extra_params = {
              'kind': 'Method',
              'detailed_info': 'methodB\n\n'
            }
          ),
          CompletionEntryMatcher(
            'methodC',
            '(method) Foo.methodC(a: {\n    foo: string;'
            '\n    bar: number;\n}): void',
            extra_params = {
              'kind': 'Method',
              'detailed_info': 'methodC\n\n'
            }
          )
      )
    } )
  )


@UnixOnly
@SharedYcmd
def GetCompletions_AutoImport_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )
  WaitForDiagnosticsToBeReady( app, filepath, contents, 'javascript' )
  RunTest( app, {
    'description': 'Symbol from external module can be completed and '
                   'its completion contains fixits to automatically import it',
    'request': {
      'line_num': 39,
      'column_num': 5,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( has_entries( {
          'insertion_text':  'Bår',
          'menu_text':       'Bår',
          'extra_menu_info': "Auto import from './unicode'\nclass Bår",
          'detailed_info':   'Bår\n\n',
          'kind':            'Class',
          'extra_data': has_entries( {
            'fixits': contains_inanyorder(
              has_entries( {
                'text': '',
                'chunks': contains(
                  ChunkMatcher(
                    matches_regexp( '^import { Bår } from "./unicode";\r?\n' ),
                    LocationMatcher( filepath, 1, 1 ),
                    LocationMatcher( filepath, 1, 1 )
                  )
                ),
                'location': LocationMatcher( filepath, 1, 1 )
              } )
            )
          } )
        } ) )
      } )
    }
  } )
