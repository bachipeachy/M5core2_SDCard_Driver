# The MIT License (MIT)

# Copyright (c) 2013-2022 Damien P. George

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
The original software is extensively modified by bachipeachy@gmail.com.
The test is designed to run on M5Stack Core2 hardware with formatted SDCard 
"""

import os
from sdcard import SDCard


def test_sdcard(mdir='/sd'):
    sdc = SDCard(debug=False)
    vfs = os.VfsFat(sdc)
    os.mount(vfs, mdir)

    try:
        print("\nList Root Directory of SDCard")
        print("before test {} -> {}".format(mdir, os.listdir(mdir)))
    except OSError as e:
        print("ERROR:{} {} missing mount dir {}".format(sdtest, e, mdir))
    except Exception as e:
        print("ERROR:{} {}".format(sdtest, e))

    line = "abcdefghijklmnopqrstuvwxyz\n"
    lines = line * 200  # 5400 chars
    short = "1234567890\n"

    fn1 = mdir + "/sdtest1.txt"
    print("\nLarge File Multiple Block read/write test")
    with open(fn1, "w") as f:
        n = f.write(lines)
        print("{} bytes written to {}".format(n, fn1))
        n = f.write(short)
        print("{} bytes written to {}".format(n, fn1))
        n = f.write(lines)
        print("{} bytes written to {}".format(n, fn1))

    with open(fn1, "r") as f:
        result1 = f.read()
        print("{} bytes read from {}".format(len(result1), fn1))

    fn2 = mdir + "/sdtest2.txt"
    print("\nSmall File Single Block read/write test")
    with open(fn2, "w") as f:
        n = f.write(short)  # one block
        print("{}bytes written to {}".format(n, fn2))

    with open(fn2, "r") as f:
        result2 = f.read()
        print("{} bytes read from {}".format(len(result2), fn2))

    print("\nPerforming Data Read Back test")
    success = True
    
    try:
        if result1 == "".join((lines, short, lines)):
            print("Large file Pass")
        else:
            print("Large file Fail")
            success = False
        if result2 == short:
            print("Small file Pass")
        else:
            print("Small file Fail")
            success = False

        print("after test {} -> {} ".format(mdir, os.listdir(mdir)))
        print("Tests", "passed" if success else "failed")

        os.remove(fn1)

        print("Remove File test ..\nlisting after removing file {} -> {} ".format(fn1, os.listdir(mdir)))

    except MemoryError as e:
        print("ERROR:{} {}".format(sdtest, e))
        print("Sorry! Restart the program/device and run the test again ..")



if __name__ == "__main__":
    
    test_sdcard()
