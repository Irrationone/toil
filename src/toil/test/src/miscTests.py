# Copyright (C) 2015-2016 Regents of the University of California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, print_function
from future.utils import raise_
from builtins import range
from toil.test import ToilTest, slow
from uuid import uuid4

import inspect
import sys
from toil.lib.exceptions import panic

import os
import random
import tempfile
import logging


log = logging.getLogger(__name__)
logging.basicConfig()

class MiscTests(ToilTest):
    """
    This class contains miscellaneous tests that don't have enough content to be their own test
    file, and that don't logically fit in with any of the other test suites.
    """
    def setUp(self):
        super(MiscTests, self).setUp()
        self.testDir = self._createTempDir()

    @slow
    def testGetSizeOfDirectoryWorks(self):
        '''A test to make sure toil.common.getDirSizeRecursively does not
        underestimate the amount of disk space needed.

        Disk space allocation varies from system to system.  The computed value
        should always be equal to or slightly greater than the creation value.
        This test generates a number of random directories and randomly sized
        files to test this using getDirSizeRecursively.
        '''
        from toil.common import getDirSizeRecursively
        # a list of the directories used in the test
        directories = [self.testDir]
        # A dict of {FILENAME: FILESIZE} for all files used in the test
        files = {}
        # Create a random directory structure
        for i in range(0,10):
            directories.append(tempfile.mkdtemp(dir=random.choice(directories), prefix='test'))
        # Create 50 random file entries in different locations in the directories. 75% of the time
        # these are fresh files of sixe [1, 10] MB and 25% of the time they are hard links to old
        # files.
        while len(files) <= 50:
            fileName = os.path.join(random.choice(directories), self._getRandomName())
            if random.randint(0,100) < 75:
                # Create a fresh file in the range of 1-10 MB
                fileSize = int(round(random.random(), 2) * 10 * 1024 * 1024)
                with open(fileName, 'wb') as fileHandle:
                    fileHandle.write(os.urandom(fileSize))
                files[fileName] = fileSize
            else:
                # Link to one of the previous files
                if len(files) == 0:
                    continue
                linkSrc = random.choice(list(files.keys()))
                os.link(linkSrc, fileName)
                files[fileName] = 'Link to %s' % linkSrc

        computedDirectorySize = getDirSizeRecursively(self.testDir)
        totalExpectedSize = sum([x for x in list(files.values()) if isinstance(x, int)])
        self.assertGreaterEqual(computedDirectorySize, totalExpectedSize)

    @staticmethod
    def _getRandomName():
        return uuid4().hex


class TestPanic(ToilTest):
    def test_panic_by_hand(self):
        try:
            self.try_and_panic_by_hand()
        except:
            self.__assert_raised_exception_is_primary()

    def test_panic(self):
        try:
            self.try_and_panic()
        except:
            self.__assert_raised_exception_is_primary()

    def test_panic_with_secondary(self):
        try:
            self.try_and_panic_with_secondary()
        except:
            self.__assert_raised_exception_is_primary()

    def test_nested_panic(self):
        try:
            self.try_and_nested_panic_with_secondary()
        except:
            self.__assert_raised_exception_is_primary()

    def try_and_panic_by_hand(self):
        try:
            self.line_of_primary_exc = inspect.currentframe().f_lineno + 1
            raise ValueError("primary")
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            try:
                raise RuntimeError("secondary")
            except Exception:
                pass
            raise_(exc_type, exc_value, exc_traceback)

    def try_and_panic(self):
        try:
            self.line_of_primary_exc = inspect.currentframe().f_lineno + 1
            raise ValueError("primary")
        except:
            with panic(log):
                pass

    def try_and_panic_with_secondary(self):
        try:
            self.line_of_primary_exc = inspect.currentframe().f_lineno + 1
            raise ValueError("primary")
        except:
            with panic( log ):
                raise RuntimeError("secondary")

    def try_and_nested_panic_with_secondary(self):
        try:
            self.line_of_primary_exc = inspect.currentframe().f_lineno + 1
            raise ValueError("primary")
        except:
            with panic( log ):
                with panic( log ):
                    raise RuntimeError("secondary")

    def __assert_raised_exception_is_primary(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        self.assertEquals(exc_type, ValueError)
        self.assertEquals(str(exc_value), "primary")
        while exc_traceback.tb_next is not None:
            exc_traceback = exc_traceback.tb_next
        self.assertEquals(exc_traceback.tb_lineno, self.line_of_primary_exc)
