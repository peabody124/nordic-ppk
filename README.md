Some modifications to version 1.1 of the Noridc nRF6707 desktop software to run on OSX

This requires PyQt5 and only seems to run with the installed python2.7 with OSX
- brew install pyqt5
- sudo /usr/bin/python2.7 -m pip install pynrfjproj pyqtgraph matplotlib
- /usr/bin/python2.7 ppk.py

PYTHONPATH includes /usr/local/lib/python2.7/site-packages/ to find PyQt5 from Homebrew

Code and credit goes to Nordic Semiconductor. I just made a few tweaks.
