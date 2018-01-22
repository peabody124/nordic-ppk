@echo off
echo Installing pyside
python -m pip install pyside
echo Installing matplotlib
python -m pip install matplotlib
echo Installing pyqtgraph
python -m pip install pyqtgraph
echo Installing pynrfjprog
python -m pip install pynrfjprog --upgrade
echo Finished.
pause
