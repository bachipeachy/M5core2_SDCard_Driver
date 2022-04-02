# The MIT License (MIT)
#
# Copyright (c) 2022 bachipeachy@gmail.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import os
from sdcard import SDCard


class SDCardUtil:

    def __init__(self, mdir='/sd'):

        self.mdir = mdir
        self.mount_sd()

    def mount_sd(self):

        try:
            sdc = SDCard()
            vfs = os.VfsFat(sdc)
            os.mount(vfs, self.mdir)
            print("Flash Memory root level listing -> {}".format(os.listdir()))

        except OSError as e:
            if e.errno == errno.EPERM:
                print("{} already mounted".format(self.mdir))

        except Exception as e:
            print("ERROR: {}{} {}".format(SDUtil, SDUtil.mount_sd, e))

    def erase_sd(self, path):

        try:
            print("contents in sdcard before erase {} -> {}".format(self.mdir, os.listdir(self.mdir)))

        except Exception as e:
            print("ERROR: {}{} {}".format(SDUtil, SDUtil.erase_sd, e))

        if path[0] != '/':
            path = '/' + path

        try:
            os.remove(self.mdir + path)
            print("success removed'{}'".format(self.mdir + path))
            print("contents in sdcard after erase {} -> {}".format(self.mdir, os.listdir(self.mdir)))

        except OSError as e:
            if e.errno == errno.ENOENT:
                print("{}: did not find '{}' in '{}'".format(e, path, self.mdir))
            else:
                print("checking if path '{}' is a dir".format(path))
            if e.errno == errno.EISDIR:
                try:
                    ct = len([f for f in os.listdir(self.mdir + path)])
                    if ct == 0:
                        os.rmdir(self.mdir + path)
                        print("success removed empty dir {}".format(self.mdir + path))
                        print("contents in sdcard after erase {} -> {}".format(self.mdir, os.listdir(self.mdir)))
                    else:
                        print("{}: dir '{}' is not empty has {} entry -> {}".format(e, self.mdir + path, ct,
                                                                                    os.listdir(self.mdir + path)))

                except Exception as e:
                    print("ERROR: {}{} {}".format(SDUtil, SDUtil.erase_sd, e))
            else:
                pass


if __name__ == "__main__":
    sdu = SDCardUtil()
    os.listdir('/sd')
