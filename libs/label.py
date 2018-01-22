from PySide import QtCore, QtGui

class EditableLabel(QtGui.QLabel):
    ''' Custom label class, inherited from QLabel. Double clicking it with let you edit the value of it.
        Will emit a valueChanged signal upon return pressed
    '''
    valueChanged = QtCore.Signal()
    def __init__(self,layout, idx):
        QtGui.QLabel.__init__(self)
        self.layout = layout
        self.idx = idx
        self.initial_val = None

    def mousePressEvent(self, ev):
        self.start_edit_text()

    def start_edit_text(self):
        self.initial_val = self.text().split(' ')[0]

        self.edit_text = QtGui.QLineEdit(self.text())               # Create a lineedit
        self.edit_text.setFixedWidth(40)
        self.edit_text.setText(str(self.initial_val))
        self.hide()                                                 # Hide label
        self.layout.insertWidget(self.idx, self.edit_text)          # Insert line edit in place
        self.edit_text.returnPressed.connect(self.finish_edit_text) # Enter pressed
        self.setText(self.initial_val)                              # Set text of label
        self.edit_text.selectAll()                                  # Select the text for easy editing
        self.edit_text.setFocus()                                   # Place cursor in lineedit

    def finish_edit_text(self):
        self.edit_text.hide()                                       # Hide the lineedit
        if not self.edit_text.text() == '':
            if ',' in self.edit_text.text():                 # Replace commas with period if used
                self.edit_text.setText(self.edit_text.text().replace(',','.'))
            self.setText(self.edit_text.text())                     # Set new labeltext

            try:
                tmp = int(self.edit_text.text())
            except:
                print("Invalid format")
                self.setText(self.initial_val)

        else:
            print("Invalid format")
            self.setText(self.initial_val)
        self.show()                                                 # Show label
        self.valueChanged.emit()
